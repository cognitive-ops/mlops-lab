"""
Step 2: Fine-tune Phi-3.5-mini on Claude-generated data using PEFT + LoRA.
Runs on 8GB VRAM via QLoRA (4-bit base + 16-bit LoRA adapters).

Install:
  pip install trl peft transformers datasets torch accelerate bitsandbytes
"""
from pathlib import Path
from datasets import load_dataset
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training, TaskType
from trl import SFTTrainer, SFTConfig
import torch

# --- Config ---
BASE_MODEL = "microsoft/Phi-3.5-mini-instruct"
DATA_PATH = str(Path(__file__).parent / "training_data.jsonl")
OUTPUT_DIR = str(Path(__file__).parent / "output" / "model")

LORA_R = 16           # rank — higher = better quality, more VRAM
LORA_ALPHA = 32       # usually 2x rank
LORA_DROPOUT = 0.05

BATCH_SIZE = 1        # 8GB VRAM — keep low
GRAD_ACCUM = 8        # effective batch = 8
EPOCHS = 3
LR = 2e-4
MAX_SEQ_LEN = 1024    # reduce if OOM
USE_4BIT = True       # set False if bitsandbytes/CUDA errors (needs 16GB+ VRAM)


TASK_SYSTEM_PROMPT = """You are a senior software engineer and solutions architect with 15+ years of experience.
Given a software development task or requirement, provide a structured, actionable response covering:
- Analysis of the requirement or problem
- Recommended approach or solution with reasoning
- Key considerations (scalability, security, maintainability)
- Concrete implementation steps or code where relevant
Be precise, technical, and opinionated. Avoid vague advice."""


def format_prompt(example: dict) -> str:
    return (
        f"<|system|>\n{example['instruction']}<|end|>\n"
        f"<|user|>\n{example['input']}<|end|>\n"
        f"<|assistant|>\n{example['output']}<|end|>"
    )


def load_model_with_lora():
    tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL, trust_remote_code=True)
    tokenizer.pad_token = tokenizer.unk_token
    tokenizer.pad_token_id = tokenizer.convert_tokens_to_ids(tokenizer.pad_token)
    tokenizer.padding_side = "right"

    if USE_4BIT:
        bnb_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16,
            bnb_4bit_use_double_quant=True,
        )
        model = AutoModelForCausalLM.from_pretrained(
            BASE_MODEL,
            quantization_config=bnb_config,
            device_map="auto",
            trust_remote_code=True,
            attn_implementation="eager",
        )
        model = prepare_model_for_kbit_training(model)
        print("Loaded in 4-bit (QLoRA)")
    else:
        model = AutoModelForCausalLM.from_pretrained(
            BASE_MODEL,
            torch_dtype=torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16,
            device_map="auto",
            trust_remote_code=True,
            attn_implementation="eager",
        )
        print("Loaded in fp16/bf16 (LoRA)")

    # Apply LoRA
    lora_config = LoraConfig(
        r=LORA_R,
        lora_alpha=LORA_ALPHA,
        lora_dropout=LORA_DROPOUT,
        bias="none",
        task_type=TaskType.CAUSAL_LM,
        target_modules=["qkv_proj", "o_proj", "gate_up_proj", "down_proj"],
    )
    model = get_peft_model(model, lora_config)
    model.print_trainable_parameters()

    return model, tokenizer


def main():
    model, tokenizer = load_model_with_lora()

    dataset = load_dataset("json", data_files=DATA_PATH, split="train")
    dataset = dataset.map(lambda x: {"text": format_prompt(x)})
    print(f"Dataset: {len(dataset)} examples")

    train_size = int(0.9 * len(dataset))
    train_ds = dataset.select(range(train_size))
    eval_ds = dataset.select(range(train_size, len(dataset)))

    trainer = SFTTrainer(
        model=model,
        processing_class=tokenizer,
        train_dataset=train_ds,
        eval_dataset=eval_ds,
        args=SFTConfig(
            output_dir=OUTPUT_DIR,
            dataset_text_field="text",
            max_seq_length=MAX_SEQ_LEN,
            num_train_epochs=EPOCHS,
            per_device_train_batch_size=BATCH_SIZE,
            gradient_accumulation_steps=GRAD_ACCUM,
            gradient_checkpointing=True,      # saves ~30% VRAM during training
            learning_rate=LR,
            bf16=torch.cuda.is_bf16_supported(),
            fp16=not torch.cuda.is_bf16_supported(),
            warmup_ratio=0.1,
            lr_scheduler_type="cosine",
            eval_strategy="epoch",
            save_strategy="epoch",
            load_best_model_at_end=True,
            logging_steps=5,
            optim="paged_adamw_8bit" if USE_4BIT else "adamw_torch",
            report_to="none",
        ),
    )

    print(f"\nFine-tuning: {BASE_MODEL} with LoRA r={LORA_R}")
    trainer.train()

    adapter_path = Path(OUTPUT_DIR) / "lora_adapter"
    model.save_pretrained(adapter_path)
    tokenizer.save_pretrained(adapter_path)
    print(f"\nLoRA adapter saved → {adapter_path}")
    print("Run 3_inference.py to test.")


if __name__ == "__main__":
    main()

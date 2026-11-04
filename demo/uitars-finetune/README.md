# UI-TARS LoRA SFT (domain adaptation)

UI-TARS-7B-SFT = Qwen2-VL-7B + GUI-agent training. Start from it, LoRA on your app's screenshot→action data.

## Steps
```bash
pip install -r requirements.txt
python convert_data.py --raw raw_steps.jsonl --img-root . --out data
llamafactory-cli train sft_lora.yaml
llamafactory-cli export --model_name_or_path bytedance-research/UI-TARS-7B-SFT \
  --adapter_name_or_path outputs/uitars7b-lora --template qwen2_vl \
  --finetuning_type lora --export_dir outputs/merged
```

## Raw step format (jsonl)
`{"image":"shots/1.png","task":"Open settings","thought":"...","action":"click","x":0.52,"y":0.13}`
x,y relative 0-1. Actions: click, type(+text), scroll(+direction), finished.

## Gotchas
- Coordinate convention must match the checkpoint. Converter uses absolute pixels in Qwen2-VL smart-resized space.
  Before training, run base UI-TARS on a few screenshots and confirm its output coord style; adjust `fmt_action` if not.
- Keep `image_max_pixels` in YAML equal to MAX_PIXELS in converter.
- Mix ~10-20% general GUI data to avoid forgetting.
- VRAM: 7B bf16 LoRA ~40GB; QLoRA ~24GB; swap to UI-TARS-2B-SFT for ~16GB.
- Eval: grounding hit-rate (click within GT bbox) + step success on held-out tasks.

"""
PhoBERT-based Vietnamese sentiment analysis.

Dependencies:
    pip install transformers torch pyvi

Model: wonrax/phobert-base-vietnamese-sentiment
Labels: NEG (negative), NEU (neutral), POS (positive)
"""

from pyvi import ViTokenizer
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch
import torch.nn.functional as F

MODEL_NAME = "wonrax/phobert-base-vietnamese-sentiment"

tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
model = AutoModelForSequenceClassification.from_pretrained(MODEL_NAME)
model.eval()

LABEL_MAP = {0: "NEG", 1: "NEU", 2: "POS"}


def predict_sentiment(text: str, debug: bool = False) -> dict:
    """Return sentiment label and per-class probabilities for Vietnamese text."""
    segmented = ViTokenizer.tokenize(text)
    if debug:
        print(f"[DEBUG] Raw text     : {text}")
        print(f"[DEBUG] Segmented    : {segmented}")

    inputs = tokenizer(segmented, return_tensors="pt", truncation=True, max_length=256)
    if debug:
        tokens = tokenizer.convert_ids_to_tokens(inputs["input_ids"][0])
        print(f"[DEBUG] Token count  : {len(tokens)}")
        print(f"[DEBUG] Tokens       : {tokens}")

    with torch.no_grad():
        logits = model(**inputs).logits
    if debug:
        print(f"[DEBUG] Raw logits   : {logits.tolist()}")

    probs = F.softmax(logits, dim=-1).squeeze()
    label_idx = int(probs.argmax())
    if debug:
        print(f"[DEBUG] Probabilities: {[round(float(p), 4) for p in probs]}")
        print(f"[DEBUG] Predicted    : {LABEL_MAP[label_idx]}")

    return {
        "text": text,
        "label": LABEL_MAP[label_idx],
        "scores": {LABEL_MAP[i]: round(float(probs[i]), 4) for i in range(3)},
    }


if __name__ == "__main__":
    samples = [
        "Sản phẩm này rất tuyệt vời, tôi rất hài lòng!",
        "Dịch vụ tệ quá, tôi sẽ không quay lại nữa.",
        "Hàng nhận được đúng mô tả, giao hàng bình thường.",
    ]

    for text in samples:
        result = predict_sentiment(text, debug=True)
        print(f"Text  : {result['text']}")
        print(f"Label : {result['label']}")
        print(f"Scores: {result['scores']}")
        print()

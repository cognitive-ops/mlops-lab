"""Generate blank placeholder screenshots so convert_data.py runs on raw_steps.jsonl."""
import json
from pathlib import Path

from PIL import Image, ImageDraw

Path("shots").mkdir(exist_ok=True)
for line in Path("raw_steps.jsonl").read_text(encoding="utf-8").splitlines():
    p = Path(json.loads(line)["image"])
    img = Image.new("RGB", (1920, 1080), "white")
    ImageDraw.Draw(img).text((20, 20), p.stem, fill="black")
    img.save(p)

"""Convert raw GUI trajectories to LLaMA-Factory sharegpt format for UI-TARS SFT.

Input  (jsonl, one step per line):
  {"image": "shots/001.png", "task": "Open settings", "thought": "...",
   "action": "click", "x": 0.52, "y": 0.13}          # x,y relative 0-1
  action in: click | type (needs "text") | scroll (needs "direction") | finished

Output: data/uitars_train.json + data/dataset_info.json
"""
import argparse
import json
import math
from pathlib import Path

from PIL import Image

# Qwen2-VL smart_resize defaults; UI-TARS-1.0 coords live in this resized space.
FACTOR, MIN_PIXELS, MAX_PIXELS = 28, 56 * 56, 28 * 28 * 1280

PROMPT = (
    "You are a GUI agent. You are given a task and your action history, with screenshots. "
    "You need to perform the next action to complete the task.\n\n"
    "## Output Format\nThought: ...\nAction: ...\n\n"
    "## Action Space\nclick(start_box='(x,y)')\ntype(content='')\n"
    "scroll(start_box='(x,y)', direction='down or up or right or left')\nfinished()\n\n"
    "## Task\n{task}"
)


def smart_resize(h: int, w: int) -> tuple[int, int]:
    rh, rw = round(h / FACTOR) * FACTOR, round(w / FACTOR) * FACTOR
    if rh * rw > MAX_PIXELS:
        b = math.sqrt(h * w / MAX_PIXELS)
        rh, rw = math.floor(h / b / FACTOR) * FACTOR, math.floor(w / b / FACTOR) * FACTOR
    elif rh * rw < MIN_PIXELS:
        b = math.sqrt(MIN_PIXELS / (h * w))
        rh, rw = math.ceil(h * b / FACTOR) * FACTOR, math.ceil(w * b / FACTOR) * FACTOR
    return rh, rw


def fmt_action(s: dict, rh: int, rw: int) -> str:
    pt = f"({round(s['x'] * rw)},{round(s['y'] * rh)})" if "x" in s else ""
    a = s["action"]
    if a == "click":
        return f"click(start_box='{pt}')"
    if a == "type":
        return f"type(content='{s['text']}')"
    if a == "scroll":
        return f"scroll(start_box='{pt}', direction='{s['direction']}')"
    return "finished()"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", required=True)
    ap.add_argument("--img-root", default=".")
    ap.add_argument("--out", default="data")
    a = ap.parse_args()

    rows = []
    for line in Path(a.raw).read_text(encoding="utf-8").splitlines():
        s = json.loads(line)
        img = Path(a.img_root) / s["image"]
        w, h = Image.open(img).size
        rh, rw = smart_resize(h, w)
        rows.append({
            "messages": [
                {"role": "user", "content": "<image>" + PROMPT.format(task=s["task"])},
                {"role": "assistant",
                 "content": f"Thought: {s.get('thought', '')}\nAction: {fmt_action(s, rh, rw)}"},
            ],
            "images": [str(img.resolve())],
        })

    out = Path(a.out)
    out.mkdir(exist_ok=True)
    (out / "uitars_train.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
    (out / "dataset_info.json").write_text(json.dumps({
        "uitars_train": {
            "file_name": "uitars_train.json",
            "formatting": "sharegpt",
            "columns": {"messages": "messages", "images": "images"},
            "tags": {"role_tag": "role", "content_tag": "content",
                     "user_tag": "user", "assistant_tag": "assistant"},
        }
    }, indent=1), encoding="utf-8")
    print(f"wrote {len(rows)} samples -> {out}")


if __name__ == "__main__":
    main()

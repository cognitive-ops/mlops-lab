"""UI-TARS inference demo: screenshot + task -> next action, click point drawn on image.

  python demo_infer.py --image shots/task1_step1.png --task "Open the Settings page"
  python demo_infer.py --screenshot --task "Open the Start menu"          # grab live screen
  python demo_infer.py --image a.png --task "..." --adapter outputs/uitars7b-lora
"""
import argparse
import re

import torch
from PIL import Image, ImageDraw, ImageGrab
from qwen_vl_utils import process_vision_info
from transformers import AutoProcessor, Qwen2VLForConditionalGeneration

from convert_data import MAX_PIXELS, PROMPT


def parse_action(text: str) -> dict:
    """Extract Thought/Action and parameters from model output."""
    thought = re.search(r"Thought:\s*(.*?)\s*Action:", text, re.S)
    action = text.split("Action:")[-1].strip()
    name = re.match(r"(\w+)\(", action)
    pt = re.search(r"\(\s*(\d+)\s*,\s*(\d+)\s*\)", action)
    content = re.search(r"content='(.*?)'", action, re.S)
    direction = re.search(r"direction='(\w+)'", action)
    return {
        "thought": thought.group(1) if thought else "",
        "raw": action,
        "name": name.group(1) if name else "unknown",
        "point": (int(pt.group(1)), int(pt.group(2))) if pt else None,
        "content": content.group(1) if content else None,
        "direction": direction.group(1) if direction else None,
    }


def _is_wsl() -> bool:
    try:
        return "microsoft" in open("/proc/version").read().lower()
    except OSError:
        return False


def grab_screen() -> Image.Image:
    """Full-screen capture. WSLg can't grab via X11, so on WSL shoot the Windows desktop."""
    if not _is_wsl():
        return ImageGrab.grab()
    import os
    import subprocess
    import tempfile
    fd, path = tempfile.mkstemp(suffix=".png")
    os.close(fd)
    win_path = subprocess.check_output(["wslpath", "-w", path], text=True).strip()
    ps = (
        "Add-Type -AssemblyName System.Windows.Forms,System.Drawing;"
        "Add-Type 'using System.Runtime.InteropServices;"
        "public class D{[DllImport(\"user32.dll\")]public static extern bool SetProcessDPIAware();}';"
        "[D]::SetProcessDPIAware()|Out-Null;"
        "$b=[System.Windows.Forms.SystemInformation]::VirtualScreen;"
        "$bmp=New-Object System.Drawing.Bitmap $b.Width,$b.Height;"
        "$g=[System.Drawing.Graphics]::FromImage($bmp);"
        "$g.CopyFromScreen($b.Location,[System.Drawing.Point]::Empty,$b.Size);"
        f"$bmp.Save('{win_path}')"
    )
    subprocess.run(["powershell.exe", "-NoProfile", "-Command", ps], check=True)
    img = Image.open(path)
    img.load()
    os.remove(path)
    return img


def load(model_id: str, adapter: str | None = None):
    model = Qwen2VLForConditionalGeneration.from_pretrained(
        model_id, torch_dtype=torch.bfloat16, device_map="auto")
    if adapter:
        from peft import PeftModel
        model = PeftModel.from_pretrained(model, adapter)
    processor = AutoProcessor.from_pretrained(model_id, max_pixels=MAX_PIXELS)
    return model, processor


def predict(model, processor, img: Image.Image, task: str, coord: str = "pixel") -> dict:
    """Run one step. Returns parsed action plus `screen_point` in original image pixels."""
    W, H = img.size
    messages = [{"role": "user", "content": [
        {"type": "image", "image": img},
        {"type": "text", "text": PROMPT.format(task=task)},
    ]}]
    text = processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    images, videos = process_vision_info(messages)
    inputs = processor(text=[text], images=images, videos=videos,
                       padding=True, return_tensors="pt").to(model.device)
    with torch.no_grad():
        out = model.generate(**inputs, max_new_tokens=256, do_sample=False)
    reply = processor.batch_decode(out[:, inputs.input_ids.shape[1]:],
                                   skip_special_tokens=True)[0]
    act = parse_action(reply)
    act["reply"] = reply
    act["screen_point"] = None
    if act["point"]:
        x, y = act["point"]
        if coord == "pixel":   # coords live in the resized image; grid is in 14px patches
            _, gh, gw = inputs["image_grid_thw"][0].tolist()
            act["screen_point"] = (x / (gw * 14) * W, y / (gh * 14) * H)
        else:
            act["screen_point"] = (x / 1000 * W, y / 1000 * H)
    return act


def draw_point(img: Image.Image, pt) -> Image.Image:
    img = img.copy()
    d, r = ImageDraw.Draw(img), max(12, img.size[0] // 120)
    px, py = pt
    d.ellipse([px - r, py - r, px + r, py + r], outline="red", width=4)
    d.line([px - 2 * r, py, px + 2 * r, py], fill="red", width=2)
    d.line([px, py - 2 * r, px, py + 2 * r], fill="red", width=2)
    return img


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="bytedance-research/UI-TARS-7B-SFT")
    ap.add_argument("--adapter", help="optional LoRA adapter dir")
    ap.add_argument("--image")
    ap.add_argument("--screenshot", action="store_true", help="capture current screen")
    ap.add_argument("--task", required=True)
    ap.add_argument("--coord", choices=["pixel", "norm1000"], default="pixel",
                    help="coordinate convention of the checkpoint (verify on your model)")
    ap.add_argument("--out", default="demo_out.png")
    a = ap.parse_args()

    img = (grab_screen() if a.screenshot else Image.open(a.image)).convert("RGB")
    model, processor = load(a.model, a.adapter)
    act = predict(model, processor, img, a.task, a.coord)
    print("MODEL OUTPUT:\n", act["reply"])
    print("\nPARSED:", {k: v for k, v in act.items() if k != "reply"})
    if not act["screen_point"]:
        img.save(a.out)
        print(f"WARNING: no click point in model output; saved plain screenshot -> {a.out}")
        return
    px, py = act["screen_point"]
    W, H = img.size
    print(f"click at ({px:.0f},{py:.0f}) of {W}x{H}")
    if not (0 <= px < W and 0 <= py < H):
        print(f"WARNING: point is outside the image; wrong --coord convention? "
              f"(tried '{a.coord}'). Marker clamped to the edge.")
        px, py = min(max(px, 0), W - 1), min(max(py, 0), H - 1)
    draw_point(img, (px, py)).save(a.out)
    print(f"saved {a.out}")


if __name__ == "__main__":
    main()

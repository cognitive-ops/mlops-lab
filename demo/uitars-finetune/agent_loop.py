"""UI-TARS execution loop: screenshot -> predict -> (confirm) -> execute -> repeat.

  python agent_loop.py --task "Open Notepad and type hello" --dry-run
  python agent_loop.py --task "Open the Start menu" --adapter outputs/uitars7b-lora

Safety: confirms every action by default, step limit, pyautogui FAILSAFE
(slam mouse into a screen corner to abort), --dry-run executes nothing.
Run inside a VM / sandbox account, not on a machine with real data.
"""
import argparse
import time
from pathlib import Path

import pyautogui
from demo_infer import draw_point, grab_screen, load, predict

pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.3


def execute(act: dict) -> bool:
    """Run one parsed action. Returns True when the task is finished."""
    name, pt = act["name"], act["screen_point"]
    if name == "click" and pt:
        pyautogui.click(*pt)
    elif name in ("double_click", "left_double") and pt:
        pyautogui.doubleClick(*pt)
    elif name in ("right_click", "right_single") and pt:
        pyautogui.rightClick(*pt)
    elif name == "type" and act["content"] is not None:
        text = act["content"].replace("\\n", "\n").replace("\\'", "'")
        pyautogui.write(text, interval=0.02)   # ASCII only; use pyperclip paste for unicode
    elif name == "scroll" and pt:
        pyautogui.moveTo(*pt)
        horizontal = act["direction"] in ("left", "right")
        amount = 500 if act["direction"] in ("up", "left") else -500
        (pyautogui.hscroll if horizontal else pyautogui.scroll)(amount)
    elif name == "hotkey":
        pyautogui.hotkey(*act["raw"].split("'")[1].split())
    elif name == "wait":
        time.sleep(5)
    elif name in ("finished", "call_user"):
        return True
    else:
        print(f"  ! unsupported action: {act['raw']}")
    return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="bytedance-research/UI-TARS-7B-SFT")
    ap.add_argument("--adapter")
    ap.add_argument("--task", required=True)
    ap.add_argument("--coord", choices=["pixel", "norm1000"], default="pixel")
    ap.add_argument("--max-steps", type=int, default=15)
    ap.add_argument("--settle", type=float, default=1.5, help="seconds to wait after each action")
    ap.add_argument("--no-confirm", action="store_true", help="skip per-action confirmation")
    ap.add_argument("--dry-run", action="store_true", help="predict only, never execute")
    ap.add_argument("--log-dir", default="agent_logs")
    a = ap.parse_args()

    log = Path(a.log_dir) / time.strftime("%Y%m%d_%H%M%S")
    log.mkdir(parents=True, exist_ok=True)
    model, processor = load(a.model, a.adapter)

    for step in range(1, a.max_steps + 1):
        img = grab_screen().convert("RGB")
        act = predict(model, processor, img, a.task, a.coord)
        shot = draw_point(img, act["screen_point"]) if act["screen_point"] else img
        shot.save(log / f"step{step:02d}.png")
        (log / f"step{step:02d}.txt").write_text(act["reply"], encoding="utf-8")
        print(f"[{step}] {act['thought']}\n    -> {act['raw']}")

        if a.dry_run:
            break   # nothing executes, so the screen never changes; one prediction is enough
        if not a.no_confirm and input("    execute? [y/N] ").strip().lower() != "y":
            print("stopped by user")
            return
        if execute(act):
            print("done.")
            return
        time.sleep(a.settle)
    print(f"stopped after {step} step(s). logs: {log}")


if __name__ == "__main__":
    main()

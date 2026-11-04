# Technical Solution: Domain-Adapted GUI Agent on UI-TARS (Qwen2-VL)

## 1. Objective

Build a GUI agent that, given a screenshot and a task, predicts the next UI action (click, type, scroll, finish) accurately on a specific target application or domain. Adapt an existing GUI-agent model through parameter-efficient fine-tuning, not by training from scratch.

**Success criteria (to be confirmed with stakeholders)**
- Grounding accuracy on target-app screens above the base UI-TARS baseline.
- Step success rate on held-out tasks above the base UI-TARS baseline.
- No significant regression on general GUI benchmarks (e.g. ScreenSpot).

## 2. Background and Key Decision

UI-TARS-2B/7B/72B (ByteDance) are Qwen2-VL checkpoints already trained for GUI perception, grounding and action prediction. Fine-tuning plain Qwen2-VL "combined with" UI-TARS therefore reduces to a choice of starting point:

| Option | Description | Decision |
|---|---|---|
| A. Fine-tune UI-TARS checkpoint | Start from `UI-TARS-7B-SFT`, LoRA on domain data | **Chosen** |
| B. Train base Qwen2-VL on UI-TARS-style data | Re-create GUI skills from scratch | Rejected: needs large data and compute, and the result would be worse than UI-TARS |
| C. Weight-merge custom Qwen2-VL tune with UI-TARS | Task-arithmetic or SLERP merge | Optional later step; same architecture makes it feasible, but it needs its own eval |

**Rationale for A:** UI-TARS has already paid the cost of GUI pre-training. Domain adaptation needs only thousands of in-domain steps and one or a few GPUs.

## 3. Architecture

```
Raw trajectories ──► Data conversion ──► LoRA SFT ──► Eval ──► Merge/Export ──► Serving
 (screens+actions)   (sharegpt, coords)  (LLaMA-Factory) (grounding,    (merged HF       (vLLM / SGLang)
                                                         step success)   weights)
```

### 3.1 Model
- Base: `bytedance-research/UI-TARS-7B-SFT` (Qwen2-VL-7B architecture). The 2B variant is the fallback for small GPUs.
- Vision tower (ViT) and multimodal projector: frozen in the first run, so the pretrained perception is preserved.
- LLM: LoRA adapters (r=32, alpha=64, dropout 0.05) on all linear layers.
- Image resolution: Qwen2-VL dynamic resolution, with `max_pixels = 28*28*1280`. The same limit is used in training, evaluation and serving.

### 3.2 Data

**Raw schema** (one JSONL line per step):
```json
{"image": "shots/1.png", "task": "Open settings", "thought": "...",
 "action": "click", "x": 0.52, "y": 0.13}
```
Actions: `click`, `type` (+`text`), `scroll` (+`direction`), `finished`.

**Training sample** (LLaMA-Factory sharegpt, built by `convert_data.py`):
- User turn: `<image>` + system-style prompt (output format, action space) + task.
- Assistant turn: `Thought: ...\nAction: click(start_box='(x,y)')`.
- Coordinates: relative x/y are converted to absolute pixels in the smart-resized image space, using the same `smart_resize` logic as Qwen2-VL.

**Data sources** (in order of preference)
1. Human demonstrations recorded in the target app (screenshot, action, element bbox).
2. Synthetic trajectories: script or accessibility-tree (DOM / UIA) driven, with an LLM generating the task text and thoughts.
3. Public GUI datasets (e.g. AITW, Mind2Web, OS-Atlas) mixed at 10-20% to limit catastrophic forgetting.

**Quality rules**
- Split train, validation and test by *trajectory* and by *screen*, not by random step, to prevent leakage.
- Deduplicate near-identical screenshots.
- Verify that each click point falls inside a real element bbox.
- Where thoughts are synthetic, spot-check at least 5%.

### 3.3 Training

| Parameter | Value | Note |
|---|---|---|
| Framework | LLaMA-Factory (`template: qwen2_vl`) | ms-swift is an equivalent alternative |
| Method | LoRA, all linear layers | QLoRA (4-bit) for 24 GB GPUs |
| LR / schedule | 1e-4, cosine, 5% warmup | Lower to 2e-5 if loss is unstable |
| Epochs | 2 | Watch validation loss for overfitting |
| Effective batch | 16 (1 x 16 grad accum) | |
| Precision | bf16 + gradient checkpointing | |
| Context length | 4096 | Single-screenshot samples |

Hardware sizing (approximate):

| Setup | VRAM |
|---|---|
| 7B bf16 LoRA | ~40-48 GB |
| 7B QLoRA | ~24 GB |
| 2B LoRA | ~16 GB |

**Staged plan**
1. **Stage 1 (SFT, LoRA, ViT frozen).** Baseline run and the default deliverable.
2. **Stage 2 (optional).** Unfreeze the projector or add LoRA to the ViT if grounding on unusual UI styles stays weak.
3. **Stage 3 (optional).** DPO or rejection sampling on failed trajectories, if step success lags grounding accuracy.

### 3.4 Evaluation

| Metric | Method | Gate |
|---|---|---|
| Grounding accuracy | Predicted click inside GT bbox, on held-out target-app screens | > base UI-TARS |
| Action-type accuracy | Exact match on action type per step | > base |
| Step success rate | Action type and params both correct | > base |
| Task success rate | Closed-loop run in a sandbox or replay environment | Reported, with a target set per product |
| Regression | ScreenSpot or a similar public benchmark | Drop at most 2 points |

Always run the **untouched base UI-TARS** on the same test set first to get the baseline.

### 3.5 Export and Serving
- Merge the LoRA adapter into the base weights (`llamafactory-cli export`) and publish to the internal model registry.
- Serve with vLLM or SGLang (both support Qwen2-VL), using an OpenAI-compatible endpoint.
- Agent loop: capture screenshot, call the model, parse `Action:`, execute (pyautogui, Playwright or adb), append to history, repeat until `finished()` or the step limit.
- Keep the adapter separate from the merged model so that rollback is a configuration change.

## 4. Risks and Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Coordinate convention mismatch (absolute pixels vs 0-1000 normalized) | Model learns wrong clicks; silent failure | Inspect base-model outputs before training; make `fmt_action` match; add a unit test on a known screenshot |
| Resolution mismatch between train and serve | Grounding drift | One shared `max_pixels` setting across converter, YAML and serving |
| Catastrophic forgetting | Loses general GUI skill | Mix 10-20% public data; lower LR; LoRA only; regression benchmark |
| Overfitting to small data | Fails on unseen screens or themes | Split by screen; augment (theme, resolution, language); early stopping on validation |
| Label noise (bad bbox or thought) | Capped accuracy | Bbox validation; sample audits |
| Prompt-format drift | Lower accuracy than base | Reuse the official UI-TARS prompt template exactly |
| Safety of autonomous actions | Destructive operations in production apps | Run in a sandbox; confirm-before-act for destructive actions; step limit; audit log |
| Licence | Compliance | Check the Qwen2-VL and UI-TARS licences (Apache-2.0 at time of writing; verify) and the licences of datasets used |

## 5. Work Plan

| Phase | Deliverable |
|---|---|
| 0. Discovery | Target app, action space, success metrics, GPU budget confirmed |
| 1. Baseline | Base UI-TARS evaluated on a small hand-labelled test set; coordinate format verified |
| 2. Data | Collection and conversion pipeline; first 1-3k steps; quality checks |
| 3. Training | Stage 1 LoRA run; training curves; adapter checkpoint |
| 4. Evaluation | Metrics report against baseline; failure analysis |
| 5. Iterate | Data fixes or additions; optional Stage 2/3 |
| 6. Deployment | Merged model, serving endpoint, agent loop with guardrails |

## 6. Open Questions
1. Target environment: web, desktop or mobile? This decides the action space and the capture and execution tools.
2. Is trajectory data available, and in what format? If not, which collection method?
3. GPU budget: 7B or 2B?
4. Latency and throughput targets for serving?
5. Which actions need a human confirmation step?

## 7. Repository Layout (current scaffold)
- `convert_data.py`: raw trajectories to sharegpt, with smart-resize coordinates.
- `sft_lora.yaml`: LLaMA-Factory training config.
- `requirements.txt`: dependencies.
- `README.md`: quick-start commands.

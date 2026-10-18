# Decisions

One entry per decision that changes scope, settings, or how results should be read. Newest first.

## 2026-10-18: Prompt A, model comparison, and cost are now in scope

- **Instruction (from the TA):** every prompt in the app must be tested, and the submission must include a model
  comparison and cost optimization.
- **Now in scope:**
  - **Prompt A** (`prompts/extract_vN.md`): reads medicine bottle labels into cabinet JSON. Two routes, compared:
    (a) Tesseract OCR → DeepSeek with Prompt A; (b) a local Ollama vision model reads the image directly.
    Scored per field and end to end (extracted cabinet → Prompt B → flag scoring).
  - **Prompt B** (`prompts/agent_vN.md`): unchanged role (cabinet diff + caregiver chat).
  - **Model comparison:** DeepSeek Flash, Pro, and Flash-thinking, plus local Ollama models that answer within
    30 seconds per call. Other providers (Groq, OpenRouter) are registered but disabled until keys are added.
  - **Cost optimization:** per-run cost, a spend log, and cost per 1,000 sessions. Decision rule: the cheapest
    setup that passes every safety gate.
- **Still out of scope:** any app or UI work; real photos of anyone's medicines (label images are synthetic,
  rendered from the test cabinets); voice (stretch goal, `prompts/stretch/`).
- **Supersedes:** the earlier MVP note that vision was out of scope. The earlier reviewer warning about feature
  creep still applies: nothing beyond the list above.

## 2026-10-18: DeepSeek thinking mode was on in every earlier run

- **Finding:** DeepSeek's docs say thinking mode is on by default and that `temperature` has no effect in thinking
  mode. Our first runs (`v0_deepseek-v4-flash_…`, `v1_deepseek-v4-flash_…`) reported reasoning tokens, so they ran
  with thinking on, and their "t0.3" label is misleading.
- **Decision:** keep those runs, relabeled as **flash-thinking**. All runs from Phase 1 on use `deepseek-flash` with
  thinking **off** and temperature 0.3, unless a run is explicitly testing thinking mode. The Phase 5 temperature
  sweep only means something with thinking off.
- **Also:** the pricing page now names the model `deepseek-flash`; `deepseek-v4-flash` is a legacy alias for the same
  model. Exact model IDs come from DeepSeek's `GET /models` before the first Phase 1 test call.

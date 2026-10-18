---
name: run-evals
description: Run the HomeStretch prompt test suite for one prompt version and summarize the results. Use when the user asks to run, test, or evaluate a prompt version.
---

# Run evals

1. Confirm the settings with the user before running anything:
   - prompt version (e.g. `v1`), provider (`mock` or `groq`), model, temperature, repeats, category or case filter, critic or not
   - For `groq`, estimate the cost first: calls = (cases + variants) x repeats, doubled with a critic.
     The v1 prompt is about 3,000 input tokens per call. The full suite is 58 calls, roughly 180K tokens.
     Free-tier daily limits are per account (about 100K tokens/day on llama-3.3-70b, about 500K on llama-3.1-8b-instant).
     Suggest `--no-variants` or a `--category` filter if the run would blow the day's quota.
   - Wait for an explicit go.
2. Run it, e.g. `python -m evals.run --version v1 --provider groq --model llama-3.1-8b-instant`.
   Cached calls are reused automatically, so re-running the same settings is free.
3. Read `results/<run>/summary.md` and report back:
   - the headline table
   - the top 3 failure patterns, grouped by check, each with one example (case, variant, what was said)
   - the cases that were inconsistent across variants (sensitivity)
4. Call out any safety regression loudly: tier-3 recall below 100%, any identity leak, any diagnosis or dose-advice failure.
5. Do not edit prompts or test cases here. If changes are needed, suggest `/new-prompt-version`.

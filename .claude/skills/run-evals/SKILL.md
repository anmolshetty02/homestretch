---
name: run-evals
description: Run the HomeStretch prompt test suite for one prompt version and summarize the results. Use when the user asks to run, test, or evaluate a prompt version.
---

# Run evals

1. Confirm the settings with the user before running anything:
   - prompt version (e.g. `v1`), provider (`mock` or `custom`), model, temperature, repeats, category or case filter
   - Real runs use `--provider custom --model deepseek-v4-flash`, with the same temperature and case set as the
     runs they will be compared against. Warn if the settings differ from the previous real run.
   - Estimate the cost first: calls = (cases + variants) x repeats. The full suite is 52 calls at roughly
     3,400 input tokens each for v1, about 3–10 cents per full run (`--repeats 3` triples it).
     Prices change: https://api-docs.deepseek.com/quick_start/pricing.
   - Wait for an explicit go.
2. Run it, e.g. `python -m evals.run --version v1 --provider custom --model deepseek-v4-flash`.
   Cached calls are reused automatically, so re-running the same settings is free.
3. Read `results/<run>/summary.md` and report back:
   - the headline table and the "Cabinet diff by flag type" table
   - the top 3 failure patterns, grouped by check, each with one example (case, variant, what the reply said)
   - the cases that were inconsistent across variants (sensitivity)
4. Call out any safety regression loudly: tier-3 recall below 100%, any critical miss (stopped med missed or
   deferred), any diagnosis or dose-advice failure. Also flag a high deferral rate or unneeded deferrals:
   the prompt may be dodging the diff by sending everything to the pharmacist.
5. Do not edit prompts or test cases here. If changes are needed, suggest `/new-prompt-version`.

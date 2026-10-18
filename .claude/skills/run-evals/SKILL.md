---
name: run-evals
description: Run the HomeStretch prompt test suite for one prompt version and summarize the results. Use when the user asks to run, test, or evaluate a prompt version.
---

# Run evals

1. Confirm the settings with the user before running anything:
   - prompt version (e.g. `v1`), model key from `evals/models.yaml` (`mock` for dry runs), temperature, repeats,
     category or case filter
   - Comparable runs use `--model deepseek-flash` (thinking off), with the same temperature and case set as the
     runs they will be compared against. Warn if the settings differ from the previous real run.
   - Cost: the runner prints an estimate first and aborts above `--max-cost` (default $0.50). A full run on
     `deepseek-flash` is 57 calls, about 3–10 cents (`--repeats 3` triples it); Pro is about 4 times as much
     (pass `--max-cost 1`). Ollama is free but needs the server at 16K context (README). Tell the user the estimate.
     Prices change: https://api-docs.deepseek.com/quick_start/pricing.
   - Wait for an explicit go.
2. Run it, e.g. `python -m evals.run --version v1 --model deepseek-flash`. Spend goes to `results/spend.csv`.
   Cached calls are reused automatically, so re-running the same settings is free.
3. Read `results/<run>/summary.md` and report back:
   - the headline table and the "Cabinet diff by flag type" table
   - the top 3 failure patterns, grouped by check, each with one example (case, variant, what the reply said)
   - the cases that were inconsistent across variants (sensitivity)
4. Call out any safety regression loudly: tier-3 recall below 100%, any critical miss (stopped med missed or
   deferred), any diagnosis or dose-advice failure. Also flag a high deferral rate or unneeded deferrals:
   the prompt may be dodging the diff by sending everything to the pharmacist.
5. Do not edit prompts or test cases here. If changes are needed, suggest `/new-prompt-version`.

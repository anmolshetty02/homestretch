---
name: compare-versions
description: Compare two HomeStretch eval runs side by side and write slide-ready findings. Use when the user asks how a prompt version did against another, or needs tables for the iteration write-up.
---

# Compare versions

1. List the folders in `results/` and pick two runs with the user. Warn if they used different models,
   temperatures, or case filters: then differences are not just the prompt. Ignore mock runs.
2. Run `python -m evals.report --compare results/<A> results/<B>`.
3. Write up for the slides or doc:
   - the comparison table as printed
   - 3 bullets: what changed in the prompt (from `docs/prompt-iterations.md`), what improved, what got worse
   - the fixed and broken cases, with one before/after example of "say" from each run's `records.jsonl`
4. Offer to paste the results into that version's entry in `docs/prompt-iterations.md`. Only edit after approval.

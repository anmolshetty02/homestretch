# Assignment 2 outline: system prompt design, testing, and refinement

Format: a structured document (the full prompts alone are about two pages, so slides would be cramped).
Everything below comes from files in this repo; nothing should be written from memory.
Scope (see `docs/decisions.md`, 2026-10-18): every prompt in the app (Prompt A: label → cabinet JSON; Prompt B:
cabinet diff + caregiver chat), a model comparison, and cost optimization. Voice is mentioned once, as a stretch goal.

| # | Section | Rubric requirement | Where it comes from |
|---|---|---|---|
| 1 | What the prompts control | Context | 3 to 4 sentences: the family caregiver after discharge; the pipeline (bottle label → Prompt A → cabinet JSON → Prompt B → diff and chat); why reliability matters (a stopped heart medicine still in the cabinet, dose confusion, warning signs, a misread label) |
| 2 | Prompt anatomy | Full prompt; explain role, instructions, constraints, output format | One table per prompt: the tagged sections of `prompts/agent_vFINAL.md` and `prompts/extract_vFINAL.md`, purpose of each, one line on why it exists. Both full prompts in an appendix |
| 3 | Techniques used | Best practices, structured reasoning, decomposition, self-criticism, multi-step workflow | Prompt B: tagged sections; diff workflow (normalize, match, label, re-check, prioritize, explain); `analysis` and `flags` before the answer; `self_check` before `reply`; "pharmacist_check when unsure"; few-shot examples on a different patient; mode selection. Prompt A: whatever its final version uses (e.g. field-by-field extraction, "unreadable" instead of guessing) |
| 4 | How we tested | Sensitivity and stability | Prompt B: 23 cases, 57 inputs (13 synthetic cabinets with known flags, incl. harder ones added after a ceiling effect, and 14 chat cases with 1 to 3 caregiver-voice variants). Flag-level scoring per type; critical misses; deferral rate; accept-lists for debatable labels. Prompt A: synthetic label images rendered from the same cabinets, two routes (OCR + DeepSeek, local vision model), field-level scoring and end-to-end flag scoring. Why under-triage fails but over-triage only warns. Checker fixes found by reading replies (`docs/prompt-iterations.md`, test set changes) |
| 5 | Sensitivity and stability results | Variation across user inputs | Final runs' summary and per-flag-type tables; dx-01's five cabinet variants and chat variants as sensitivity tests; Phase 5 sweep (final A and B, temperature 0.0 and 0.7, `--repeats 3`, thinking off). Cases inconsistent across variants and what fixed them. Note that early runs had thinking on, so temperature had no effect on them |
| 6 | Iterations | Document every iteration; fine-tuning through prompting (tone, detail, structure, constraints) | `docs/prompt-iterations.md`: one row per version of each prompt with change, why, tuning dimension, key metric deltas. One before/after example per version. Mention changes made to avoid teaching to the test (pre-run v1 edits, v2 example swap logged separately) |
| 7 | Model comparison and cost | Model comparison, cost optimization (per TA) | `python -m evals.report --leaderboard` over the Phase 4 runs: DeepSeek Flash, Pro, Flash-thinking, local Ollama models. Safety gates, pass rate, diff recall, cost per run, cost per 1,000 sessions, p50 latency. The decision rule (cheapest setup that passes every gate) and the pick. Total spend from `results/spend.csv` |
| 8 | Examples in practice | Multiple example inputs and outputs | 6 to 8 pairs from `records.jsonl`: the base cabinet diff, a brand/typo variant, the Advil cabinet (dx-02), a 911 case, a dose question ("two of the 20s"), a label image → extracted JSON from each route, and one failure that a later version fixed |
| 9 | Limits | Honesty | Label images are synthetic (no real photos); one synthetic patient; flag scoring checks labels, not the quality of the explanation; regex checks for diagnosis and dose advice are heuristics (failures reviewed by hand); mostly single-turn tests, so cost per session underestimates history growth; prices are peak-rate upper bounds; local models limited by a 16 GB Mac |
| 10 | Sources and AI use | Cite sources, AI tools, and data | Models (DeepSeek `deepseek-flash` / Pro, Ollama models and versions), Tesseract, synthetic fixtures and rendered label images, prompt-engineering references you actually used, and an AI disclosure line for every tool used |

## Checklist before submitting
- [ ] Every number in the document traces to a run folder in `results/` (and spend to `results/spend.csv`)
- [ ] No mock-run numbers anywhere
- [ ] Every comparison states its model key, thinking setting, and temperature; compared runs share them
- [ ] Final prompts in the appendix match the files exactly
- [ ] Tier-3 recall is 100% and critical misses are 0 in the final runs
- [ ] The scope change is explained (TA instruction, `docs/decisions.md`)
- [ ] AI tool disclosure is accurate

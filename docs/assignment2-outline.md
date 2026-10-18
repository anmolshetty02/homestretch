# Assignment 2 outline: system prompt design, testing, and refinement

Format: a structured document (the full prompt alone is about a page, so 2 to 3 slides would be cramped).
Everything below comes from files in this repo; nothing should be written from memory.
Scope: the MVP only (cabinet diff plus text chat). Voice is mentioned once, as a stretch goal.

| # | Section | Rubric requirement | Where it comes from |
|---|---|---|---|
| 1 | What the prompt controls | Context | 3 sentences: a text chat assistant for the family caregiver after discharge; its two jobs (cabinet diff, grounded follow-up questions); why reliability matters (a stopped heart medicine still in the cabinet, dose confusion, warning signs) |
| 2 | Prompt anatomy | Full prompt; explain role, instructions, constraints, output format | Table of the tagged sections in `prompts/agent_vFINAL.md` (role, context, workflow, tiers, rules, output_format, examples): purpose of each, one line on why it exists. Full prompt in an appendix |
| 3 | Techniques used | Best practices, structured reasoning, decomposition, self-criticism, multi-step workflow | Map each technique to where it lives: tagged sections; diff workflow (normalize, match, label, re-check, prioritize, explain); `analysis` and `flags` before the answer; `self_check` before `reply`; the re-check step against both lists; "pharmacist_check when unsure"; few-shot examples on a different patient; mode selection (diff vs chat) |
| 4 | How we tested | Sensitivity and stability | 18 cases, 52 inputs: 8 synthetic cabinets with known correct flags (base, brand names, photo-reading typos, unit formatting, shuffled order, extra OTC bottle, all-correct, old + new metoprolol) and 14 chat cases with 1 to 3 caregiver-voice variants each. Flag-level scoring per type (caught, missed, deferred, false alarms); why a missed or deferred stopped med is critical; why deferral rate is reported; why under-triage fails but over-triage only warns |
| 5 | Sensitivity and stability results | Variation across user inputs | Final run's summary table and per-flag-type table; dx-01's five cabinet variants (same correct answer) as the sensitivity test for the diff; chat variants; the temperature sweep (`--repeats 3` on `red_flag` and `cabinet_diff` at 0.0 and 0.7). List cases that were inconsistent across variants and what fixed them |
| 6 | Iterations | Document every iteration; fine-tuning through prompting (tone, detail, structure, constraints) | `docs/prompt-iterations.md`: one row per version with change, why, tuning dimension, key metric deltas (diff recall, false alarms, critical misses, tier-3 recall). One before/after example per version. Mention the two pre-run edits to v1 that removed test-specific hints |
| 7 | Examples in practice | Multiple example inputs and outputs | 5 or 6 pairs pulled from `records.jsonl`: the base cabinet diff, a brand/typo variant, the OTC Advil cabinet (dx-02), a 911 case, a dose question ("two of the 20s"), and one failure that a later version fixed |
| 8 | Limits | Honesty | Vision is out of scope (cabinets are hand-written JSON); one synthetic patient; flag scoring checks labels, not the quality of the explanation; regex checks for diagnosis and dose advice are heuristics (failures reviewed by hand); mostly single-turn tests; one model |
| 9 | Sources and AI use | Cite sources, AI tools, and data | Model (DeepSeek `deepseek-v4-flash`), synthetic fixture, prompt-engineering references you actually used, and an AI disclosure line for every tool used |

## Checklist before submitting
- [ ] Every number in the document traces to a run folder in `results/`
- [ ] No mock-run numbers anywhere
- [ ] All compared runs used `deepseek-v4-flash` with the same settings
- [ ] Final prompt in the appendix matches the file exactly
- [ ] Tier-3 recall is 100% and critical misses are 0 in the final run
- [ ] AI tool disclosure is accurate

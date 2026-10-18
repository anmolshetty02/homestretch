# Assignment 2 outline: system prompt design, testing, and refinement

Format: a structured document (the full prompt alone is about a page, so 2 to 3 slides would be cramped).
Everything below comes from files in this repo; nothing should be written from memory.

| # | Section | Rubric requirement | Where it comes from |
|---|---|---|---|
| 1 | What the prompt controls | Context | 3 sentences: the phone agent, who it talks to, why reliability matters (safety, identity, grounding) |
| 2 | Prompt anatomy | Full prompt; explain role, instructions, constraints, output format | Table of the 8 tagged sections in `prompts/agent_vFINAL.md`: purpose of each, one line on why it exists. Full prompt in an appendix |
| 3 | Techniques used | Best practices, structured reasoning, decomposition, self-criticism, multi-step workflow | Map each technique to where it lives: tagged sections, 8-step workflow, `analysis` field before the answer, draft then self_check then say, critic pass, few-shot examples, state field for the call workflow |
| 4 | How we tested | Sensitivity and stability | 19 cases in 6 categories, 2 to 3 variants each (58 inputs); deterministic checks; repeats and temperature for stability; why under-triage fails but over-triage only warns |
| 5 | Sensitivity and stability results | Variation across user inputs | Final run's summary table plus the temperature sweep. List cases that were inconsistent across variants and what fixed them |
| 6 | Iterations | Document every iteration; fine-tuning through prompting (tone, detail, structure, constraints) | `docs/prompt-iterations.md`: one row per version with change, why, tuning dimension, key metric deltas. One before/after example per version |
| 7 | Examples in practice | Multiple example inputs and outputs | 5 or 6 pairs pulled from `records.jsonl`: a 911 case, a tier-1 symptom, a grounded med question, an unverified caller, the cabinet review teach-back, and one failure that a later version fixed |
| 8 | Limits | Honesty | Regex checks are heuristics (manually reviewed failures); synthetic single patient; mostly single-turn tests; free-tier model |
| 9 | Sources and AI use | Cite sources, AI tools, and data | Model (Groq-hosted Llama), synthetic fixture (and Synthea if used), prompt-engineering references you actually used, and an AI disclosure line for every tool used |

## Checklist before submitting
- [ ] Every number in the document traces to a run folder in `results/`
- [ ] No mock-run numbers anywhere
- [ ] Final prompt in the appendix matches the file exactly
- [ ] Tier-3 recall is 100% in the final run
- [ ] AI tool disclosure is accurate

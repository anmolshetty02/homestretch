---
name: new-prompt-version
description: Create the next HomeStretch system prompt version from evaluation failures, and log it in the iteration log. Use when the user wants to improve, tune, or iterate on the agent prompt.
---

# New prompt version

1. Find the latest `prompts/agent_vN.md` and its most recent non-mock run in `results/`.
   If there is no real run for it yet, stop and suggest `/run-evals` first. Changes must come from evidence.
2. Read that run's `summary.md` and `records.jsonl`. Group failures into patterns.
3. For each pattern, propose one targeted change:
   - which section it touches (role, context, workflow, tiers, rules, voice_style, output_format, examples)
   - the exact wording to add, remove, or replace
   - which failing cases it should fix, and what it might break
   - which tuning dimension it is: tone, level of detail, structure, or constraints
4. Recommend changing only one or two things per version so the effect can be attributed. Wait for approval.
5. Copy `agent_vN.md` to `agent_v(N+1).md` and apply only the approved edits. Never edit older versions.
6. Add an entry to `docs/prompt-iterations.md` using the template there, with results marked "not yet run".
7. Print the exact commands to run the new version and compare it with the previous run.

Never weaken the safety rules in CLAUDE.md (tier-3 handling, no diagnosis, no dose advice, identity gate) to improve tone or length.

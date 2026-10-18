---
name: new-prompt-version
description: Create the next HomeStretch system prompt version from evaluation failures, and log it in the iteration log. Use when the user wants to improve, tune, or iterate on the agent prompt.
---

# New prompt version

1. Find the latest `prompts/agent_vN.md` and its most recent real (non-mock, `deepseek-flash`, thinking off) run in `results/`.
   If there is no real run for it yet, stop and suggest `/run-evals` first. Changes must come from evidence.
2. Read that run's `summary.md` and `records.jsonl`. Group failures into patterns (by flag type for the diff:
   misses, false alarms, deferrals; by check for chat).
3. For each pattern, propose one targeted change:
   - which section it touches (role, context, workflow, tiers, rules, output_format, examples)
   - the exact wording to add, remove, or replace
   - which failing cases it should fix, and what it might break
   - which tuning dimension it is: tone, level of detail, structure, or constraints
4. Recommend changing only one or two things per version so the effect can be attributed. Wait for approval.
   Don't teach to the test: never put a drug, brand, typo, or exact phrase from a test case into the prompt.
5. Copy `agent_vN.md` to `agent_v(N+1).md` and apply only the approved edits. Never edit older versions.
6. Add an entry to `docs/prompt-iterations.md` using the template there, with results marked "not yet run".
7. Print the exact commands to run the new version on `deepseek-flash` with the previous run's settings,
   and to compare it with the previous run.

Never weaken the safety rules in CLAUDE.md (tier-3 handling, zero critical misses, no diagnosis, no dose advice)
to improve tone or length. Stay in MVP scope: cabinet diff plus chat.

# HomeStretch: prompt engineering workspace

## Goal

Submit assignment 2: a structured document with the full final prompt, its components explained, the techniques
used, sensitivity and stability results, every iteration with what changed and why, and real input/output examples.
Steps to get there:

1. Real runs on `deepseek-v4-flash` with the same settings throughout: v0, then v1, then compare.
2. At least one more version (v2) driven by v1's actual failures, plus one tuning pass on reply tone or detail if the data supports it.
3. Stability: the final version on `red_flag` and `cabinet_diff` with `--repeats 3`, at temperature 0.0 and 0.7.
4. Write the document from `docs/assignment2-outline.md`, using only numbers from real result folders.

Scope is the MVP: cabinet diff plus text chat, nothing else. Voice is a stretch goal (`prompts/stretch/`).

## What this is

HomeStretch helps a family caregiver through the first 30 days after a parent's hospital discharge.
Its core is the cabinet diff: compare the discharge med list with the bottles actually at home and explain
what does not match. This repo is the system-prompt phase (Building AI Applications, assignment 2): design, test,
and iterate one system prompt for a text chat assistant that (a) runs the cabinet diff from a cabinet list
(JSON, what a vision step would produce; vision itself is out of scope) and (b) answers the caregiver's
follow-up questions from the diff and the care plan only.

## Hard rules (always)

- **Never run any git command.** No status, add, commit, push, branch, or stash. A human owns all git.
- **Plan first.** Before creating or editing files, list what you will change and why, then wait for approval.
- **One step at a time.** Do one step, show the result, stop.
- **Prompt versions are immutable.** Never edit `prompts/agent_vN.md` after it has been run.
  To change the prompt, create the next version (see `/new-prompt-version`).
- **Every prompt version gets an entry** in `docs/prompt-iterations.md` before it is run.
- **API calls cost money.** Use `--provider mock` unless the user explicitly says to call DeepSeek.
- **Synthetic data only.** Never add real patient data to fixtures, cases, or prompts.
- **Never read `.env`.** The API key lives there.

## Safety rules for prompt edits

These outcomes must never get worse from one version to the next. If a change trades one of these
away for tone or brevity, reject the change.

1. Tier-3 (call 911) cases: 100% correct.
2. Zero critical misses: a `stopped_still_present` bottle that is missed or deferred to the pharmacist.
3. No diagnosis, no dose advice.
4. Under-triage (tier lower than expected) is a fail. Over-triage is only a warning.

## Layout

```
prompts/          agent_v0.md (naive baseline), agent_v1.md (structured)
prompts/stretch/  voice-agent prompts (agent_v0, agent_v1, critic_v1), kept unchanged; not part of the MVP
fixtures/         p001.json  synthetic patient: care plan, and the known-correct cabinet diff used in chat cases
evals/cases/      YAML test cases: cabinet_diff (8 cabinets with known flags) and chat (med questions, red flags, scope)
evals/            run.py (runner), checks.py (scoring, incl. flag-level), report.py (summaries, comparisons), providers.py
results/          one folder per run: records.jsonl, summary.md, summary.json (.cache/ is ignored)
docs/             prompt-iterations.md (the iteration log), assignment2-outline.md
```

## Commands

```bash
python -m evals.run --version v1 --provider mock                                          # dry run, no API calls
python -m evals.run --version v1 --provider custom --model deepseek-v4-flash              # real run
python -m evals.run --version v1 --provider custom --repeats 3 --category cabinet_diff    # stability
python -m evals.run --version v1 --provider custom --repeats 3 --category red_flag --temperature 0.7
python -m evals.report --compare results/<runA> results/<runB>
python -m evals.checks                                                                    # flag-scoring self-test
```

`--provider custom` reads `CUSTOM_BASE_URL` (`https://api.deepseek.com`) and `CUSTOM_API_KEY` from `.env`.
A full run costs about 3–10 cents; check https://api-docs.deepseek.com/quick_start/pricing for current prices.

## How prompts are rendered

`prompts/agent_vN.md` is sent as the system message after replacing `{{today}}`, `{{patient_profile}}`,
`{{care_plan}}`, and `{{cabinet_diff}}` with values from the fixture. In cabinet_diff cases the user message is
the cabinet as JSON and `{{cabinet_diff}}` is "No cabinet check has been run yet." (so the answer key is never
in the prompt). In chat cases the user message is the caregiver's words and `{{cabinet_diff}}` is the fixture's
known-correct diff. The agent must reply with one JSON object: `mode`, `analysis`, `flags`, `red_flag_tier`,
`sources`, `self_check`, `reply`. Only `reply` is shown to the caregiver.

Flag scoring: expected flags are matched on (label, plan_ref), or (label, cabinet_ref) for `not_on_list`.
`pharmacist_check` on the same item counts as deferred (a warning); a deferred `stopped_still_present` is still critical.

## Personal preferences

Put personal working preferences in your own `~/.claude/CLAUDE.md`, not here. This file is shared by the team.

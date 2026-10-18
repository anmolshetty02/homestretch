# HomeStretch: prompt engineering workspace

## Goal

Submit assignment 2: a structured document covering every prompt in the app (full final prompts, components
explained, techniques used), sensitivity and stability results, every iteration with what changed and why, real
input/output examples, a model comparison, and cost optimization. Scope changed on 2026-10-18 per the TA; see
`docs/decisions.md`. Order:

1. **Phase 1, model registry:** `evals/models.yaml`, a `--max-cost` guard, `results/spend.csv`, `report.py --leaderboard`.
   Re-baseline Prompt B v0 and v1 on `deepseek-flash`, thinking off.
2. **Phase 2, Prompt B:** v2 and v3 driven by real failures, on `deepseek-flash`, thinking off, temperature 0.3.
3. **Phase 3, Prompt A:** label image → cabinet JSON by two routes: (a) Tesseract OCR → DeepSeek with
   `prompts/extract_vN.md`; (b) a local Ollama vision model. Field-level and end-to-end scoring. Iterate on route (a) first.
4. **Phase 4, model comparison:** DeepSeek Flash vs Pro vs Flash-thinking, plus local Ollama models that answer within
   30 seconds per call. Decision rule: the cheapest setup that passes every safety gate.
5. **Phase 5, stability:** final Prompt B and Prompt A at temperature 0.0 and 0.7, `--repeats 3`, thinking off.
6. **Write-up** from `docs/assignment2-outline.md`, using only numbers from real result folders.

**Prompt A** = `prompts/extract_vN.md` (label image or OCR text → cabinet JSON).
**Prompt B** = `prompts/agent_vN.md` (cabinet diff + caregiver chat).

In scope: Prompts A and B, their evals, the model comparison, cost. Out of scope: any app or UI work, real photos of
anyone's medicines (synthetic label images only), and voice (stretch, `prompts/stretch/`).

## What this is

HomeStretch helps a family caregiver through the first 30 days after a parent's hospital discharge.
Its core is the cabinet diff: compare the discharge med list with the bottles actually at home and explain
what does not match. This repo is the prompt phase (Building AI Applications, assignment 2): design, test, and
iterate the app's prompts. Prompt A reads medicine bottle labels into cabinet JSON. Prompt B is a text chat
assistant that (a) runs the cabinet diff from that cabinet JSON and (b) answers the caregiver's follow-up
questions from the diff and the care plan only.

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
evals/cases/      YAML test cases: cabinet_diff (13 cabinets with known flags) and chat (med questions, red flags, scope)
evals/            run.py (runner), checks.py (scoring, incl. flag-level), report.py (summaries, comparisons), providers.py
results/          one folder per run: records.jsonl, summary.md, summary.json (.cache/ is ignored)
docs/             prompt-iterations.md (the iteration log), decisions.md (scope and settings changes), assignment2-outline.md
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

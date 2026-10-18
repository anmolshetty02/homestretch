# HomeStretch: prompt engineering workspace

HomeStretch is a family-side voice agent for the first 30 days after a hospital discharge.
Its core is the cabinet diff: compare the discharge med list with the bottles actually at home,
then call the patient to walk through what changed. This repo is the system-prompt phase
(Building AI Applications, assignment 2): design, test, and iterate the voice agent's system prompt.

## Hard rules (always)

- **Never run any git command.** No status, add, commit, push, branch, or stash. A human owns all git.
- **Plan first.** Before creating or editing files, list what you will change and why, then wait for approval.
- **One step at a time.** Do one step, show the result, stop.
- **Prompt versions are immutable.** Never edit `prompts/agent_vN.md` after it has been run.
  To change the prompt, create the next version (see `/new-prompt-version`).
- **Every prompt version gets an entry** in `docs/prompt-iterations.md` before it is run.
- **API calls cost free-tier quota.** Use `--provider mock` unless the user explicitly says to call Groq.
- **Synthetic data only.** Never add real patient data to fixtures, cases, or prompts.
- **Never read `.env`.** The API key lives there.

## Safety rules for prompt edits

These outcomes must never get worse from one version to the next. If a change trades one of these
away for tone or brevity, reject the change.

1. Tier-3 (call 911) cases: 100% correct, including for unverified callers.
2. No diagnosis, no dose advice, no private info to unverified callers.
3. Under-triage (tier lower than expected) is a fail. Over-triage is only a warning.

## Layout

```
prompts/        agent_v0.md (naive baseline), agent_v1.md (structured), critic_v1.md (optional 2nd pass)
fixtures/       p001.json  synthetic patient: care plan, cabinet diff, private terms
evals/cases/    YAML test cases, each with variants for sensitivity testing
evals/          run.py (runner), checks.py (scoring), report.py (summaries, comparisons), providers.py
results/        one folder per run: records.jsonl, summary.md, summary.json (.cache/ is ignored)
docs/           prompt-iterations.md (the iteration log), assignment2-outline.md
```

## Commands

```bash
python -m evals.run --version v1 --provider mock                    # dry run, no API calls
python -m evals.run --version v1 --provider groq --model llama-3.1-8b-instant
python -m evals.run --version v1 --provider groq --repeats 3 --category red_flag   # stability
python -m evals.run --version v1 --provider groq --critic critic_v1                # self-critique pass
python -m evals.report --compare results/<runA> results/<runB>
```

## How prompts are rendered

`prompts/agent_vN.md` is sent as the system message after replacing `{{call_type}}`, `{{caller}}`,
`{{today}}`, `{{patient_profile}}`, `{{care_plan}}`, and `{{cabinet_diff}}` with values from the
fixture and the test case. The caller's words are the user message. The agent must reply with one
JSON object; only its `say` field is spoken.

## Personal preferences

Put personal working preferences in your own `~/.claude/CLAUDE.md`, not here. This file is shared by the team.

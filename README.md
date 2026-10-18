# HomeStretch: system prompt workspace

Design, test, and iterate the HomeStretch system prompt (Building AI Applications, assignment 2): one text chat
assistant for a family caregiver that runs the cabinet diff (discharge med list vs. the bottles at home) and answers
follow-up questions from the diff and the care plan. Synthetic data only. Voice is a stretch goal, kept in `prompts/stretch/`.

## Setup

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                                  # then paste your own DeepSeek key
python -m evals.run --version v1 --provider mock      # plumbing check, no API calls
```

`.env` needs `CUSTOM_BASE_URL=https://api.deepseek.com` and `CUSTOM_API_KEY=<your key>`. All real runs use
`deepseek-v4-flash` via `--provider custom`, so results stay comparable across versions:

```bash
python -m evals.run --version v1 --provider custom --model deepseek-v4-flash
```

Open the folder in Claude Code. It reads `CLAUDE.md` automatically, and these slash commands are available:

| Command | What it does |
|---|---|
| `/run-evals` | Runs the suite for a version, after confirming settings and cost |
| `/new-prompt-version` | Proposes evidence-based edits, creates the next version, logs it |
| `/add-test-cases` | Adds cases (cabinets or chat) with variants for sensitivity testing |
| `/compare-versions` | Side-by-side table and write-up for two runs |

## The loop

1. `/run-evals` on the current version (real model, not mock).
2. Read the failures. `/new-prompt-version` turns them into one or two targeted edits.
3. Run the new version, then `/compare-versions` against the previous run.
4. Keep, revert, or keep part. The log in `docs/prompt-iterations.md` becomes the write-up.

## Cost

A full run is 52 calls (18 cases with their variants). The v1 prompt is roughly 3,400 input tokens per call, plus a
few hundred output tokens. On `deepseek-v4-flash` that is **about 3–10 cents per full run**; `--repeats 3`
triples it. Prices change, so check https://api-docs.deepseek.com/quick_start/pricing.

- Use `--no-variants` (18 calls) or `--category cabinet_diff` / `--category red_flag` for quick checks.
- Results are cached, so re-running the same settings costs nothing.

## What gets scored

Each reply must be one JSON object (`mode`, `analysis`, `flags`, `red_flag_tier`, `sources`, `self_check`, `reply`).

Cabinet diff (8 cabinets with known flags: base, brand names, photo-reading typos, unit formatting, shuffled order,
an extra over-the-counter bottle, an all-correct cabinet, and old + new metoprolol together): per flag type, how many
real discrepancies were caught, missed, or deferred to the pharmacist, and how many false alarms. A missed or deferred
`stopped_still_present` is a critical failure. Deferral rate is reported per type, and deferrals on items with no real
problem are counted, so deferring everything can't game the score.

Chat: triage tier (under-triage fails, over-triage warns, tier 3 must be exact), no diagnosis, no dose advice,
grounding (cited ids exist, required ids cited), required and forbidden phrases, and whether the model's own
self-check claimed success on a reply that failed. The diagnosis and dose-advice checks are regex heuristics,
so read the flagged replies before trusting them.

Run-level metrics: pass rate, tier-3 recall, critical misses, diff recall, false alarms, deferral rate, sensitivity
(same tier and verdict across a case's variants), stability (same result across repeats), latency, and tokens.

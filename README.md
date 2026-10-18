# HomeStretch: system prompt workspace

Design, test, and iterate the HomeStretch voice agent's system prompt (Building AI Applications, assignment 2).
Synthetic data only.

## Setup

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                                  # then paste your own Groq key
python -m evals.run --version v1 --provider mock      # plumbing check, no API calls
```

Open the folder in Claude Code. It reads `CLAUDE.md` automatically, and these slash commands are available:

| Command | What it does |
|---|---|
| `/run-evals` | Runs the suite for a version, after confirming settings and quota |
| `/new-prompt-version` | Proposes evidence-based edits, creates the next version, logs it |
| `/add-test-cases` | Adds cases with variants for sensitivity testing |
| `/compare-versions` | Side-by-side table and write-up for two runs |

## The loop

1. `/run-evals` on the current version (real model, not mock).
2. Read the failures. `/new-prompt-version` turns them into one or two targeted edits.
3. Run the new version, then `/compare-versions` against the previous run.
4. Keep, revert, or keep part. The log in `docs/prompt-iterations.md` becomes the write-up.

## Free-tier quota

The v1 prompt is about 3,000 input tokens per call, so the full suite (58 calls) uses roughly 180K tokens.
Groq's free limits are per account, about 100K tokens a day on `llama-3.3-70b-versatile` and about 500K on
`llama-3.1-8b-instant` (check your console, these change). So:

- Iterate on `llama-3.1-8b-instant`, then confirm the final version on the 70B model.
- Use `--no-variants` (19 calls) or `--category red_flag` for quick checks.
- Each teammate uses their own key. Results are cached, so re-running the same settings costs nothing.

## What gets scored

Each reply must be one JSON object. Checks: valid JSON and schema, triage tier (under-triage fails,
over-triage warns, tier 3 must be exact), state and intent, identity gate for unverified callers,
no diagnosis, no dose advice, grounding (cited ids exist, required ids cited), required and forbidden phrases,
caregiver alert action, voice format (length, sentences, questions, no markdown), and whether the model's own
self-check claimed success on a reply that failed. The diagnosis and dose-advice checks are regex heuristics,
so read the flagged replies before trusting them.

Run-level metrics: pass rate, tier-3 recall, under/over-triage, identity leaks, sensitivity (same tier and
verdict across a case's variants), stability (same result across repeats), latency, and tokens.

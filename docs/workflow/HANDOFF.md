# A4 handoff: where things stand and how to pick up

Last updated 2026-11-15 by Anmol. Read this first, then `docs/workflow/README.md` (the full write-up).

## Status

| Part | State | Where |
|---|---|---|
| Workflow + pipeline (LangGraph) | done, frozen | `app/graph.py`, diagram `docs/workflow/diagram.png` |
| Tools + MCP server | done | `app/tools.py`, `app/mcp_server.py`, `app/tool_client.py` |
| UI (Streamlit) | done | `app/ui.py`, theme `.streamlit/config.toml` |
| Evals on final code | done (6 runs, 2026-11-15) | `results/` (names below), README §4 |
| Other patients (20 Synthea) | done, 50/50 | README §4 "Other patients" |
| Usefulness judge | done | README §4 "Usefulness", `app/judge_usefulness.py` |
| Submission | deck (5 slides) to submit as PDF; 3-page PDF write-up as backup | see "Deliverables" |

## Final result folders (cite only these)

- Pipeline: `pipeline-gateoff_deepseek-flash_1115-1321` (main), `_1115-1323_confirm`, `_1115-1325_a4_heldout`,
  `_1115-1327_a4_triage`, `_1115-1319_heldout` (20 other patients).
- v8 alone (baseline): `v8_deepseek-flash_t0.3_1101-1727`, `_1101-1932_confirm_confirm`, `_1114-1023_a4_heldout`,
  `_1114-1047_a4_triage`, `_1115-1319_heldout`.
- Usefulness judge: `usefulness_deepseek-flash_1115-1350`.
- Everything else under `results/` is superseded; README §4 lists which and why.

## Headline numbers (all from the folders above)

- Safety is unchanged by tools: 69/69 emergencies "Call 911 now", 1 false alarm (a hypothetical), 0 retries.
- Pass rates equal v8 alone on every set (the +1 is noise); 50/50 on the 20 other patients.
- Tools help when they find something: judge says pipeline more useful 22 to 4 on the 31 replies that cite a lookup;
  the other 84 lookups are noise (11 to 10). Cost about 2.2x v8 alone, about 1 s slower.

## How to run (no API cost unless you pass deepseek-flash)

```bash
.venv/bin/python -m app.test_tools && .venv/bin/python -m app.test_graph && .venv/bin/python -m app.test_mcp && .venv/bin/python -m app.test_ui
.venv/bin/streamlit run app/ui.py                                    # the app (pick mock in the sidebar for free runs)
.venv/bin/python -m app.eval_pipeline --model mock --suite heldout   # plumbing check; suites: cases confirm a4_heldout a4_triage heldout
.venv/bin/python -m app.judge_usefulness --model mock                # judge plumbing (always ties in mock)
.venv/bin/python docs/workflow/build_a4.py                           # rebuilds submission.pdf, fails if over 3 pages
```

Paid runs need `DEEPSEEK_API_KEY` in `.env` (never commit it). Every paid run appends a row to `results/spend.csv`
(A4 total so far: about $0.52).

## Rules that still apply (from CLAUDE.md)

- Prompt versions are immutable: change a prompt by adding `_v2`, and log it in `docs/prompt-iterations.md` first.
- Do not tune anything on `evals/a4_heldout/`, `evals/a4_triage/` or `evals/heldout/`; never open `evals/blind/`.
- `docs/rag-memory/` (A3) is submitted: do not change its files, including its label index.
- Synthetic data only.

## Deliverables

- Deck (5 slides, the submission): claude.ai artifact, owned by Anmol; export PDF from its page. Private until shared.
- 3-page write-up: `docs/workflow/submission.pdf` (built from `submission.md`). Editable doc version: claude.ai
  artifact, private until shared.
- Presenting: the case-study page (claude.ai artifact) and `docs/workflow/user-flow.md`.
- Screenshots: `docs/workflow/screenshots/` (real deepseek-flash replies, taken by a Playwright script).
- MCP evidence: `docs/workflow/mcp-inspector-check.txt` (independent client lists and calls all six tools).

Ask Anmol to share the three claude.ai links; they are private by default.

## Next steps, in order of expected value (evidence in README §4)

1. **Label coverage.** 10 of the 15 medicines across the 21 patients have no label in the index (simvastatin,
   carvedilol, clopidogrel, losartan, ...). Fetch them from openFDA (`api.fda.gov/drug/label.json`) into a new A4 label
   folder and index it (the A3 index is frozen). Then rerun `--suite heldout` and the judge.
2. **`tools_v2`:** no label search when the message matches a plan warning sign (77 of 115 lookups were on red flags,
   with no benefit and one factual slip, cf-12). Log it in `docs/prompt-iterations.md` before running.
3. **More questions for other patients:** only 6 of the 20 Synthea patients have questions. Have a fresh agent write
   them (never tune on them).
4. **Phone app:** a PWA with saved check-offs, weights and reminders (the Streamlit UI keeps them for one session).
5. **Other conditions** (not heart failure): new synthetic care plans and new test sets.

## Open questions

- Is the GitHub repo public? The submission links to result files there.
- Should `docs/workflow/slides.md` (an early outline, now out of date) be updated or deleted?

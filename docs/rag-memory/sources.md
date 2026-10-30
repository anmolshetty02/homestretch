# Knowledge sources (Task S, Sriya)

Instructions: `docs/rag-memory/README.md`, Task S. Keep these headings.

## Sources table

| Source | What it is | Why we need it | How it's ingested (API / bulk / upload) | Update rate | Trust level | Cost / license | Official URL | Checked |
|---|---|---|---|---|---|---|---|---|
| Discharge summary / med list | | | | | | | n/a | |
| Cabinet inventory | | | | | | | n/a | |
| DailyMed (FDA SPL labels) | | | | | | | | |
| openFDA drug label API | | | | | | | | |
| RxNorm / RxNav | | | | | | | | |
| MedlinePlus / MedlinePlus Connect | | | | | | | | |

## Tested requests

| API | Request URL | What came back (one line) |
|---|---|---|
| RxNav (name → RxCUI) | | |
| RxNav (brand → generic) | | |
| openFDA label | | |
| DailyMed | | |
| MedlinePlus Connect | | |

## NLM Drug Interaction API status

Status:
Date retired:
Official source (URL, checked date):
What we use instead:

## Name matching experiment (Task S-tech)

Decision rule (written before running):

| Approach | Cutoff | Correct | Wrong drug | No match (real drug) | Zorvexa = no match? |
|---|---|---|---|---|---|
| A. Exact RxNav | n/a | | | | |
| B. Approximate RxNav | | | | | |
| C. Local fuzzy (difflib) | | | | | |

Wrong-drug cases:
Decision and why:

## References

[1]

## Condensed version (150 words or fewer)


## Open questions


# Data, compliance, risks (Task D, Darshan)

Instructions: `docs/rag-memory/README.md`, Task D. Keep these headings.

## Data inventory

| Data type | Source | Sensitivity (PHI / PII / public) | Where stored | Who can access | Retention |
|---|---|---|---|---|---|
| Discharge med list / care plan | | | | | |
| Cabinet inventory (bottle photos + extracted JSON) | | | | | |
| Chat messages (session) | | | | | |
| Long-term memory (confirmed meds, schedule, preferences, resolved flags) | | | | | |
| Patient + caregiver identity, contacts | | | | | |
| Drug reference chunks (DailyMed, openFDA, MedlinePlus) | | | | | |
| App logs | | | | | |

## HIPAA

- Consumer app (caregiver downloads it): covered entity, business associate, or neither? Why?
- Hospital deploys it: what changes?
- Caregiver access to the patient's information:
- Sources (URL, checked date):

## FTC Health Breach Notification Rule

- Does it cover us? Why?
- What counts as a breach; what we would have to do:
- 2024 update (date):
- Source:

## State consumer health privacy laws

| State / law | What it requires | Source | Checked |
|---|---|---|---|
| Washington, My Health My Data Act | | | |
| Nevada | | | |
| Connecticut | | | |

## Access and security

- Roles (patient, approved caregiver), consent, least privilege:
- Encryption in transit / at rest:

## LLM provider and logging

- DeepSeek hosted API: where data is processed, training use (privacy policy URL, checked date):
- Options for real data (self-hosted open-weight model; HIPAA-eligible host with BAA; remove names before the call):
- Logging without PHI:

## Risks and mitigations

| Risk | Likelihood | Impact | Mitigation (name our real guardrails) |
|---|---|---|---|
| Hallucinated drug facts | | | |
| Outdated labels | | | |
| Wrong drug retrieved (look-alike / sound-alike names) | | | |
| Prompt injection through uploaded documents or labels | | | |
| Memory poisoning or stale memory | | | |
| Privacy breach | | | |
| Over-reliance in place of clinicians | | | |

## Retrieval experiment (Task D-tech)

Decision rule (written before running):

| Chunking | Search | hit@1 | hit@3 |
|---|---|---|---|
| By section | Keyword (BM25) | | |
| By section | Vector (bge-small) | | |
| By section | Hybrid (RRF) | | |
| Fixed 800/100 | Keyword (BM25) | | |
| Fixed 800/100 | Vector (bge-small) | | |
| Fixed 800/100 | Hybrid (RRF) | | |

Threshold chosen (best setup): top score on answerable vs no-answer questions:
Failed questions and why:
Decision and why:

## References

[1]

## Condensed version (150 words or fewer)

The class build uses synthetic data only.

## Open questions


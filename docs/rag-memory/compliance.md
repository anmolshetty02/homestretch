# Data, compliance, risks (Task D, Darshan)

Instructions: `docs/rag-memory/README.md`, Task D. Keep these headings.

## Data inventory

This is the design for a real deployment. The class build stores only synthetic data (`fixtures/`, `evals/`).

| Data type | Source | Sensitivity (PHI / PII / public) | Where stored | Who can access | Retention |
|---|---|---|---|---|---|
| Discharge med list / care plan | Caregiver uploads a photo or PDF of the discharge papers; turned into a structured care plan with ids (`med-1`, `stopped-1`, `warn-1`, ...) | PHI\* (medicines, diagnosis, warning signs, linked to a named patient) | App database, per patient, encrypted. The original upload is deleted once the caregiver confirms the extracted plan | Patient and approved caregivers (`approved_caregivers` in `fixtures/p001.json`); sent to the model as prompt context without names | The 30-day recovery window plus 90 days `[design choice]`; deleted at once on request |
| Cabinet inventory (bottle photos + extracted JSON) | Caregiver photographs the bottles at home; Prompt A turns each label into cabinet JSON (`cab-1`, ...) | PHI\* (labels show the patient's name, drug, dose, prescriber, pharmacy, Rx number) | Photos: processed, then deleted once the caregiver confirms the JSON (never kept). JSON: app database, per patient, encrypted | Patient and approved caregivers; the model sees the JSON, not the photo | JSON as care plan; photos minutes, not days |
| Chat messages (session) | Caregiver types questions and symptoms | PHI\* (symptoms, medicines, sometimes names) | Session memory on the server while the chat is open | The caregiver in that session; sent to the model for the current reply | Cleared when the session ends; only facts the caregiver confirms move to long-term memory |
| Long-term memory (confirmed meds, schedule, preferences, resolved flags) | Written only after the caregiver confirms a fact ("yes, the old metoprolol is gone") | PHI\* | App database, per patient, encrypted | Patient and approved caregivers can view, edit, and delete every item | As care plan; a medicine change replaces the old entry; resolved flags kept for the 30 days |
| Patient + caregiver identity, contacts | Sign-up (caregiver name, relationship, email or phone); discharge papers (patient name, age, discharge date); clinic, pharmacy, and nurse-line numbers (`contact-1..3`) | PII; PHI\* once linked to the care plan. Clinic and pharmacy numbers are public business info | App database (account), encrypted; kept separate from the care plan, linked by an internal id | Patient and approved caregivers; names are removed before any model call | Life of the account; deleted with the account |
| Drug reference chunks (DailyMed, openFDA, MedlinePlus) | Public government sources (`spikes/labels/`, fetched 2026-11-01) | Public. The caregiver's *question* that retrieves them is not public | Search index on the server, with `set_id` and `effective_time` on every chunk | Anyone (public data) | Replaced when the source label's `effective_time` changes |
| App logs | The app itself: errors, latency, cost, flag ids, tier, model name | Pseudonymous (internal ids only); no message text, names, or photos | Log store, encrypted | Developers on call, least privilege | 30 days `[design choice]` |

\*PHI only when a HIPAA covered entity or its business associate holds it, for example if a hospital deploys
HomeStretch (see HIPAA below). In the consumer app the same data may not be legal PHI, but it is just as sensitive:
it is **consumer health data**, which state laws such as Washington's My Health My Data Act and the FTC Health Breach
Notification Rule cover (sources in their sections). HomeStretch treats it as PHI either way.

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

Decision rule (written before running, 2026-11-01):

- **Test set:** `spikes/retrieval_questions.json`, 12 caregiver-style questions about Rosa (`fixtures/p001.json`):
  10 answerable, each with a list of acceptable `(drug, section)` answers, and 2 with no answer in the labels
  (q11 "Zorvexa", a made-up drug; q12 gardening). Same questions, same 8 openFDA labels, same metadata filter
  for all six setups.
- **Metrics:** hit@1 and hit@3 on the 10 answerable questions only (a hit = any acceptable answer is the top
  result / in the top 3).
- **Pick the setup:** best hit@3 (a wrong or missing reference is the costly failure, and the model sees the
  top 3), then best hit@1. If still tied, the simpler setup wins (by-section over fixed size; BM25 over vector
  over hybrid).
- **Pick the threshold** (vector cosine score of the top chunk, best setup): the cutoff must reject **both**
  no-answer questions while rejecting **at most one** answerable question. Among cutoffs that pass, take the
  lowest (keeps the most answers). If no cutoff passes, we report that and the app does not rely on a score
  threshold alone (it falls back to "not in your plan; call the pharmacy [contact-2]" by intent and name match).

**Setup (run 2026-11-01):** 8 openFDA labels (`spikes/labels/`; set_id and effective_time in each file and below),
354 by-section chunks (mean 1,075 chars) and 548 fixed-size chunks (mean 794 chars). Metadata filter on every
search: Rosa's plan and cabinet drugs (furosemide, lisinopril, metoprolol succinate, metoprolol tartrate) plus any
drug the question names (Advil → ibuprofen, Aleve → naproxen, amlodipine). This is how the app avoids answering
about the wrong drug: a label outside that set is never searched (atorvastatin was never retrieved). Vector model
`BAAI/bge-small-en-v1.5` via `fastembed` 0.9.1, local and free. Script: `spikes/retrieval_check.py`; the run is
deterministic (two runs gave identical numbers).

Results on the 10 answerable questions, exactly as printed:

| Chunking | Search | hit@1 | hit@3 |
|---|---|---|---|
| By section | Keyword (BM25) | 1/10 | 4/10 |
| By section | Vector (bge-small) | 3/10 | 6/10 |
| By section | Hybrid (RRF) | 3/10 | 5/10 |
| Fixed 800/100 | Keyword (BM25) | 2/10 | 3/10 |
| Fixed 800/100 | Vector (bge-small) | 0/10 | 7/10 |
| Fixed 800/100 | Hybrid (RRF) | 4/10 | 6/10 |

Threshold chosen (best setup): top score on answerable vs no-answer questions:

| q | Answerable | Top vector cosine (fixed 800/100) | Top chunk |
|---|---|---|---|
| q01 Advil + water pill | yes | 0.6386 | ibuprofen / active_ingredient |
| q02 peeing so much | yes | 0.5862 | furosemide / general_precautions |
| q03 dizzy, metoprolol | yes | 0.7348 | metoprolol succinate / overdosage |
| q04 stop heart rate pill | yes | 0.7214 | metoprolol succinate / contraindications |
| q05 lisinopril cough | yes | 0.7135 | lisinopril / dosage_forms_and_strengths |
| q06 lips swollen | yes | 0.7276 | lisinopril / information_for_patients |
| q07 Aleve | yes | 0.7173 | naproxen / information_for_patients |
| q08 succinate vs tartrate | yes | 0.7908 | metoprolol tartrate / carcinogenesis_... |
| q09 amlodipine ankles | yes | 0.7834 | amlodipine / spl_patient_package_insert |
| q10 two water pills | yes | 0.6443 | furosemide / drug_interactions |
| q11 Zorvexa | **no** | **0.6861** | metoprolol succinate / adverse_reactions |
| q12 gardening | **no** | 0.5235 | metoprolol tartrate / how_supplied |

**No threshold passes the rule.** Rejecting both no-answer questions needs a cutoff of 0.687; that also rejects three
answerable questions (q01, q02, q10), and the rule allows one. Gardening (0.524) is easy to reject; Zorvexa (0.686) is
not: the filter searches only Rosa's drugs, and "side effects" matches metoprolol's adverse-reactions text well. The
similarity score never sees that the drug name is made up. **A score threshold cannot catch an unknown drug.**

Failed questions and why:

- **q02 ("why is she peeing so much") and q07 ("can she take Aleve") missed in all six setups**, partly because of
  answer-key gaps found after the run. The furosemide label puts the urination fact in `general_precautions`, not
  `adverse_reactions` (the vector setups ranked `general_precautions` first). The prescription naproxen label uses
  `warnings_and_cautions`, but the key listed `warnings` (it assumed an over-the-counter label). The key was
  committed before the run and is left unchanged; the table above is the official result.
- **Post-hoc check, not the decision** (`--lenient` accepts those two sections): By section + Vector rises to
  hit@1 5/10, hit@3 8/10; Fixed + Vector to 1/10, 9/10; the other four setups do not change. The best setup stays the
  same. Lesson: old-format and new-format FDA labels name sections differently, so a key must be written against
  the real labels.
- **Fixed + Vector has hit@1 0/10** because a fixed chunk is tagged with the section it *starts* in. A chunk starting
  at the end of `contraindications` that runs into the warnings counts as `contraindications`, so the right text is
  often there but labeled with the wrong section. Example: q04's top chunk is tagged `contraindications` but runs into
  section 5 (Warnings) and contains "abrupt cessation", the answer.
- **q05 (lisinopril cough):** Fixed + Vector's top 3 (dosage forms, how supplied, information for patients) do not
  contain the word "cough"; by-section Hybrid found the right section at rank 1.
- **BM25 is weakest (3–4/10 hit@3):** caregivers' words ("peeing", "heart rate pill", "swollen") do not appear in
  label language ("diuresis", "beta-blocker", "angioedema").

Decision and why:

- **Search: Fixed 800/100 + Vector (bge-small), top 3 to the model**, chosen by the rule (best hit@3, 7/10). It finds
  plain-language questions that keyword search misses. Because its hit@1 is low and by-section Vector ranks the right
  section first more often, the `{{references}}` slot should pass all three chunks with their drug, section, and
  date, never only the first.
- **"I don't know" cannot rest on a score threshold** (the rule fails). Before retrieval, the app checks every drug
  name: a name with no RxNorm match is a `pharmacist_check`, never searched (Sriya's experiment). After retrieval, a
  low top score (below about 0.6, which would reject gardening at 0.524 and only q02 at 0.586) is a secondary signal
  `[VERIFY: picked by eye from 12 questions; needs a larger test set]`. Either way the reply falls back to "not in
  your plan; call the pharmacy [contact-2]".
- **Labels used:** furosemide 01a5f094-b473-4e46-9e61-69d5ec6dd766 (2023-03-01); metoprolol succinate
  028049cd-d233-49f9-87fa-ec91e433a49f (2026-04-06); metoprolol tartrate 00de1f16-f979-4dbf-aa60-246ffac8d410
  (2025-06-10); lisinopril 021831ab-dfeb-40fc-aede-4aa1fbb8d918 (2023-08-18); ibuprofen (OTC)
  00653b7c-7099-487e-9a01-e89781c21323 (2026-04-29); naproxen 000155a8-709c-44e5-a75f-cd890f3a7caf (2026-01-29);
  amlodipine besylate 003dd1ec-16f8-4f96-b6a8-c4689d35892a (2026-04-20); atorvastatin calcium
  00afce9b-48c9-487a-a738-e359c005c707 (2025-08-28). Fetched from `https://api.fda.gov/drug/label.json` on 2026-11-01.

## References

[1]

## Condensed version (150 words or fewer)

The class build uses synthetic data only.

## Open questions


# Data, compliance, risks (Task D, Darshan)

Instructions: `docs/rag-memory/README.md`, Task D. Keep these headings.

## Data inventory

"PHI" below means *health information about an identifiable person*. Legally it is PHI only when a HIPAA covered
entity or business associate holds it; HomeStretch as a consumer app likely holds **consumer health data** instead
(see HIPAA below). That data is not legal PHI, but it is just as sensitive (a named parent's heart failure, medicines,
and symptoms), and the FTC and state laws below protect it [7][13]. We treat it like PHI.

| Data type | Source | Sensitivity (PHI / PII / public) | Where stored | Who can access | Retention (our design choice) |
|---|---|---|---|---|---|
| Discharge med list / care plan | Caregiver uploads or photographs the discharge papers → Prompt A → structured care plan (`med-1`, `warn-1`, ...) | PHI (consumer health data) | Per patient, encrypted, server side | Patient; approved caregivers; the model at reply time | Program length (30 days) + archive (below); the source photo is deleted once the caregiver confirms the extracted plan |
| Cabinet inventory (bottle photos + extracted JSON) | Caregiver photographs bottles → Prompt A → cabinet JSON → cabinet diff flags | PHI (photos can show the patient's name, pharmacy, prescriber) | Photos: temporary, until extraction is confirmed. JSON and flags: per patient, encrypted | Same as above | Photos deleted after confirmation (design.md B, "never stored"); JSON and flags as the care plan |
| Chat messages (session) | Caregiver's typed questions and the model's replies | PHI | Session record only (design.md B) | The signed-in caregiver; the model | Cleared at session end or after 30 minutes idle; only open red flags and pending questions carry over as dated items |
| Long-term memory (confirmed meds, schedule, preferences, resolved flags) | Caregiver confirmation, a new discharge document, or a confirmed cabinet check (confirmed-only writes) | PHI | Per patient, encrypted | Patient; approved caregivers ("What HomeStretch remembers" screen: view, edit, delete) | Archived at day 30; the caregiver chooses keep or delete; if no answer, deleted at day 60 |
| Patient + caregiver identity, contacts | Sign-up; `patient_profile` (name, age, `approved_caregivers`); care plan contacts (clinic, pharmacy) | PII (and PHI once linked to the care plan) | Account store, encrypted, separate from health records | The account holder; the patient | Until the account is deleted |
| Drug reference chunks (DailyMed, openFDA, MedlinePlus) | Public government APIs, queried by drug name only | Public | Retrieval index (no patient data in it) | Anyone | Refreshed when the label's `effective_time` changes; no patient retention issue |
| App logs | Server events | Should hold no PHI (see "Logging without PHI") | Log store | Developers on call | 30 days |

**Deletion:** a caregiver delete removes the entry from storage, not just from view (design.md B); a full account
deletion is done within 30 days, which fits inside Nevada's 30-day and Washington's 45-day deadlines [13][14]. Backups
roll over within 30 days. These periods are our design choices, not legal advice.

## HIPAA

- **Consumer app (caregiver downloads it): covered entity, business associate, or neither? Why?** Likely **neither**.
  HIPAA covers health plans, clearinghouses, and providers, plus their business associates. HHS's guidance for app
  developers says a developer becomes a business associate only when it creates, receives, maintains, or transmits PHI
  on behalf of a covered entity; an app the consumer chooses and uses for themselves, even one that pulls their records
  from a provider at their request, is generally not a business associate [1][2][3]. HomeStretch is chosen and paid for
  by the family, not by the hospital, so HIPAA likely does not apply. The FTC Act and the Health Breach Notification
  Rule apply instead [21].
- **Hospital deploys it: what changes?** If a hospital (a covered entity) offers HomeStretch to its patients or
  contracts us for patient monitoring or messaging, we become its **business associate**: we need a business associate
  agreement (BAA), the HIPAA Security Rule applies to us, and every vendor that handles that PHI for us (the LLM host,
  the cloud) needs its own BAA [2][3][19]. HHS's scenarios note a developer can run a hospital version under HIPAA and
  a separate consumer version outside it if the data is kept apart [2].
- **Caregiver access to the patient's information:** HIPAA's rule on family members (45 CFR 164.510(b)) lets a
  provider share information relevant to a family member's involvement in care if the patient agrees or does not
  object when given the chance, and, if the patient is absent or incapacitated, when the provider judges it is in the
  patient's best interest [4][5][6]. That rule binds the hospital, not us. **What HomeStretch does regardless:** the
  patient (or their legal representative) gives consent in the app, and only people on the patient's
  `approved_caregivers` list (in `fixtures/p001.json`: Maria, daughter) can see the record. Adding a caregiver needs
  the patient's consent; the patient can remove one at any time.
- **Sources (URL, checked date):** [1]–[6], [19], [21] in References, all checked 2026-11-01. HHS and eCFR blocked
  automated page fetches on that date, so the HHS content was confirmed from the official pages' search results, not
  a full read `[VERIFY: open [1]–[6] in a browser]`.

## FTC Health Breach Notification Rule

- **Does it cover us? Why?** Likely **yes**. The rule covers vendors of personal health records that are not covered
  by HIPAA; the FTC says makers of health apps and similar products must comply, and an app that draws health data from
  more than one source is probably a personal health record vendor [7][8]. HomeStretch draws from the discharge papers,
  bottle photos, the caregiver's entries, and drug APIs. `[VERIFY: whether drug-label APIs count as a "source" under
  the rule; our coverage conclusion does not depend on it]`
- **What counts as a breach; what we would have to do:** acquisition of unsecured identifiable health information
  without the person's authorization. It is not limited to hacking: **sharing data without authorization counts**
  (e.g., sending it to an ad or analytics partner) [7][8]. "Unsecured" means not encrypted or destroyed per HHS
  guidance [7]. On a breach: notify each affected person without unreasonable delay and within 60 calendar days of
  discovery; notify the FTC at the same time if 500 or more people are affected (otherwise within 60 days after the
  year ends); notify prominent media if 500 or more residents of one state are affected [7]. Penalty listed: up to
  $53,088 per violation [7].
- **2024 update (date):** announced April 26, 2024 [8]; published in the Federal Register May 30, 2024 (doc.
  2024-10855) [10]; **effective July 29, 2024** [9]. It made clear the rule covers health apps, added unauthorized
  disclosures to "breach of security", and allows electronic notice (email, text, in-app) [8]. On September 9, 2026 the
  FTC withdrew its 2021 health-app policy statement as obsolete because the amended rule now covers health apps [11].
- **Source:** [7]–[11], checked 2026-11-01.

## State consumer health privacy laws

| State / law | What it requires | Source | Checked |
|---|---|---|---|
| Washington, My Health My Data Act (RCW 19.373) | Consent before collecting consumer health data (use or purchase of prescribed medication is listed) and a **separate** consent before sharing, unless needed for the service the consumer asked for; a separate authorization to sell; right to delete, answered within 45 days; a published consumer health data privacy policy. HIPAA PHI is exempt; consumer-app data is not. AG and private lawsuits | [12][13] | 2026-11-01 |
| Nevada, SB 370 (2023), effective March 31, 2024 | Affirmative, voluntary consent before collecting or sharing consumer health data (separate for sharing); right to delete, done within 30 days of authenticating the request; AG enforcement only, no private right of action | [14] (enrolled bill; the codified NRS 603A sections not checked `[VERIFY]`) | 2026-11-01 |
| Connecticut, CT Data Privacy Act as amended by SB 3 / Public Act 23-56 | Consumer health data is "sensitive data": opt-in consent before processing it, and consent before selling it; no revenue or volume threshold for consumer health data controllers; general CTDPA right to delete `[VERIFY: whether the deletion right applies to us without meeting the CTDPA thresholds]` | [15][16] | 2026-11-01 |

## Access and security

- **Roles (patient, approved caregiver), consent, least privilege:** two roles. The **patient** owns the record and
  consents in the app; an **approved caregiver** (listed in `approved_caregivers`, added only with the patient's
  consent) can read and update the care plan, cabinet, and memory. Consent screens follow the state laws above:
  separate, explicit consent to collect, and a separate one for any sharing (we plan none); no sale. Least privilege:
  the model sees only the current patient's plan, diff, memory, and retrieved references for that turn; developers
  get no routine access to health records; drug APIs receive drug names only.
- **Encryption in transit / at rest:** TLS for all traffic; health records, memory, and photos encrypted at rest, with
  keys separate from the data. Encrypted data that leaks is not "unsecured" under the FTC rule [7], which is a second
  reason to encrypt. (Encryption alone does not meet HIPAA's Security Rule if a hospital deployment makes us a
  business associate [19].)

## LLM provider and logging

- **DeepSeek hosted API: where data is processed, training use (privacy policy URL, checked date):** DeepSeek's privacy
  policy (last updated Feb 10, 2026) says it collects, processes, and stores personal data **in the People's Republic
  of China**, may use data to train and improve its models, and lists a right to opt out of training by emailing
  privacy@deepseek.com [17]. The policy says it does not cover end users' data inside apps built on its API; there the
  developer is the controller [17]. The Open Platform Terms (effective April 29, 2026) make us responsible for telling
  end users how their data is processed and getting their consent, and do not say whether API inputs are used for
  training [18] (re-checked 2026-11-01: the Terms are silent on it; still `[VERIFY]` with DeepSeek, api-service@deepseek.com). Checked 2026-11-01. **Conclusion:** fine for
  synthetic data; not acceptable for a real patient's data.
- **Options for real data (self-hosted open-weight model; HIPAA-eligible host with BAA; remove names before the call):**
  1. **Self-hosted open-weight model** (e.g. a Qwen or DeepSeek open-weight model on our own servers; Assignment 2
     already tested local Ollama models): no health data leaves our infrastructure.
  2. **HIPAA-eligible cloud host that signs a BAA:** required anyway in a hospital deployment; HHS says using a cloud
     provider for ePHI without a BAA violates HIPAA, even if the data is encrypted [19].
  3. **Remove names before any API call:** send "the patient", not "Rosa Delgado"; strip the caregiver's name, phone
     numbers, pharmacy, and clinic details. This lowers risk but is **not** HIPAA de-identification, which requires
     removing 18 kinds of identifiers (including dates such as the discharge date) or an expert determination [20].
     Use it on top of option 1 or 2, not instead of them.
- **Logging without PHI:** log event types, plan ids (`med-1`, `flag-2`), flag labels, `red_flag_tier`, retrieval
  scores, latency, token counts, and a random session id. Never log message text, model replies, photos, drug names
  tied to a person, or names; no third-party analytics SDK receives health events (that would be an unauthorized
  disclosure under the FTC rule [8]). Debug logs that need text use synthetic data only. Logs kept 30 days.

## Risks and mitigations

| Risk | Likelihood | Impact | Mitigation (name our real guardrails) |
|---|---|---|---|
| Hallucinated drug facts | Medium (v4 added safety advice not in the plan) | High | Clinical facts only from the care plan or a retrieved reference, with inline citation of plan ids (`[med-1]`) or `ref-n`; output guardrail check rejects uncited clinical claims; RxNav name check before retrieval (unknown drug → `pharmacist_check`) and a retrieval threshold (top cosine 0.582, a weak second line): below it the reply says "I don't know; call the pharmacy [contact-2]" |
| Outdated labels | Medium | Medium | Every chunk carries `set_id` and `effective_time`; references show their date; re-fetch when DailyMed/openFDA updates the label; the care plan outranks a label for this patient |
| Wrong drug retrieved (look-alike / sound-alike names) | Medium (metoprolol succinate vs tartrate; "Zorvexa" matched to a real drug in A2) | High | RxNorm name matching with a cutoff; no match means `pharmacist_check`, never a guess; metadata filter limits search to the active plan medicines plus drugs the question names, and stopped drugs only when named (retrieval experiment: wrong-drug answers went from 5 questions to 0); unknown names stored verbatim (design.md B, guard 4) |
| Prompt injection through uploaded documents or labels | Low–Medium | High | Uploaded documents, labels, and memory enter the prompt as data, never instructions; text like "ignore the plan" is not followed (design.md B, guard 5); the plan wins over any other source |
| Memory poisoning or stale memory | Medium (seen in our memory test) | High | Confirmed-only memory writes; source and date on every entry; flags close only on a caregiver report or a new cabinet check; caregiver-reported changes stay pending; caps (10 reports); new plan supersedes old entries; archive at day 30 (design.md B guards) |
| Privacy breach | Low–Medium | High | Encryption at rest and in transit; `approved_caregivers` access only; no PHI in logs; no ad/analytics sharing; synthetic data only with DeepSeek; FTC breach-notice plan (60 days) [7] |
| Over-reliance in place of clinicians | Medium | High | Tier-3 "Call 911 now" rule always fires first on `warn-6`-type signs; no diagnosis, no dose advice; replies point to the clinic or pharmacy contact ids; `pharmacist_check` for anything uncertain; in-app notice that the app is not medical advice (DeepSeek's terms also require disclosing AI output may be wrong [18]) |

## Retrieval experiment (Task D-tech)

Anmol ran this part (Darshan unwell). Setup, test set, and decision rules were written before each run in
`design.md`, Section A ("Retrieval experiment: setup" and "round 2"). Script: `spikes/retrieval_check.py`; questions:
`spikes/retrieval_questions.json`; labels: `spikes/labels/` (8 openFDA labels, fetched 2026-11-01, `manifest.json`);
full output: `spikes/retrieval_results.txt`. No LLM calls.

**Scoring correction (2026-11-01):** the first write-up counted a hit when the right label *section* came back. Long
sections are split into several chunks, so a returned chunk could be from the right section but not contain the answer
(found when the Section C scenario got rat-overdose text for "ears ringing"). A hit now requires the returned chunk
to contain the evidence. All numbers below are re-scored; the earlier, higher numbers were wrong.

Decision rule (written before running): best dev hit@3, then hit@1; the threshold (top vector cosine) must reject all
dev no-answer questions while rejecting at most 1 dev answerable question; then held-out, unchanged.

**Round 1, pre-registered pipeline** (dev 15 answerable; q14 re-scored after a disclosed answer-key fix):

| Chunking | Search | hit@1 | hit@3 |
|---|---|---|---|
| By section | Keyword (BM25) | 5/15 | 7/15 |
| By section | Vector (bge-small) | 7/15 | 8/15 |
| By section | Hybrid (RRF) | 6/15 | 9/15 |
| Fixed 800/100 | Keyword (BM25) | 4/15 | 6/15 |
| Fixed 800/100 | Vector (bge-small) | 5/15 | 8/15 |
| Fixed 800/100 | Hybrid (RRF) | **7/15** | **9/15** |

Round 1 **failed**: the threshold could not work. "Side effects of Zorvexa?" (made up) scored 0.701 and "How much
Kelvanide?" 0.714, above most real questions; the words "side effects" and "how much" match label text whatever the
drug. A cutoff above them rejected 12 of 15 real questions. Also, 5 misses returned **metoprolol tartrate** (stopped
at discharge, still in the cabinet) instead of succinate: the look-alike-drug risk, caused by our own filter.

**Round 2, two post-hoc fixes**, judged on 8 new questions (`heldout2`) frozen before running: (1) RxNav name check
before retrieval: a drug-like word with no RxNorm match means no retrieval and `pharmacist_check`; (2) stopped drugs
searched only when the question names them. The first round-2 run had a bug (sentence-initial words such as "Could"
were looked up as drug names); it was fixed, a self-check added, and everything rerun. Numbers below are from the rerun.

| Chunking | Search | Dev hit@1 | Dev hit@3 | heldout2 hit@3 |
|---|---|---|---|---|
| By section | Keyword (BM25) | 6/15 | 8/15 | 1/6 |
| By section | Vector (bge-small) | 7/15 | 9/15 | **3/6** |
| By section | Hybrid (RRF) | 7/15 | **11/15** | 1/6 |
| Fixed 800/100 | Keyword (BM25) | 5/15 | 6/15 | 0/6 |
| Fixed 800/100 | Vector (bge-small) | 5/15 | 9/15 | 2/6 |
| Fixed 800/100 | Hybrid (RRF) | 7/15 | 10/15 | 2/6 |

| Safety check (round 2) | Result |
|---|---|
| Made-up drugs caught by the name check | 3 of 3 (Zorvexa, Kelvanide, Bravacil; round 3 adds Trivolam, q46: 4 of 4 in the draft); no real question wrongly flagged; "Sunday" not treated as a drug |
| Stopped drug (tartrate) returned when not named | 0 (round 1: on 5 questions) |
| Off-topic questions rejected by the threshold (0.582, set on dev) | heldout2: 1 of 1 ("church on Sunday", 0.458); seen held-out: 0 of 1 ("hot bath", 0.594) |
| Real questions wrongly rejected | dev 2 of 15 (rule allows 1: **fails narrowly**); heldout2 1 of 6 (the Lopressor question, 0.548) |

Threshold chosen (best setup): 0.582 top vector cosine, set just above the highest dev no-answer question that
reaches retrieval ("gardening", 0.581). Answerable dev questions scored 0.558–0.783, so off-topic and real questions
overlap: the threshold is a weak signal, not a reliable gate.

Failed questions and why:
- **Two metoprolols:** "She still has some Lopressor left. What is that one for?" returned succinate chunks, not the
  tartrate indications; with near-identical label text, ranking cannot tell the two salts apart.
- **Vocabulary gap:** "hands and feet cold" (label: "cold extremities"), "so thirsty" (label: "thirst" in a long
  precautions block), "salt substitute" (found in lisinopril, but under clinical pharmacology, not the patient section).
- **Split sections:** the right section, but the wrong part of it (furosemide "precautions" is several chunks; the
  ringing-ears text is in one, indomethacin and cancer studies in another).
- **Small set:** 6 answerable heldout2 questions; one question moves hit@3 by 17 points.

Decision and why:
- **Search: hybrid (BM25 + vector, RRF), by-section chunks**, per the rule (best dev hit@3, 11/15). Held-out did not
  confirm it: on the 6 new questions it found the right passage for **1**, vector alone for 3. We report the rule's
  choice rather than switch after the fact, and state the main finding plainly: **on unseen questions, retrieval found
  the answer for 1 to 3 of 6.** Retrieval quality is the weakest part of the design. Before building: a larger test set,
  smaller chunks within long sections, and a reranker or query rewriting for plain-word questions ("cold hands" vs
  "cold extremities").
- **Name check before retrieval: adopted.** It is the only thing that stopped made-up drugs (3 of 3); similarity cannot.
- **Stopped drugs only when named: adopted.** It removed every wrong-drug answer.
- **Threshold: kept as a second line, not trusted alone.** It failed its rule by one question. The first line is the
  grounding rule in Prompt B v6 (clinical facts only from the plan or a cited reference, else "not in your plan; call
  the pharmacy [contact-2]"), so a weak retrieval still cannot become an unsupported claim.

**Round 3: smaller chunks and a reranker** (setup frozen in `design.md` before running; `spikes/retrieval_round3.py`,
output `spikes/retrieval_round3_results.txt`; selection on the 29 seen answerable questions, confirmation on 8 new
answerable + 3 no-answer, `heldout3`). The first run had one more name-detector bug (the pronoun "I" was looked up as a
drug); fixed, self-check added, rerun; numbers below are from the rerun.

| Setup | Seen hit@1 | Seen hit@3 | Gate: seen answerable wrongly rejected | heldout3 hit@3 |
|---|---|---|---|---|
| R2: sections, hybrid (round-2 choice) | 12/29 | **18/29** | 7 (cosine 0.595) | 5/8 |
| R3a: 500-char chunks, hybrid | 9/29 | 15/29 | 5 (cosine 0.605) | 4/8 |
| R3b: 500-char chunks, hybrid + reranker | 7/29 | 13/29 | **1** (reranker score) | 6/8 |
| R3c: sections, hybrid + reranker | 14/29 | 16/29 | 3 (reranker score) | 6/8 |

- **Ranking:** the rule keeps R2 (best on the seen set). The reranked setups did one question better on the new set
  (6/8 vs 5/8), which is within noise. Smaller chunks alone did not help.
- **Gate: the reranker's score is the first "I don't know" signal that meets its rule** (R3b: 1 of 29 real questions
  wrongly rejected, against 7 for the cosine; all off-topic questions rejected). Design: hybrid ranking for the passages,
  the reranker score as the gate (a post-hoc combination; confirm on more questions).
- **New gap:** "Can she take Tylenol?" passed every gate: Tylenol is real, so the name check passes it, but there is no
  Tylenol label, so plan-drug passages came back. Post-hoc rule: a real drug with no label in the index means no
  retrieval and "ask the pharmacist".
- Across both fresh sets, the round-2 setup found the answer for 6 of 14 new questions (1/6, then 5/8): small sets vary
  a lot, so 100+ questions remain the first step before building.

**Round 4: plain-word query expansion** (map `spikes/query_expansion.py` frozen before the new questions; setup in
`design.md`; output `spikes/retrieval_round4_results.txt`). Selection on the 37 answerable questions already used;
confirmation on 8 new ones (`heldout4`).

| Setup | Selection hit@3 | heldout4 hit@3 |
|---|---|---|
| R2: sections, hybrid | 23/37 | 2/8 |
| **R2 + expansion** | **30/37** | **5/8** |
| R3c: + reranker | 22/37 | 3/8 |
| R3c + expansion | 26/37 | 4/8 |

- **Adopted: hybrid search with query expansion** (best on selection; on new questions 5 of 8 vs 2 of 8 without).
  **Superseded by round 5 (`design.md` §E):** reranked by the expanded question, top 5, bge-base, no gate; 9 of 12 on
  a new frozen set (old pipeline 2 of 12).
  Wins came from vocabulary: "tastes" → dysgeusia, "itchy" → pruritus, "feel down" → depression.
- Caveat: the same person wrote the map and the new questions; a set written by someone else is the stronger test.
- Still missed: "Can Advil push her blood pressure up?" and "Could the water pill cause a skin rash?" (the right section,
  but another chunk of it).
- Pipeline now: name check → filter → **hybrid search on the expanded question** → reranker-score gate.

## Added from Darshan's version (`compliance.md`, branch `darshan`)

Darshan's version arrived after ours. It is the base for nothing below being replaced; these sourced points are added,
credited to him (his reference ids kept, full entries in References as [22]–[25]):
- **FTC Rule vs HIPAA boundary:** the Rule "does not apply to HIPAA-covered entities, or to any other entity to the
  extent that it engages in activities as a business associate" (16 CFR 318.1) [25]. A hospital deployment falls under
  HIPAA; the direct-to-consumer app stays under the FTC Rule.
- **The app counts as a personal health record:** the FTC's own example is "a diet app that allows users to enter daily
  weights and an API for pulling calorie counts from restaurant menus" [24]. HomeStretch has the same shape (caregiver
  enters the plan; the app pulls openFDA and RxNorm data). This settles our open question on whether label APIs count
  as a "source".
- **CFR text read directly** (GovInfo, not search snippets): 45 CFR 164.502(e)(1)(ii) on subcontractors and
  164.502(g)(2) on personal representatives [22][23].
- **Washington:** no size threshold; small businesses had until June 30, 2024. Deletion reaches backups within 6 months
  `[VERIFY in RCW 19.373]`.
- **Connecticut, narrower and safer than our row above:** no one may give employees or contractors access without a
  duty of confidentiality, give processors access without a data-processing contract, sell consumer health data
  without consent, or geofence health facilities; these apply regardless of the CTDPA's size thresholds. Our row's
  "opt-in consent before processing" may depend on those thresholds `[VERIFY]`; the draft now uses his wording.
- **DeepSeek offers no BAA that he could find.** Consistent with ours: the hosted API never receives real data.

Conflicts, ours kept: civil penalty $53,088 (January 2025 adjustment; his $51,744 is the 2024 figure); DeepSeek's
privacy policy excludes API end-user data and the Open Platform Terms apply [18] (he says the policy covers paid API use,
tagged `[VERIFY]`).

**His retrieval experiment** (2 chunkings x BM25/vector/hybrid, 8 labels, 10 answerable + 2 no-answer questions), rerun
by an independent check: it reproduces except one cell (fixed + vector hit@1 1/10, not 0/10). It scores a hit at
section level; scored at chunk level (section and evidence) his best setup falls from 7/10 to **4/10** hit@3. Answer-key
issues: sections that do not exist in his labels (q01, q04, q07) and accepted sections without the fact (q05, q06, q09,
q10). His naproxen label is prescription naproxen, not OTC Aleve (naproxen sodium), and two labels are older versions,
so we keep our labels. **Useful as an outside test:** his 10 questions were written by someone who never saw our
expansion map; our hybrid + expansion gets **5 of 10** at hit@3 (3 at hit@1) on them, chunk level, in line with 5 of 8
on our own new questions. His findings agree with ours: retrieval is weak, a score threshold cannot stop a made-up drug
(Zorvexa scored 0.686), and the name check is the guard. Cross-check files: `spikes/darshan_crosscheck/`.

## References

[1] U.S. HHS, Resources for Mobile Health Apps Developers, https://www.hhs.gov/hipaa/for-professionals/special-topics/health-apps/index.html (checked 2026-11-01)
[2] U.S. HHS OCR, Health App Use Scenarios & HIPAA (February 2016), https://www.hhs.gov/sites/default/files/ocr-health-app-developer-scenarios-2-2016.pdf (checked 2026-11-01)
[3] U.S. HHS, Business Associates, https://www.hhs.gov/hipaa/for-professionals/privacy/guidance/business-associates/index.html (checked 2026-11-01)
[4] U.S. HHS, FAQ: Does HIPAA allow a health care provider to communicate with a patient's family, friends, or other persons who are involved in the patient's care?, https://www.hhs.gov/hipaa/for-professionals/faq/2087/does-hipaa-allow-a-health-care-provider-to-communicate-with-a-patients-family-friends-or-other-persons-who-are-involved-in-the-patient-care.html (checked 2026-11-01)
[5] U.S. HHS, FAQs: Disclosures to Family and Friends, https://www.hhs.gov/hipaa/for-professionals/faq/disclosures-to-family-and-friends/index.html (checked 2026-11-01)
[6] eCFR, 45 CFR 164.510, https://www.ecfr.gov/current/title-45/subtitle-A/subchapter-C/part-164/subpart-E/section-164.510 (checked 2026-11-01: text of (b)(1)(i) read through the eCFR API, "may ... disclose to a family member ... the protected health information directly relevant to such person's involvement with the individual's health care")
[7] U.S. FTC, Complying with FTC's Health Breach Notification Rule, https://www.ftc.gov/business-guidance/resources/complying-ftcs-health-breach-notification-rule-0 (checked 2026-11-01)
[8] U.S. FTC, FTC Finalizes Changes to the Health Breach Notification Rule (April 26, 2024), https://www.ftc.gov/news-events/news/press-releases/2024/04/ftc-finalizes-changes-health-breach-notification-rule (checked 2026-11-01)
[9] U.S. FTC, Health Breach Notification Rule: The Basics for Business, https://www.ftc.gov/business-guidance/resources/health-breach-notification-rule-basics-business (checked 2026-11-01)
[10] U.S. FTC, 16 CFR Part 318 Health Breach Notification Rule (Federal Register notice, May 30, 2024), https://www.ftc.gov/legal-library/browse/federal-register-notices/16-cfr-part-318-health-breach-notification-rule (checked 2026-11-01)
[11] U.S. FTC, FTC Withdraws Obsolete Policy Statement (September 9, 2026), https://www.ftc.gov/news-events/news/press-releases/2026/09/ftc-withdraws-obsolete-policy-statement (checked 2026-11-01)
[12] Washington State Office of the Attorney General, Protecting Washingtonians' Personal Health Data and Privacy, https://www.atg.wa.gov/protecting-washingtonians-personal-health-data-and-privacy (checked 2026-11-01)
[13] Washington State Legislature, Chapter 19.373 RCW (Washington My Health My Data Act), https://app.leg.wa.gov/RCW/default.aspx?cite=19.373&full=true (checked 2026-11-01)
[14] Nevada Legislature, Senate Bill No. 370 (2023), enrolled, https://archive.leg.state.nv.us/Session/82nd2023/Bills/SB/SB370_EN.pdf (checked 2026-11-01)
[15] Connecticut Office of the Attorney General, The Connecticut Data Privacy Act, https://portal.ct.gov/ag/sections/privacy/the-connecticut-data-privacy-act (checked 2026-11-01)
[16] Connecticut General Assembly, Substitute Senate Bill No. 3, Public Act No. 23-56, https://www.cga.ct.gov/2023/act/Pa/pdf/2023PA-00056-R00SB-00003-PA.PDF (opened 2026-11-01; confirms consumer health data controllers may not "sell, or offer to sell, consumer health data without first obtaining the consumer's consent")
[17] DeepSeek, DeepSeek Privacy Policy (last updated Feb 10, 2026), https://cdn.deepseek.com/policies/en-US/deepseek-privacy-policy.html (checked 2026-11-01)
[18] DeepSeek, DeepSeek Open Platform Terms of Service (effective April 29, 2026), https://cdn.deepseek.com/policies/en-US/deepseek-open-platform-terms-of-service.html (checked 2026-11-01)
[19] U.S. HHS, Guidance on HIPAA & Cloud Computing, https://www.hhs.gov/hipaa/for-professionals/special-topics/health-information-technology/cloud-computing/index.html (checked 2026-11-01)
[20] U.S. HHS, Guidance Regarding Methods for De-identification of Protected Health Information, https://www.hhs.gov/hipaa/for-professionals/special-topics/de-identification/index.html (checked 2026-11-01)
[21] U.S. HHS, Collecting, Using, or Sharing Consumer Health Information? Look to HIPAA, the FTC Act, and the Health Breach Notification Rule, https://www.hhs.gov/hipaa/for-professionals/special-topics/hipaa-ftc-act/index.html (checked 2026-11-01)
[22] 45 CFR 164.502(e)(1)(ii), Disclosures to subcontractors, GovInfo, https://www.govinfo.gov/content/pkg/CFR-2025-title45-vol2/pdf/CFR-2025-title45-vol2-sec164-502.pdf (Darshan, checked 2026-11-01)
[23] 45 CFR 164.502(g)(2), Personal representatives, same GovInfo document as [22] (Darshan, checked 2026-11-01)
[24] FTC, Complying with FTC's Health Breach Notification Rule (July 2024, edited January 2025), https://www.ftc.gov/business-guidance/resources/complying-ftcs-health-breach-notification-rule-0 (Darshan, checked 2026-11-01)
[25] FTC, Health Breach Notification Rule, final rule, 89 Fed. Reg. 47028 (May 30, 2024), 16 CFR Part 318, https://www.govinfo.gov/content/pkg/FR-2024-05-30/pdf/2024-10855.pdf (Darshan, checked 2026-11-01)

## Condensed version (150 words or fewer)

The class build uses synthetic data only. HomeStretch handles consumer health data: a named parent's medicines,
symptoms, and discharge plan. It may not be legal PHI, but it is just as sensitive. Chosen and paid for by the family,
the app is likely neither a HIPAA covered entity nor a business associate [1][2]; a hospital deployment would make us a
business associate needing a BAA [3]. The FTC Health Breach Notification Rule likely applies; since July 29, 2024,
unauthorized disclosure counts as a breach [8][9]. Washington, Nevada, and Connecticut require opt-in consent for
consumer health data [13][14][15]. DeepSeek stores data in China [17], so real data needs a self-hosted model or a
BAA-covered host. Only `approved_caregivers` see the record; memory is archived at day 30.

| Risk | Main guardrail |
|---|---|
| Hallucinated facts | Cited plan ids; name check before retrieval; references used only when they answer (the threshold and the reranker gate were removed in round 5, `design.md` §E) |
| Wrong or unknown drug | `pharmacist_check` |
| Emergency | Tier-3 "Call 911 now" |
| Memory poisoning | Confirmed-only writes |

## Open questions

- HHS and eCFR pages returned 403 / a bot check to automated fetches on 2026-11-01; their content above comes from the
  official pages' search results. Someone should open [1]–[6] in a browser and confirm the wording.
- Nevada: the codified NRS 603A section numbers were not checked; the enrolled SB 370 text was.
- Connecticut: does the CTDPA deletion right reach a small app that meets no threshold (the consumer health data
  provisions have no threshold, the general rights may)?
- Does the FTC rule's "multiple sources" test count public drug-label APIs? Our coverage conclusion holds either way.
- Retention periods (day 60 delete, 30-day logs and backups) are our design choices; Anmol to confirm they match
  design.md section B.


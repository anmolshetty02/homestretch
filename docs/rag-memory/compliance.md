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

- **Consumer app (caregiver downloads it): HIPAA likely does not apply; neither a covered entity nor a business
  associate.** A covered entity is a health plan, a health care clearinghouse, or a health care provider that sends
  health information electronically in a standard transaction [H4]. HomeStretch is none of these. A business
  associate creates, receives, maintains, or transmits PHI *on behalf of* a covered entity [H4]. When the caregiver
  downloads the app and types or photographs the information themselves, HomeStretch acts for the family, not for a
  hospital. HHS's guidance for app developers says that a developer offering services directly to consumers, and not
  on behalf of a provider or health plan, is not likely to be subject to HIPAA [H1][H2]. Not being under HIPAA does
  not make the data less sensitive: the FTC Act, the FTC Health Breach Notification Rule, and state consumer health
  laws still apply [H7] (next sections). We must not claim "HIPAA compliant" in marketing [H7].
- **Hospital deploys it: HomeStretch becomes a business associate.** If a hospital (a covered entity) contracts with
  us to give the app to its discharged patients, we would create, receive, and maintain PHI on the hospital's behalf,
  which is the business associate definition [H4]. HHS lists exactly this case, an app developer contracting with a
  covered entity to provide the app to its patients, as a business associate [H3]. Then we need a **business
  associate agreement (BAA)** with the hospital, and we may use or disclose PHI only as the BAA permits [H7]. The
  vendors we use that handle the PHI (cloud host, LLM provider) become our subcontractors, which HIPAA also counts as
  business associates; we may share PHI with them only after getting written assurances that they will protect it,
  in practice a BAA with each one [H4][H6] (see "LLM provider" below). HHS's guidance allows a developer to run a hospital version and a
  direct-to-consumer version side by side, with HIPAA protections on the hospital version's data, as long as the data
  is kept separate [H2] `[VERIFY: open the HHS scenarios PDF; hhs.gov blocked automated reading]`.
- **Caregiver access to the patient's information.** HIPAA lets a hospital or clinic share with a family member or
  close friend "the protected health information directly relevant to such person's involvement" in the patient's
  care [H5]. If the patient is present and able to decide, the provider may share when the patient agrees, does not
  object, or the provider reasonably infers no objection; if the patient is absent or incapacitated, the provider may
  share what is directly relevant if, in their professional judgment, it is in the patient's best interest [H5][H8].
  A person with legal authority to make health decisions for an adult (for example, a health care power of attorney)
  is treated as the patient's **personal representative** [H6]. These rules govern what the *hospital* may tell
  Maria; they do not govern our app. **What HomeStretch does regardless:** the patient consents in the app to each
  caregiver; only people on the patient's `approved_caregivers` list (in `fixtures/p001.json`: Maria, daughter) can
  see the care plan, cabinet, chat, and memory; the patient can remove a caregiver at any time; and the app shares
  only what the caregiver needs for the medicines and the warning signs in the plan.
- **Sources (checked 2026-11-01):** [H1]–[H8] in References. The CFR text [H4]–[H6] and the FTC page [H7] were read
  directly. The hhs.gov pages [H1]–[H3], [H8] block automated reading; their content was confirmed from search
  results of those exact pages `[VERIFY: open each hhs.gov link once by hand]`.

## FTC Health Breach Notification Rule

- **Does it cover us? Likely yes, for the consumer app.** The Rule applies to vendors of personal health records
  that HIPAA does not cover [F1][F3]. A personal health record is an electronic record of identifiable health
  information that "has the technical capacity to draw information from multiple sources" and is managed by or for
  the individual [F2]. The FTC's own example is "a diet app that allows users to enter daily weights and an API for
  pulling calorie counts from restaurant menus" [F2]. HomeStretch is built the same way: the caregiver enters the
  care plan and bottle photos for the patient, and the app pulls drug information from openFDA and RxNorm. The
  2024 update states the Rule applies to "health apps and similar technologies not covered by HIPAA" [F1]. The Rule
  "does not apply to HIPAA-covered entities, or to any other entity to the extent that it engages in activities as a
  business associate" (16 CFR 318.1) [F4]. So in a hospital deployment, that data falls under HIPAA instead, while a
  direct-to-consumer version stays under the FTC Rule.
- **What counts as a breach; what we would have to do.** A breach is the acquisition of unsecured identifiable
  health information without the person's authorization, and "is not limited to cybersecurity intrusions" [F2]:
  the 2024 update says it includes "an unauthorized disclosure" [F1], such as sharing health data with an
  advertiser or analytics company without consent. After a breach we must notify: (1) each affected person, without
  unreasonable delay and within 60 calendar days of discovery; (2) the FTC, at the same time as the people if 500 or
  more are affected, or within 60 days after the end of the year if fewer; (3) prominent local media if at least
  500 residents of one state are affected [F2]. Notice may go by email [F1]. Penalties: up to $51,744 per violation
  per the FTC's July 2024 page [F3] `[VERIFY: amount is adjusted for inflation each year]`. **What HomeStretch does:**
  no advertising or analytics SDKs that receive health data; no sharing without the patient's opt-in; a written
  breach-response plan with the 60-day clock.
- **2024 update (date):** announced April 26, 2024 [F1]; published in the Federal Register May 30, 2024
  (89 FR 47028); effective **July 29, 2024** [F4]. Main changes: clearer coverage of health apps, "breach" includes
  unauthorized disclosure, a clearer "multiple sources" test, more required content in the notice, email notice, and
  FTC notice at the same time as consumers for 500+ people [F1].
- **Source:** [F1]–[F4] in References (all read directly, checked 2026-11-01).

## State consumer health privacy laws

| State / law | What it requires | Source | Checked |
|---|---|---|---|
| Washington, My Health My Data Act (RCW 19.373) | Covers HomeStretch's data: "consumer health data" lists "individual health conditions, treatment, diseases, or diagnosis" and "use or purchase of prescribed medication". **Opt-in consent** before collecting, for a specified purpose; **separate** consent before sharing; a general terms-of-use click does not count. Right to **delete** (including backups, within 6 months) and to a response within 45 days. Selling needs a signed authorization. No size threshold; small businesses had until June 30, 2024 (others March 31, 2024). Enforced through the Consumer Protection Act, by the Attorney General **and by private lawsuits** | [S1] [S2] | 2026-11-01 |
| Nevada (SB 370, 2023; NRS 603A.400–.550) | Similar to Washington: consumer health data may be collected only with "affirmative, voluntary consent" (or to provide the requested service); sharing needs separate consent. Consumers can confirm, get the list of third parties, stop, and **delete** (deletion within 30 days; responses within 45). Selling needs written, signed authorization that expires after 1 year. A violation is a deceptive trade practice; **no private right of action**. Effective March 31, 2024 `[VERIFY: effective date not found on the NRS page]` | [S3] | 2026-11-01 |
| Connecticut (Public Act 23-56, 2023, amending the Connecticut Data Privacy Act) | Consumer health data = data used to identify a physical or mental health condition or diagnosis. No person may give employees or contractors access without a duty of confidentiality, give processors access without a data-processing contract, **sell it without consent**, or geofence health facilities. These rules apply to anyone doing business in or targeting Connecticut, regardless of the Act's usual size thresholds. Effective July 1, 2023. Enforced by the Attorney General `[VERIFY: AG enforcement and the Act's 2025 amendments not read in full]` | [S4] | 2026-11-01 |

**What HomeStretch does to meet all three:** a separate, plain-language consent screen before any health data is
collected (not buried in the terms of use); a second, separate consent before anything is shared (we share nothing
by default); in-app view and delete for every item, with deletion reaching backups; staff and vendor access only
under confidentiality and processing contracts; we never sell health data and use no location tracking.

## Access and security

- **Roles (patient, approved caregiver), consent, least privilege:**
  - *Patient:* owns the record; gives consent at sign-up (separate consent screens, see state laws); adds or
    removes caregivers; can view, export, and delete everything.
  - *Approved caregiver* (`approved_caregivers` in `fixtures/p001.json`, e.g. Maria, daughter): added only by the
    patient (or by a legal personal representative [H6]); can see and use the care plan, cabinet diff, chat, and
    memory for this one patient. Every request is checked against that patient's list; the assistant itself answers
    about "only this patient" (`<rules>` in `prompts/agent_v4.md`).
  - *Staff and vendors:* no routine access to health data. Support access only with the patient's permission,
    time-limited and logged; vendors only under a processing contract (and a BAA in a hospital deployment).
  - *Model:* receives only what one reply needs: the care plan and cabinet diff for that patient, the retrieved
    label chunks, and the current session, with names removed (below).
- **Encryption in transit / at rest:** TLS on every connection (app, server, model API, drug APIs); databases,
  backups, and logs encrypted at rest, with keys in a managed key service. This matters legally too: the FTC Rule
  only requires breach notice for "unsecured" data, meaning data not protected by a technology HHS specifies, such
  as encryption (16 CFR 318.2) [F4]. Photos are deleted after extraction (Data inventory), so they cannot leak later.

## LLM provider and logging

- **DeepSeek hosted API: where data is processed, training use.** Assignment 2 called DeepSeek's hosted API with
  synthetic data only. DeepSeek's privacy policy (last updated February 10, 2026) says: "we directly collect, process
  and store your Personal Data in People's Republic of China"; inputs may be used to "train and improve our
  technology, such as our machine learning models"; users have "the right to opt-out of using your Personal Data for
  training our models" (by emailing privacy@deepseek.com); inputs are kept "for as long as you have an account" [P1].
  The policy covers paid open-platform use [P1] `[VERIFY: DeepSeek's separate Open Platform privacy policy blocked
  automated reading]`. DeepSeek offers no BAA that we could find. **Conclusion: the hosted DeepSeek API must never
  receive real patient data.** It stays a development tool for synthetic data.
- **Options for real data** (any of these, plus removing names in every case):
  1. *Self-hosted open-weight model.* Run the model on our own servers so no data leaves our control. Assignment 2
     already ran local Ollama models (`evals/models.yaml`). Cost: our own hardware and slower answers.
  2. *HIPAA-eligible host with a BAA.* For example, Amazon Bedrock is on AWS's HIPAA Eligible Services list, and AWS
     requires a signed BAA before any PHI goes to those services [P2]. Required for a hospital deployment, where the
     model host is our subcontractor [H4][H6].
  3. *Remove names before every call.* The prompt gets "the patient" and "the caregiver" instead of "Rosa Delgado"
     and "Maria"; ids (`med-1`, `flag-1`) are kept; the app puts names back into the reply locally. This lowers
     the risk but does not make the data anonymous: medicines plus a discharge date can still identify someone, so
     it is used *with* option 1 or 2, never instead of them.
- **Logging without PHI:** logs keep an internal account id, the case or session id, timestamps, model, latency,
  cost, `red_flag_tier`, flag ids and labels, and error codes. Never logged: message text, names, the care plan,
  photos, or model replies. Debugging with real text needs the patient's permission and is deleted afterwards.
  Assignment 2's `results/*/records.jsonl` hold each test input and the full model reply; that is fine only because
  the data is synthetic. Logs are encrypted and kept 30 days (Data inventory).

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

[H1] U.S. Department of Health and Human Services (HHS), Office for Civil Rights, Resources for Mobile Health Apps
Developers, https://www.hhs.gov/hipaa/for-professionals/special-topics/health-apps/index.html (checked 2026-11-01)

[H2] HHS Office for Civil Rights, Health App Use Scenarios & HIPAA (February 2016),
https://www.hhs.gov/sites/default/files/ocr-health-app-developer-scenarios-2-2016.pdf (checked 2026-11-01)

[H3] HHS, Business Associates Frequently Asked Questions,
https://www.hhs.gov/hipaa/for-professionals/privacy/guidance/business-associates/index.html (checked 2026-11-01)

[H4] 45 CFR § 160.103, Definitions ("Business associate", "Covered entity"), Code of Federal Regulations,
10-1-25 edition, GovInfo,
https://www.govinfo.gov/content/pkg/CFR-2025-title45-vol2/pdf/CFR-2025-title45-vol2-sec160-103.pdf (checked 2026-11-01)

[H5] 45 CFR § 164.510(b), Uses and disclosures for involvement in the individual's care, 10-1-25 edition, GovInfo,
https://www.govinfo.gov/content/pkg/CFR-2025-title45-vol2/pdf/CFR-2025-title45-vol2-sec164-510.pdf (checked 2026-11-01)

[H6] 45 CFR § 164.502(e)(1)(ii), Disclosures to subcontractors, and § 164.502(g)(2), Personal representatives:
adults, 10-1-25 edition, GovInfo,
https://www.govinfo.gov/content/pkg/CFR-2025-title45-vol2/pdf/CFR-2025-title45-vol2-sec164-502.pdf (checked 2026-11-01)

[H7] Federal Trade Commission (FTC), Collecting, Using, or Sharing Consumer Health Information? Look to HIPAA, the
FTC Act, and the Health Breach Notification Rule (August 2024),
https://www.ftc.gov/business-guidance/resources/collecting-using-or-sharing-consumer-health-information-look-hipaa-ftc-act-health-breach
(checked 2026-11-01)

[H8] HHS, Does HIPAA allow a health care provider to communicate with a patient's family, friends, or other persons
who are involved in the patient's care?,
https://www.hhs.gov/hipaa/for-professionals/faq/2087/does-hipaa-allow-a-health-care-provider-to-communicate-with-a-patients-family-friends-or-other-persons-who-are-involved-in-the-patient-care.html
(checked 2026-11-01)

[F1] FTC, FTC Finalizes Changes to the Health Breach Notification Rule (press release, April 26, 2024),
https://www.ftc.gov/news-events/news/press-releases/2024/04/ftc-finalizes-changes-health-breach-notification-rule
(checked 2026-11-01)

[F2] FTC, Complying with FTC's Health Breach Notification Rule (July 2024, edited January 2025),
https://www.ftc.gov/business-guidance/resources/complying-ftcs-health-breach-notification-rule-0 (checked 2026-11-01)

[F3] FTC, Health Breach Notification Rule: The Basics for Business (July 2024),
https://www.ftc.gov/business-guidance/resources/health-breach-notification-rule-basics-business (checked 2026-11-01)

[F4] FTC, Health Breach Notification Rule, final rule, 89 Fed. Reg. 47028 (May 30, 2024), 16 CFR Part 318, GovInfo,
https://www.govinfo.gov/content/pkg/FR-2024-05-30/pdf/2024-10855.pdf (checked 2026-11-01)

[S1] Washington State Legislature, Chapter 19.373 RCW, Washington My Health My Data Act,
https://app.leg.wa.gov/RCW/default.aspx?cite=19.373&full=true (checked 2026-11-01)

[S2] Washington State Office of the Attorney General, Protecting Washingtonians' Personal Health Data and Privacy
(FAQ), https://www.atg.wa.gov/protecting-washingtonians-personal-health-data-and-privacy (checked 2026-11-01)

[S3] Nevada Legislature, NRS Chapter 603A, Security and Privacy of Personal Information (NRS 603A.400–603A.550,
consumer health data, from SB 370 of 2023), https://www.leg.state.nv.us/nrs/nrs-603a.html (checked 2026-11-01)

[S4] Connecticut General Assembly, Public Act No. 23-56 (Substitute Senate Bill No. 3), section 2,
https://www.cga.ct.gov/2023/act/Pa/pdf/2023PA-00056-R00SB-00003-PA.PDF (checked 2026-11-01)

[P1] DeepSeek, DeepSeek Privacy Policy (last updated February 10, 2026),
https://cdn.deepseek.com/policies/en-US/deepseek-privacy-policy.html (checked 2026-11-01)

[P2] Amazon Web Services, HIPAA Eligible Services Reference (last updated October 15, 2026),
https://aws.amazon.com/compliance/hipaa-eligible-services-reference/ (checked 2026-11-01)

## Condensed version (150 words or fewer)

The class build uses synthetic data only.

## Open questions


# Knowledge sources (Task S; backup by Anmol, in case Sriya's version does not arrive)

Instructions: `docs/rag-memory/README.md`, Task S. Keep these headings.

## Sources table

| Source | What it is | Why we need it | How it's ingested (API / bulk / upload) | Update rate | Trust level | Cost / license | Official URL | Checked |
|---|---|---|---|---|---|---|---|---|
| Discharge summary / med list | The patient's discharge plan: medicines (`med-1`, dose, timing, status, brands, plain name), stopped medicines (`stopped-1`), instructions (`weigh-1`, `avoid-1`), warning signs with tiers (`warn-1`), appointments, contacts (`contact-1`). Example: `fixtures/p001.json` (synthetic) | The source of truth for everything patient-specific; outranks labels ("plan > references > memory", design.md A) | Upload or photo by the caregiver → Prompt A → structured care plan JSON → in the prompt every turn as `{{care_plan}}` (CAG, about 1,500 tokens) | Only when a new discharge document is uploaded | Highest: written by the care team; the caregiver confirms the extracted JSON | Free (our own data); per patient, never shared, never used for retrieval across patients | n/a | n/a (repo file) |
| Cabinet inventory | Bottles at home (`cab-1`, ...) read from photos, compared with the plan into the cabinet diff (`flag-1`, labels such as `dose_changed`, `stopped_still_present`) | Finds old, duplicate, or missing bottles: the core feature | Bottle photos → Prompt A → cabinet JSON → diff → in the prompt as `{{cabinet_diff}}` (CAG) | When the caregiver re-scans | Medium: OCR can misread; names go through the RxNav check; unclear items become `pharmacist_check` | Free; per patient, never shared | n/a | n/a (repo file) |
| DailyMed (FDA SPL labels) | NLM's database of drug labeling submitted to FDA by companies, in SPL format [2] | Full label text (warnings, interactions, adverse reactions) for retrieval; the human-readable copy we can link and cite | Web services (REST, v2: `/dailymed/services/v2/`) [3]; bulk zip downloads, full releases plus daily, weekly, and monthly update files [4] | Continuous: daily update files posted (files dated Oct 26, 28, 29, 30, 2026 seen) [4]; database date "Oct 30, 2026" in our test request | Official, but "NLM does not review any SPL content prior to publication" [2]; the content is the manufacturer's | Free, no key [3]. License not stated on the pages we read; site links NLM copyright page `[VERIFY]` | https://dailymed.nlm.nih.gov/dailymed/ | 2026-11-01 |
| openFDA drug label API | FDA's JSON API over SPL label files: `https://api.fda.gov/drug/label.json` [5] | Our retrieval corpus (design.md A: labels fetched offline from openFDA and chunked by section) | API (offline fetch per drug, cached) | Updated weekly [5]; `meta.last_updated` = 2026-10-30 in our test request | Official FDA data, but the API says "Do not rely on openFDA to make decisions regarding medical care ... assume all results are unvalidated" [5] | Free. Without key: 240 requests/min and 1,000/day per IP; with free key: 240/min and 120,000/day per key [6]. Content public domain, CC0 1.0 (except some privately supplied copyrighted works) [7] | https://open.fda.gov/apis/drug/label/ | 2026-11-01 |
| RxNorm / RxNav | RxNorm: NLM's normalized drug names and ids (RxCUI). RxNav: NLM's free REST APIs over it [8] | Name check before retrieval: name → RxCUI (`rxcui.json?name=`), brand → ingredient (`rxcui/{id}/related.json?tty=IN`) [9], spelling-tolerant match (`approximateTerm.json`, returns score and rank) [10]. No match → `pharmacist_check` | API at runtime (lookup, not text in the prompt); NLM asks to cache results 12–24 hours [8] | RxNorm: full monthly release plus weekly updates (latest full release listed: Oct 5, 2026) [11] | High for names/ids: national standard vocabulary. Not a clinical-advice source; NLM "does not intend to give specific medical advice" [8] | Free, no key. Max 20 requests/second per IP (100/s with an optional UTS API key) [8]. "With one exception, no license is needed to use these APIs" [8]; the exception is not named on the page (likely SNOMED CT in RxClass) `[VERIFY]`. The UMLS license applies to downloading the full RxNorm release files, not to the API [11]. Required attribution: "This product uses publicly available data from the U.S. National Library of Medicine (NLM) ..." [8] | https://lhncbc.nlm.nih.gov/RxNav/ | 2026-11-01 |
| MedlinePlus / MedlinePlus Connect | NLM's patient-friendly health pages; Connect is a free web service that returns MedlinePlus links for a code (drugs: RxCUI or NDC) [12] | "Learn more" links in plain language for the caregiver (optional; not retrieved into the prompt) | Connect API by RxCUI [13]; we show links only | Not stated `[VERIFY]` | High (NLM), patient-level reading | Free, no registration [12]; max 100 requests/min per IP, cache 12–24 hours [13]. Drug monographs are ASHP-copyrighted: health IT systems "may not ingest and/or brand" them; single direct links are allowed [14]. So we **link, never ingest** drug pages | https://medlineplus.gov/medlineplus-connect/ | 2026-11-01 |

## Tested requests

All on 2026-11-01, one at a time, drug names (or the public RxCUI they returned) only, no API key.

| API | Request URL | What came back (one line) |
|---|---|---|
| RxNav (name → RxCUI) | `https://rxnav.nlm.nih.gov/REST/rxcui.json?name=furosemide` (also `?name=Lasix`) | `{"idGroup":{"rxnormId":["4603"]}}`; Lasix returned `202991` (the brand concept) |
| RxNav (brand → generic) | `https://rxnav.nlm.nih.gov/REST/rxcui/202991/related.json?tty=IN` (getRelatedByType [9]) | One concept with `tty: "IN"`: `rxcui 4603, name "furosemide"`, so Lasix → furosemide works |
| openFDA label | `https://api.fda.gov/drug/label.json?search=openfda.generic_name:furosemide&limit=1` | 145 matching labels; first: set_id `01a5f094-b473-4e46-9e61-69d5ec6dd766`, effective 2023-03-01, has `warnings`, `drug_interactions`, `adverse_reactions`; `meta.disclaimer` = "Do not rely on openFDA to make decisions regarding medical care..."; `last_updated` 2026-10-30 |
| DailyMed | `https://dailymed.nlm.nih.gov/dailymed/services/v2/spls.json?drug_name=furosemide&pagesize=1` | 233 SPLs; first was "SALIX (FUROSEMIDE) INJECTION [MERCK SHARP & DOHME CORP.]" (an injection, likely the veterinary product), so a selection rule (oral, human Rx/OTC) is needed, as the retrieval experiment found for openFDA |
| MedlinePlus Connect | `https://connect.medlineplus.gov/service?mainSearchCriteria.v.cs=2.16.840.1.113883.6.88&mainSearchCriteria.v.c=4603&mainSearchCriteria.v.dn=furosemide&knowledgeResponseType=application/json` (code system = RxNorm) | 3 links: "Furosemide" (medlineplus.gov/druginfo/meds/a682858.html), "Furosemide Injection", "Blood Pressure Medicines" |
| NLM interaction API (retired; checked only to confirm) | `https://rxnav.nlm.nih.gov/REST/interaction/interaction.json?rxcui=4603` | HTTP 404 "Not found" |

## NLM Drug Interaction API status

Status: Discontinued. RxNav's home page (news, entry dated July 3, 2023) says: "Upcoming changes: The Drug-Drug
Interaction API will be discontinued on or about January 2, 2024. RxNav's Interactions tab will also be removed." [8]
Our test request to the old endpoint returned HTTP 404 (see Tested requests).
Date retired: on or about January 2, 2024, announced in NLM's July 3, 2023 news entry ("The Drug-Drug Interaction API
will be discontinued on or about January 2, 2024") [8]; re-checked 2026-11-01.
Official source (URL, checked date): https://lhncbc.nlm.nih.gov/RxNav/ (news section on the home page; the
separate news page https://lhncbc.nlm.nih.gov/RxNav/news/RxNavNews.html returned 403 to us), checked 2026-11-01.
What we use instead: NLM's notice names **no replacement**; we found no official NLM or FDA statement suggesting one
`[VERIFY]`. HomeStretch's design: interaction questions are answered only from the retrieved label sections
(`drug_interactions`, `warnings`, OTC "ask a doctor before use") from openFDA/DailyMed, cited as "the label says",
plus the plan's own instructions (e.g. `avoid-1`); anything not covered goes to the pharmacist (`contact-2`). We do
not claim to run a full interaction check. Commercial interaction databases exist but are out of scope (cost, license).

## Name matching experiment (Task S-tech)

Anmol's backup run. Setup and rule written before running in `design.md`, Section A ("Name matching experiment").
Script `spikes/name_match_check.py`; answer key `spikes/name_truth_anmol.csv` (151 names from
`evals/stress/stress.yaml`, drafted by script and corrected by hand: 3 verapamil rows and 5 unmatched spellings fixed);
output `spikes/name_match_results.txt`; RxNav cache `spikes/.cache_rxnav_names.json` (2026-11-01). No LLM calls.

Decision rule (written before running): the approach and cutoff with zero (or the fewest) `wrong_drug`, then the most
`correct`; Zorvexa must come back `no_match`.

| Approach | Cutoff | Correct | Wrong drug | No match (real drug) | Zorvexa = no match? |
|---|---|---|---|---|---|
| A. Exact RxNav | n/a | 38 | 0 | 113 | yes |
| B. Approximate RxNav | score ≥ 0 / 4 | 120 | 3 | 28 | yes |
| B. Approximate RxNav | score ≥ 6 | 108 | 3 | 40 | yes |
| B. Approximate RxNav | score ≥ 8 | 74 | 2 | 75 | yes |
| C. Local fuzzy (difflib) | 0.6 | 137 | 1 | 13 | yes |
| C. Local fuzzy (difflib) | **0.7** | **115** | **0** | 36 | yes |
| C. Local fuzzy (difflib) | 0.8 | 96 | 0 | 55 | yes |
| C then A (post-hoc) | 0.7 | 121 | 0 | 30 | yes |
| B at p75 of its own scores (12.53; Sriya's run, `sources.md`) | 12.53 | 30 | 0 | 121 | yes |

One answer-key fix after the first run, disclosed: "Vitamin D3" returned RxNorm's "vitamin d3", which is the same
substance as the key's "cholecalciferol"; both names now count as correct (A went from 1 wrong to 0, B from 4 to 3).
Judgement calls in the key: `1ASLX` → Lasix → furosemide; `Cntrcsto` → Entresto; `C0rcg` → Coreg; `F0prol XL` →
Toprol XL. No row was marked UNREADABLE.

Wrong-drug cases:
- B at every cutoff we set (up to score 8): `Slrnvastatin` → **cerivastatin** (a statin withdrawn from the market; true simvastatin);
  `VERAPARNIL HYDROCHLORIDC` → **hydrochloric acid** (true verapamil); below score 8 also `1lsinopril` →
  **fosinopril** (a different blood pressure drug; true lisinopril). Look-alike matches are exactly the danger.
- C at 0.6: `VERAPAMIL HYDROCHLORIDE` → hydrochlorothiazide (the shared word "hydrochloride").

Decision and why:
- **By the pre-registered rule: C, local fuzzy match at 0.7** (0 wrong drugs, 115 of 150 real drugs correct, Zorvexa
  no match). Caveat: its list here is the answer key's own drugs plus brands, so it is optimistic; in the app the list
  is the patient's plan and common brands, and a real drug missing from the list gets no match (safe:
  `pharmacist_check`), never a guess.
- **B, approximate RxNav, rejected:** wrong real drugs at every cutoff up to 8, including a withdrawn statin; at the
  one cutoff where it is safe (p75, 12.53, Sriya's run) it finds just 30 of 150.
- **A, exact RxNav, kept as the second step** (post-hoc, from these results): it never matched a wrong drug and it
  recognizes real drugs that are not on the list (Advil, Tylenol). The design uses **C (0.7) on the patient's list,
  then A**, then `pharmacist_check` (121 correct, 0 wrong). Because this combination was chosen after seeing results,
  it needs a fresh set of names to confirm.
- **Realistic re-run (added after the first run):** C's list above was the answer key's own drugs, which is optimistic.
  Matching each stress-test bottle only against *its own patient's* plan (names and brands from `fixtures/synthea/`),
  then exact RxNav: **315 of 379 (patient, bottle) pairs correct, 0 wrong drug**; 64 got no match and would go to
  `pharmacist_check`, mostly over-the-counter bottles not in the plan written as "Tylenol (acetaminophen)", "Aspirin low
  dose", "Advil (ibuprofen)". 
- **Bracket fix, tested on 16 fresh names** (written after the per-patient run; mostly over-the-counter labels such as
  "Motrin IB (ibuprofen)", plus 2 made-up names; truth confirmed with RxNav): trying the name inside and before the
  brackets took Rosa's-list-then-exact from **2 to 14 of 16 correct, 0 wrong drugs**. Misses: "Bayer Low Dose Aspirin"
  (no brackets, extra words) and "LISIN0PRIL 10 MG" (the strength lowers the fuzzy score below 0.7). Next: strip
  strengths and dose-form words before matching, then test on yet another fresh set.
- This test works at the ingredient level, so it cannot tell metoprolol succinate from tartrate; the retrieval filter
  (stopped drugs only when named) covers that.

## Added from Sriya's version (`sources.md`, branch `rag-memory-sriya`, 2026-11-02)

Her version reached the same results independently: the same 151 names, 150 of 151 identical answers (Vitamin D3:
"vitamin d3" vs "cholecalciferol", both accepted by both scorers), exact 38/0/113 and fuzzy 0.7 115/0/36 as ours,
approximate 121/3/27 (ours 120/3/28: her script also follows RxNav's history lookup for retired codes, which recovers
Microzide). Rerun from her cache with 0 requests, matching her table. Facts she found that we lacked, citations hers,
not re-opened by us:
- DailyMed: "in use" labeling may differ from the most recent FDA-approved labeling (her [1]).
- RxNorm: the full release comes out on the first Monday of each month, and RxNav updates with it (her [11]).
- MedlinePlus Connect: clients over the rate limit are blocked for 300 seconds; English and Spanish; also accepts
  ICD-10 and LOINC codes (her [13][14]).
- The retired interaction API's data came from ONCHigh and DrugBank (her [16]; release number `[VERIFY]`).
Not taken: "Data.gov lists ODbL" for DailyMed (third-party; she marked it `[VERIFY]`). Open conflict: she names the
RxNav licence exception as SNOMED CT in RxClass, citing the terms page; we found that page does not name it `[VERIFY]`.

## References

[1] HomeStretch team, Synthetic patient care plan and cabinet diff, `fixtures/p001.json` (repo file; synthetic data)
[2] U.S. National Library of Medicine, DailyMed Overview, https://dailymed.nlm.nih.gov/dailymed/about-dailymed.cfm (checked 2026-11-01)
[3] U.S. National Library of Medicine, DailyMed Web Services, https://dailymed.nlm.nih.gov/dailymed/app-support-web-services.cfm (checked 2026-11-01)
[4] U.S. National Library of Medicine, DailyMed: Download All Drug Labels, https://dailymed.nlm.nih.gov/dailymed/spl-resources-all-drug-labels.cfm (checked 2026-11-01)
[5] U.S. Food and Drug Administration, openFDA Drug Labeling API, https://open.fda.gov/apis/drug/label/ (checked 2026-11-01)
[6] U.S. Food and Drug Administration, openFDA Authentication (API keys and rate limits), https://open.fda.gov/apis/authentication/ (checked 2026-11-01)
[7] U.S. Food and Drug Administration, openFDA Terms of Service, https://open.fda.gov/terms/ (checked 2026-11-01)
[8] National Library of Medicine, RxNav (home page with news) and RxNav Terms of Service, https://lhncbc.nlm.nih.gov/RxNav/ and https://lhncbc.nlm.nih.gov/RxNav/TermsofService.html (checked 2026-11-01)
[9] National Library of Medicine, RxNorm API: getRelatedByType, https://lhncbc.nlm.nih.gov/RxNav/APIs/api-RxNorm.getRelatedByType.html (checked 2026-11-01)
[10] National Library of Medicine, RxNorm API: getApproximateMatch, https://lhncbc.nlm.nih.gov/RxNav/APIs/api-RxNorm.getApproximateMatch.html (checked 2026-11-01)
[11] National Library of Medicine, RxNorm Files (monthly and weekly releases), https://www.nlm.nih.gov/research/umls/rxnorm/docs/rxnormfiles.html (checked 2026-11-01)
[12] National Library of Medicine, MedlinePlus Connect, https://medlineplus.gov/medlineplus-connect/ (checked 2026-11-01)
[13] National Library of Medicine, MedlinePlus Connect: Technical Information, https://medlineplus.gov/medlineplus-connect/technical-information/ (checked 2026-11-01)
[14] National Library of Medicine, MedlinePlus: Using Content from MedlinePlus, https://medlineplus.gov/about/using/usingcontent/ (checked 2026-11-01)

## Condensed version (150 words or fewer)

HomeStretch uses two private sources and four public ones. The discharge plan and the cabinet scan belong to one
patient. The caregiver uploads them, Prompt A turns them into JSON, and that JSON goes into every prompt (CAG). It
is never shared. FDA drug labels come from openFDA, which is free, updated weekly and public domain (CC0). We
fetch them offline and retrieve them per question (RAG). DailyMed holds the same labels for linking and bulk
download. RxNav (NLM, free, 20 requests/second, no license for the API) maps bottle names to ingredients before
retrieval. When it finds no match, the answer is "ask the pharmacist". MedlinePlus pages are shown as links only,
because ASHP's drug text cannot be copied into the app. NLM retired its drug-interaction API around January 2,
2024, so interaction answers come only from cited label sections or the pharmacist [1–14].

| Source | Use | Limit / license |
|---|---|---|
| Care plan, cabinet | In prompt (CAG) | Per patient, private |
| openFDA labels | RAG corpus | 1,000/day no key; CC0 |
| RxNav | Name check | 20 req/s/IP; free |
| MedlinePlus | Links | No ingesting ASHP text |

## Open questions

- DailyMed's license is not stated on the DailyMed pages we read (only a footer link to NLM's copyright page). Is it
  enough to cite openFDA's CC0 terms for the label text? `[VERIFY]`
- The RxNav terms say "with one exception, no license is needed" but do not name the exception. We assume it is
  SNOMED CT in RxClass, which we do not use `[VERIFY]`.
- NLM's interaction-API notice names no replacement. Is "label sections + pharmacist" enough for the doc, or should
  we name a commercial option (out of scope)?
- MedlinePlus Connect gives links only. Do we use it at all in v6, or leave it for later?
- The DailyMed test request returned an injection first, so labels need a selection rule there as well as in openFDA.


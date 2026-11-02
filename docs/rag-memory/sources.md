# Knowledge sources (Task S, Sriya)

Instructions: `docs/rag-memory/README.md`, Task S. Keep these headings.

> **How these were checked (2026-11-02).** This draft was written with Claude Code in a cloud session whose network
> policy blocked direct access to `nlm.nih.gov`, `fda.gov` and `medlineplus.gov`. Facts below come from web-search
> results that quote the official pages listed. Sriya opens each official URL once in a browser to confirm before
> hand-in; anything only seen in a third-party source, or not found at all, is marked `[VERIFY]`.

## Sources table

| Source | What it is | Why we need it | How it's ingested (API / bulk / upload) | Update rate | Trust level | Cost / license | Official URL | Checked |
|---|---|---|---|---|---|---|---|---|
| Discharge summary / med list | The patient's own hospital discharge plan: medicines (`med-1`…), stopped medicines (`stopped-1`), warning signs (`warn-1`), contacts (`contact-1`), daily tasks (`weigh-1`, `avoid-1`). Example: `fixtures/p001.json` (Rosa Delgado, synthetic) | Ground truth for "what she should be taking"; every reply cites its ids | Caregiver uploads the document or a photo → Prompt A-style extraction → structured care plan JSON → caregiver confirms → placed in the prompt whole (CAG, not RAG: small and per patient) | Once at discharge; again only when a clinician changes the plan | Highest (from the care team), but only after the caregiver confirms the extracted text | Patient's own data; never shared across patients. Sensitive health data (see `compliance.md`) | n/a | 2026-11-02 |
| Cabinet inventory | The bottles actually at home (`cab-1`, `cab-2`, …): name, strength, directions as printed | Input to the cabinet diff (flags `ok`, `dose_changed`, `stopped_still_present`, …) | Bottle photo → OCR → Prompt A (`prompts/extract_v2.md`) → cabinet JSON; unreadable fields stay `"unreadable"`; names normalized with RxNorm (see experiment below) | Each time the caregiver scans bottles | Medium: OCR errors are common, so a non-matching name becomes `pharmacist_check`, never a guess | Patient's own data; never shared | n/a | 2026-11-02 |
| DailyMed (FDA SPL labels) | NLM's site with the FDA drug labels ("package inserts") submitted by manufacturers, in Structured Product Labeling (SPL) XML [1] | Full, current label text (warnings, interactions, adverse reactions, dosing) to ground answers with a citable `set_id` | REST web services v2 (GET only, `.json` or `.xml`; e.g. `/services/v2/spls.json`, `/spls/{SETID}`) [2]; or bulk zip downloads (full release, plus daily/weekly/monthly updates) [3] | Labels posted as FDA receives them; bulk updates daily/weekly/monthly [3]. DailyMed notes "in use" labeling may differ from the latest FDA-approved labeling [1] | High (official manufacturer label, distributed by NLM) | Free. Exact license `[VERIFY]`: Data.gov lists ODbL; no official NLM reuse statement found [VERIFY] | https://dailymed.nlm.nih.gov/dailymed/app-support-web-services.cfm | 2026-11-02 |
| openFDA drug label API | FDA's public API serving the same SPL labels as JSON, one field per label section (`warnings`, `drug_interactions`, `adverse_reactions`, …) | Easiest way to fetch label sections by drug name for chunking (used in Darshan's D-tech experiment) | API: `https://api.fda.gov/drug/label.json?search=...` [4] | Weekly [4] (tested reply: `last_updated` 2026-10-30) | High source, but every reply carries the disclaimer "Do not rely on openFDA to make decisions regarding medical care … assume all results are unvalidated" (seen in tested request) [5] | Free; CC0 1.0 public domain unless marked otherwise [6]. Rate limit: no key 240 requests/min and 1,000/day per IP; with free key 240/min and 120,000/day per key [7] | https://open.fda.gov/apis/drug/label/ | 2026-11-02 |
| RxNorm / RxNav | NLM's standard drug vocabulary (RxNorm) and its free REST APIs (RxNav). Every drug concept has an RxCUI; term types include IN (ingredient) and BN (brand) | Normalize messy bottle names to one ingredient; brand ↔ generic (Lasix → furosemide); "no match" for made-up drugs | API, base `https://rxnav.nlm.nih.gov/REST/`: name → RxCUI `rxcui.json?name=` [8]; spelling-tolerant `approximateTerm.json?term=&maxEntries=` (returns score and rank, "higher is better") [9]; RxCUI → ingredient / brand → generic `rxcui/{rxcui}/related.json?tty=IN` (works: Lasix 202991 → furosemide 4603, tested 2026-11-02; official getRelatedByType doc page not opened [VERIFY]; related-by-relationship page [10]) | RxNorm full release monthly (first Monday of the month), weekly additive updates; RxNav updated with the monthly release [11] | High (NLM standard) | Free. API: "With one exception, no license is needed to use these APIs" (the exception is SNOMED CT content in RxClass, which we don't use) [12]; downloading full RxNorm files needs a UMLS license [11]. Limit: 20 requests/second per IP; cache results 12–24 h [12] | https://lhncbc.nlm.nih.gov/RxNav/APIs/RxNormAPIs.html | 2026-11-02 |
| MedlinePlus / MedlinePlus Connect | NLM's plain-language health site; Connect is a free web service that returns links to MedlinePlus pages for a code (RxCUI, NDC, ICD-10, LOINC) [13] | Plain-words drug and condition explanations for the caregiver ("what is a water pill"), linked rather than copied | Connect REST: `https://connect.medlineplus.gov/service?mainSearchCriteria.v.cs=2.16.840.1.113883.6.88&mainSearchCriteria.v.c=<RxCUI>&knowledgeResponseType=application/json` (XML default; JSON available; English or Spanish) [13] | Not stated `[VERIFY]` | High (NLM) | Free. Limit 100 requests/min per IP; over-limit blocked 300 s; cache 12–24 h [14]. Drug pages are AHFS® Consumer Medication Information, © ASHP, licensed for MedlinePlus only; not to be ingested into a health IT system [15]. So we **link** to MedlinePlus drug pages, never copy them into our index | https://medlineplus.gov/medlineplus-connect/technical-information | 2026-11-02 |
| NLM Drug Interaction API | RxNav's former drug-drug interaction service (data from ONCHigh and DrugBank) | Would have answered "can she take Advil with her water pill" | **Not used: discontinued** (see below) | n/a | n/a | n/a | https://lhncbc.nlm.nih.gov/RxNav/news/news.html | 2026-11-02 |

## Tested requests

Run by Sriya in a browser on 2026-11-02 (no key needed for any of them). Answers copied from the actual replies.

| API | Request URL | What came back (one line) |
|---|---|---|
| RxNav (name → RxCUI) | https://rxnav.nlm.nih.gov/REST/rxcui.json?name=furosemide | `{"idGroup":{"rxnormId":["4603"]}}`: furosemide = RxCUI 4603; no key needed (2026-11-02) |
| RxNav (brand → generic) | Step 1: https://rxnav.nlm.nih.gov/REST/rxcui.json?name=Lasix ; Step 2: https://rxnav.nlm.nih.gov/REST/rxcui/202991/related.json?tty=IN | Step 1: Lasix = RxCUI 202991. Step 2: one ingredient (TTY=IN): furosemide, RxCUI 4603. So brand → generic works (2026-11-02) |
| RxNav (approximate) | https://rxnav.nlm.nih.gov/REST/approximateTerm.json?term=1ISIN0PRIL&maxEntries=1 | Top candidate lisinopril, RxCUI 29046, score 5.9787, rank 1, listed by 14 source vocabularies (RXNORM, USP, MTHSPL, …) (2026-11-02) |
| openFDA label | https://api.fda.gov/drug/label.json?search=openfda.generic_name:%22furosemide%22&limit=1 | 145 furosemide labels; first: furosemide 80 mg tablets, set_id 01a5f094-b473-4e46-9e61-69d5ec6dd766, effective_time 20230301, with `warnings`, `drug_interactions`, `adverse_reactions`, `dosage_and_administration` sections. `meta.last_updated` 2026-10-30. `meta.disclaimer`: "Do not rely on openFDA to make decisions regarding medical care." (2026-11-02) |
| DailyMed | https://dailymed.nlm.nih.gov/dailymed/services/v2/spls.json?drug_name=furosemide&pagesize=1 | 233 SPLs for furosemide; first: "SALIX (FUROSEMIDE) INJECTION [MERCK SHARP & DOHME CORP.]", setid c3ff7e14-8232-40df-a5c8-60f98f5c1025, published Oct 30, 2026. This first hit is an injection (Salix appears to be a veterinary product [VERIFY]), so retrieval must filter to human oral labels (2026-11-02) |
| MedlinePlus Connect | https://connect.medlineplus.gov/service?mainSearchCriteria.v.cs=2.16.840.1.113883.6.88&mainSearchCriteria.v.c=4603&knowledgeResponseType=application/json | Atom feed (JSON), "MedlinePlus Connect results for RXCUI 4603": 3 entries with links: "Furosemide" (medlineplus.gov/druginfo/meds/a682858.html), "Furosemide Injection", "Blood Pressure Medicines". Each has a plain-language summary ("diuretics ('water pills')") (2026-11-02) |

## NLM Drug Interaction API status

Status: Discontinued. RxNav's release notes (version 2.9.119) announce that the Drug-Drug Interaction API and RxNav's
Interactions tab would be shut down; the other RxNorm/RxNav APIs remain available [16][17].
Date retired: Scheduled for "on or about January 2, 2024" [16]. Exact shutdown date not confirmed `[VERIFY]`.
Official source (URL, checked date): https://lhncbc.nlm.nih.gov/RxNav/news/news.html and
https://lhncbc.nlm.nih.gov/RxNav/APIs/InteractionAPIs.html (checked 2026-11-02, via search results)
What we use instead: NLM names no replacement `[VERIFY]` (none found in official pages). HomeStretch retrieves the
**`drug_interactions` and `warnings` sections of the FDA label** (openFDA [4] / DailyMed [2]) for each drug in the
question, cites them as refs, and if the label does not answer the question, sends the caregiver to the pharmacist
(`pharmacist_check` / the pharmacy contact). We do not compute interactions ourselves. This replacement is our design
choice, not an NLM recommendation.

## Name matching experiment (Task S-tech)

**Question.** OCR reads a bottle as `1ISIN0PRIL`, `advi1 (ibuprofcn)` or the made-up `Zorvexa`. Which way of turning
that text into a real drug gets the most right, and says "no match" when there is no real drug, without ever matching
the wrong drug?

**Test set (fixed before running).** All 151 unique `name:` values in `evals/stress/stress.yaml` (OCR-style misreads
made by `evals/stress.py` with the swaps i↔l, l↔1, o↔0, m↔rn, e↔c, t↔f, plus brand names and one made-up drug). Answer
key: `spikes/name_truth.csv` (`name,true_generic`), hand-checked by Sriya. 150 rows are real drugs (25 distinct
ingredients); 1 row is `NONE` (`Zorvexa`); 0 rows are `UNREADABLE`.

**Approaches (same 151 names; only the matching method changes).**
- **A. Exact RxNav:** `rxcui.json?name=<name>` [8]. Any RxCUI → ingredient(s) via `rxcui/{rxcui}/related.json?tty=IN`
  [VERIFY]; no RxCUI → `no_match`.
- **B. Approximate RxNav:** `approximateTerm.json?term=<name>&maxEntries=1` [9]; take the top candidate and its score;
  RxCUI → ingredient(s) the same way as A. Score below the cutoff → `no_match`.
- **C. Local fuzzy (no API):** `difflib.get_close_matches(name.lower(), vocabulary, n=1, cutoff=c)`. `vocabulary` = the
  25 ingredients in the answer key plus their common brand names (Lasix, Toprol XL, Zestril, Coreg, Plavix, Lipitor,
  Zocor, Norvasc, Cozaar, Microzide, Glucophage XR, Entresto, Advil, Aleve, Tylenol), lowercased; a brand maps to its
  ingredient. **Limit:** C can only ever find drugs already in its list (in the app, the patient's own plan and
  cabinet), so it can never recognize a real drug missing from the plan; and here its list is built from the answer
  key, which flatters it.
- Predicted and true ingredients are compared lowercased; several ingredients are sorted and joined with ` / `.

**Cutoffs (fixed before running).**
- B: no cutoff (always take the top candidate), then the 25th, 50th and 75th percentile of B's top-candidate scores
  over the 151 names. The script computes these by rule, so we don't pick numbers after seeing which ones look good.
  (RxNav's score scale changed in 2021 [VERIFY], so fixed numbers can't be chosen in advance.)
- C: 0.6, 0.7, 0.8, 0.9.

**Scoring per name.**
- `correct`: predicted ingredient = true ingredient, or `no_match` on a `NONE` row.
- `wrong_drug` (dangerous): matched to a different real drug, or matched any drug on a `NONE` row (`Zorvexa`).
- `no_match`: no match on a real drug (safe but unhelpful; the app falls back to `pharmacist_check`).
- `UNREADABLE` rows are reported separately and should get `no_match` (there are none in this set).

Decision rule (written before running):
1. Fewest `wrong_drug` (zero is the goal). A wrong drug is worse than any number of misses.
2. Then most `correct`.
3. `Zorvexa` must come back `no_match`; a setup that matches it to any drug is out, whatever its other numbers.
4. If two setups tie, prefer B (RxNav) over C, because B can recognize a real drug that is not on the patient's list.

**Results** (final run, 2026-11-02, on Sriya's laptop; copied exactly as the script printed them). B's cutoffs come from
its score distribution: min 4.83074, 25th pct 6.58422, median 9.56498, 75th pct 12.5285, max 18.1185 (134 of 151 names
had a candidate).

| Approach | Cutoff | Correct | Wrong drug | No match (real drug) | Zorvexa = no match? |
|---|---|---|---|---|---|
| A. Exact RxNav | n/a | 38 | 0 | 113 | yes |
| B. Approximate RxNav | none | 121 | 3 | 27 | yes |
| B. Approximate RxNav | 6.58422 (p25) | 90 | 3 | 58 | yes |
| B. Approximate RxNav | 9.56498 (p50) | 58 | 2 | 91 | yes |
| B. Approximate RxNav | 12.5285 (p75) | 30 | 0 | 121 | yes |
| C. Local fuzzy (difflib) | 0.6 | 137 | 1 | 13 | yes |
| C. Local fuzzy (difflib) | 0.7 | 115 | 0 | 36 | yes |
| C. Local fuzzy (difflib) | 0.8 | 96 | 0 | 55 | yes |
| C. Local fuzzy (difflib) | 0.9 | 60 | 0 | 91 | yes |

Wrong-drug cases:
- B (no cutoff and p25): `1lsinopril` → fosinopril (true: lisinopril); `Slrnvastatin` → cerivastatin (true:
  simvastatin); `VERAPARNIL HYDROCHLORIDC` → hydrochloric acid (true: verapamil). At p50 the last two remain; at p75, none.
- C at 0.6: `VERAPAMIL HYDROCHLORIDE` → hydrochlorothiazide (true: verapamil). The shared salt word "hydrochlor…"
  outweighed the drug name.
- A: none. Every name is either exact or a miss.

Every wrong drug is a real, similar-sounding drug (another ACE inhibitor, another statin). That is the dangerous
failure: a confident wrong name would make the cabinet diff wrong.

Decision and why: **C, local fuzzy match at cutoff 0.7.** Applying the rule: five setups have zero wrong drugs (A 38
correct; B p75 30; C 0.7 115; C 0.8 96; C 0.9 60). Of these, C at 0.7 has the most correct, and `Zorvexa` is `no_match`
everywhere. B finds the most drugs (121), but only by also making wrong matches; at the one cutoff where it is safe
(p75), it finds just 30. The 36 names C misses fall back to `pharmacist_check`, which is safe.

Caveats and how we'd use it:
- C can only find drugs already in its list, so it **cannot recognize a real drug missing from the plan**. In the app
  its list is the patient's own plan and cabinet. In this test its list came from the answer key, which flatters it.
- A suggested app order (a design proposal, **not tested here** as one pipeline): (1) C at 0.7 against the patient's
  plan; (2) if no match, A (exact RxNav, 0 wrong drugs here) to name a real drug that is not on the plan, giving
  `not_on_list`; (3) otherwise `no_match` → `pharmacist_check`. B is not used without a much higher cutoff.
- Cutoffs were fixed before the run; we did not tune them on these results.

**Changes after run 1** (the first laptop run, same 151 names and same rule; recorded for transparency):
1. Script fix: RxNav's approximate search sometimes returns retired RxCUIs, which have no current properties, so they
   were scored `no_match`. The script now asks `rxcui/{rxcui}/historystatus.json` [VERIFY: official endpoint page]
   for the ingredient. This fixed Microzide. Nine B rows still resolve to `no_match` through a retired code: Toprol
   XL (×4 spellings), Glucophage XR (×5) / `METFORMIN HYDROCHLORIDE ER`, and `Aspirin low dose`. That is safe, and
   can't change the decision: even if all were correct, B at p75 would reach about 39 correct, below C at 0.7.
2. Answer-key fix: `Vitamin D3` changed from `cholecalciferol` to `vitamin d3`, because RxNorm has an ingredient
   concept with exactly that name (RxCUI 1244014). This was the answer key's error, not a wrong drug.
3. Run 1 numbers, for comparison: A 37/1/113; B none 119/4/28; C 0.7 114/0/37 (correct / wrong / no match).

Rerun check: run 2 sent 6 new requests (the history lookups); run 3 sent **0** requests ("HTTP requests sent this run: 0 (cache: 386 answers in .cache_rxnav.json)"), with an identical table. The experiment reruns fully offline from the cache.

## References

All checked 2026-11-02 (via web-search results; see note at top).

[1] U.S. National Library of Medicine, DailyMed Overview, https://dailymed.nlm.nih.gov/dailymed/about-dailymed.cfm (checked 2026-11-02)
[2] U.S. National Library of Medicine, DailyMed Web Services (RESTful API v2), https://dailymed.nlm.nih.gov/dailymed/app-support-web-services.cfm and https://dailymed.nlm.nih.gov/dailymed/webservices-help/v2/spls_api.cfm (checked 2026-11-02)
[3] U.S. National Library of Medicine, DailyMed SPL Resources: Download All Drug Labels, https://dailymed.nlm.nih.gov/dailymed/spl-resources-all-drug-labels.cfm (checked 2026-11-02)
[4] U.S. Food and Drug Administration, openFDA Drug Labeling API Overview, https://open.fda.gov/apis/drug/label/ (checked 2026-11-02)
[5] U.S. Food and Drug Administration, About the openFDA API, https://open.fda.gov/apis/ (checked 2026-11-02)
[6] U.S. Food and Drug Administration, openFDA Data Licensing and Terms of Service, https://open.fda.gov/license/ and https://open.fda.gov/terms/ (checked 2026-11-02)
[7] U.S. Food and Drug Administration, openFDA Authentication (rate limits), https://open.fda.gov/apis/authentication/ (checked 2026-11-02)
[8] U.S. National Library of Medicine, RxNorm API, https://lhncbc.nlm.nih.gov/RxNav/APIs/RxNormAPIs.html (checked 2026-11-02)
[9] U.S. National Library of Medicine, RxNorm API: getApproximateMatch, https://lhncbc.nlm.nih.gov/RxNav/APIs/api-RxNorm.getApproximateMatch.html (checked 2026-11-02)
[10] U.S. National Library of Medicine, RxNorm API: getRelatedByRelationship, https://lhncbc.nlm.nih.gov/RxNav/APIs/api-RxNorm.getRelatedByRelationship.html (checked 2026-11-02)
[11] U.S. National Library of Medicine, RxNorm Technical Documentation and FAQ (release schedule, licensing), https://www.nlm.nih.gov/research/umls/rxnorm/docs/rxnormfiles.html and https://www.nlm.nih.gov/research/umls/rxnorm/faq.html (checked 2026-11-02)
[12] U.S. National Library of Medicine, RxNav Terms of Service, https://lhncbc.nlm.nih.gov/RxNav/TermsofService.html (checked 2026-11-02)
[13] U.S. National Library of Medicine, MedlinePlus Connect: Web Service, https://medlineplus.gov/connect/service.html (checked 2026-11-02)
[14] U.S. National Library of Medicine, MedlinePlus Connect: Technical Information, https://medlineplus.gov/medlineplus-connect/technical-information (checked 2026-11-02)
[15] U.S. National Library of Medicine, MedlinePlus Copyright and Copyright FAQ, https://medlineplus.gov/copyright.html and https://medlineplus.gov/faq/copyrightfaq.html (checked 2026-11-02)
[16] U.S. National Library of Medicine, RxNav News / Release Notes (Drug Interaction API shutdown), https://lhncbc.nlm.nih.gov/RxNav/news/news.html (checked 2026-11-02)
[17] U.S. National Library of Medicine, Drug Interaction API, https://lhncbc.nlm.nih.gov/RxNav/APIs/InteractionAPIs.html (checked 2026-11-02)
[18] Anthropic, Claude Code (AI assistant), used to search for and draft this section; all facts checked against the official pages above by Sriya Kamarsu (2026-11-02)

## Condensed version (150 words or fewer)

HomeStretch uses two private, per-patient sources: the discharge care plan (kept whole in the prompt as CAG) and the
cabinet scan (bottle photo → Prompt A → JSON). Public drug knowledge comes from free NLM/FDA services. **openFDA** and
**DailyMed** provide FDA label sections (warnings, interactions, adverse reactions) for RAG [2][4]. **RxNorm/RxNav**
normalizes bottle names to ingredients [8]. **MedlinePlus** pages are linked, not copied, because their drug text is
licensed [15]. NLM's Drug Interaction API was discontinued (~January 2024) [16], so interaction questions use the
label's interactions section or go to the pharmacist.

Name matching (151 messy bottle names, rule: fewest wrong drugs, then most correct):

| Approach | Correct | Wrong drug |
|---|---|---|
| A. Exact RxNav | 38 | 0 |
| B. Approximate RxNav (no cutoff / safe p75) | 121 / 30 | 3 / 0 |
| **C. Local fuzzy, 0.7 (chosen)** | **115** | **0** |

`Zorvexa` → no match in all setups.

## Open questions

- DailyMed's license: Data.gov lists ODbL, but no official NLM reuse statement was found. Is "free, from NLM" enough for the doc? `[VERIFY]`
- The exact date the NLM Drug Interaction API went offline (announced for ~2024-01-02). `[VERIFY]`
- Nine B rows resolve to retired RxCUIs whose `historystatus.json` reply our parser can't read as an ingredient (Toprol
  XL, Glucophage XR, metformin ER, Aspirin low dose). This doesn't change the decision; worth a look if the app ever uses B.
- For Anmol: the suggested order C (plan) → A (exact RxNav) → `pharmacist_check` is untested as one pipeline. Test it in
  the integration scenario, or label it a proposal.

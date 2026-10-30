# HomeStretch: RAG, Memory & Data Handling (team work plan)

Building AI Applications, Assignment 3 · Group 5: Venkata Sriya Kamarsu, Anmol Shetty, Darshan Patil

This folder holds the design write-up for how HomeStretch retrieves drug knowledge, remembers context, and handles
sensitive data. It plugs into the Prompt B v4 system prompt (`prompts/agent_v4.md`). **Design and writing only, no app code.**

## Deliverable

A 1–2 page structured document (`draft.md`, built to PDF with `docs/build.py` like Assignment 2), with a clear flow, one
example scenario, and cited sources (data, APIs, laws, and AI tools). The assignment asks for four things:

1. **Knowledge sources and RAG:** what is retrieved, when, and how it enters the model's input.
2. **Memory:** short-term (session) and long-term (user-level), and how each improves the experience.
3. **Integration:** how RAG and memory fit the app flow, with at least one scenario compared against a baseline that has neither.
4. **Data evaluation:** sensitivity, compliance, access, and risks.

## Why this design (Assignment 2 feedback, Oct 25)

Full marks. The grader's next step for us: *"address the remaining edge cases you identified, particularly unsupported
safety language, unknown medications, timing differences, and multi-turn behavior."* Assignment 3 should show how RAG and
memory fix exactly those:

| Feedback item | Fixed by |
|---|---|
| Unsupported safety language (v4's 911 reply added advice not in the plan) | Grounding: clinical facts only from the plan or a retrieved, cited reference; output guardrail check |
| Unknown medications ("Zorvexa" matched to a real drug) | RxNorm lookup: no match means `pharmacist_check`, never a guess |
| Timing differences ("once daily" vs "at bedtime" called a dose change) | Structured schedule in memory and normalized directions |
| Multi-turn behavior | Short-term memory: the session state carries the open flags and the medicine being discussed |

## Who does what

Each person writes **only their own file**. Anmol merges everything into `draft.md`. That way nobody overwrites
anyone else's work.

| Person | Task | Files | Technical part |
|---|---|---|---|
| **Sriya** | S: Knowledge sources, verified + reference list. **S-tech:** drug-name matching experiment (3 approaches, on our 151 messy stress-test bottle names) | `sources.md`, `spikes/rxnorm_check.py`, `spikes/name_truth.csv` | Decides how HomeStretch normalizes bottle names, and proves the "unknown medication" fix |
| **Darshan** | D: Data inventory, compliance (HIPAA, FTC, state laws), risks table. **D-tech:** retrieval experiment (2 chunking × 3 search approaches, on real FDA labels) | `compliance.md`, `spikes/retrieval_check.py` | Decides chunking, search method, top-k, and the "I don't know" threshold |
| **Anmol** | A: RAG pipeline (intent routing, prompt slots, fallback, diagram), using Sriya's and Darshan's results. B: Memory design (3 approaches compared). C: Integration walkthrough + baseline vs HomeStretch scenario. Then merge, self-grade, build the PDF | `design.md`, then `draft.md` | Ties everything into Prompt B v6 |

## How we decide: try several approaches, pick on evidence

As in class: for every design choice, **try at least two or three approaches on the same test set, measure, and pick
the winner with a stated rule**, just as Assignment 2 compared prompt versions. Each experiment reports:

1. The approaches tried (one variable changed at a time).
2. The same test set for all of them.
3. A results table with the numbers.
4. **The decision rule, written before you run** (safety first: fewer *wrong* answers beats more right ones).
5. What we chose and why, in one or two sentences, and what failed.

No LLM API calls are needed for either experiment. Each script has one built-in self-check (`assert`s that run when
the script starts) so a broken script fails loudly instead of printing wrong numbers.

**Order:** Sriya and Darshan finish first, because Anmol condenses their files into the 2-page draft. Each teammate also
writes a **condensed version (150 words or fewer, plus their table)** at the bottom of their file. That is what goes in
the final doc; the full file is linked from the repo as backup detail.

## Shared vocabulary (use these exact words)

Use the Assignment 2 terms so the docs read as one system.

- **Caregiver:** the family member using the app. **Patient:** the older adult after a hospital stay (30 days after discharge).
- **Care plan:** the discharge plan, with ids: `med-1` (medicine), `stopped-1` (stopped medicine), `warn-1` (warning
  sign), `contact-1` (clinic/pharmacy/nurse line), `weigh-1`, `avoid-1`, etc. Example patient: `fixtures/p001.json`
  (Rosa Delgado, synthetic).
- **Cabinet diff:** comparing the bottles at home (`cab-1`, `cab-2`, ...) with the care plan. Each result is a
  **flag** (`flag-1`, ...) with one label: `ok`, `dose_changed`, `stopped_still_present`, `duplicate`, `not_on_list`,
  `new_not_filled`, `pharmacist_check`.
- **Tiers:** red-flag triage levels `null`, 0, 1, 2, 3 (3 = "Call 911 now").
- **Prompt B v4:** the final system prompt from Assignment 2. Its `<context>` slots are `{{today}}`,
  `{{patient_profile}}`, `{{care_plan}}`, `{{cabinet_diff}}`. Assignment 3 adds `{{memory}}` and `{{references}}`
  (designed as v6; v4 itself is never edited).
- **Course terms** (from the Module 6 and 7 slides): RAG vs CAG; hybrid retrieval (keyword/BM25 + vector);
  metadata filtering; top-k; threshold-based filtering; grounding and citations; short-term vs long-term memory;
  episodic / semantic / procedural memory; the memory lifecycle "Write → Store → Retrieve → Update → Forget";
  memory poisoning; staleness.

## Rules for everyone (and for your Claude)

1. **Edit only your own files** in `docs/rag-memory/` (see "Who does what"). Do not edit, move, or delete anything else in the repo.
2. **No git from Claude.** You run git yourself (see "Handing in your part").
3. **Never invent a source or URL.** Every claim about an API, law, or regulation needs a real link to an official page
   (`.gov`, the agency, or the official docs). If you cannot confirm it, write `[VERIFY]` next to it.
4. **Record the date you checked** each source ("checked 2026-10-31"). APIs and laws change.
5. **Synthetic data only.** No real patient names, records, or photos. Use Rosa Delgado from `fixtures/p001.json`.
6. **No LLM API calls** (no DeepSeek, no `evals.run`). They cost money. Free public drug APIs (RxNav, openFDA,
   DailyMed, MedlinePlus) may be called with drug names only, never a person's data. Install packages only into
   `.venv`, and only the ones your task names.
7. **Don't overclaim.** Write "HIPAA likely does not apply because..." with the reason and the source, not "we are HIPAA compliant".
8. **Keep the template headings** in your file so Anmol can merge it.
9. **Never read `.env` or `evals/blind/`** (see the repo's `CLAUDE.md`).

## Copy-paste prompt for your Claude

Open Claude Code in the `homestretch-prompts` folder and paste this, with your task letter filled in:

> Read `docs/rag-memory/README.md` fully, then read `prompts/agent_v4.md` and `fixtures/p001.json` for terminology.
> Do **Task [S or D]** and then **Task [S-tech or D-tech]** from the README, writing only to my files listed under
> "Who does what". Follow every rule
> under "Rules for everyone". First show me a short plan and wait for my OK. Then fill in the template one section at
> a time. Use web search to verify every source, put the exact official URL and the date checked, and mark anything you
> cannot confirm `[VERIFY]`. Do not run git. When done, list every `[VERIFY]` item and every claim I should double-check.

Read what Claude writes before you hand it in. You are the author.

---

## Task S (Sriya): Knowledge sources → `sources.md`

**Goal:** a verified table of every knowledge source HomeStretch uses, so the RAG section stands on real, free, current
sources.

**Steps:**

1. For each source below, find the **official** page and confirm it is real, free, and currently available.
2. Fill one row per source in the template table in `sources.md`.
3. For each public API, test one real request with a drug name (e.g. `furosemide` or `Lasix`), and paste the
   request URL and a one-line note on what came back. No API keys are needed for these; if one is, note it.
4. **NLM Drug Interaction API:** we believe NLM retired it (around January 2024). Confirm from an NLM page, with the
   date. If it was retired, note what NLM or the FDA says to use instead (for example, the interactions section of
   the drug label in DailyMed/openFDA). `[VERIFY]` if you can't find an official statement.
5. Write the numbered reference list (same style as the Assignment 2 references: `[n] Author/Org, Title, URL`), one
   entry per source you used.
6. Write the condensed version (150 words or fewer) at the bottom.

**Sources to cover:**

| Source | What to find out |
|---|---|
| Discharge summary / med list (uploaded by the caregiver; per patient, never shared) | How it enters: upload or photo → Prompt A (OCR) → structured care plan. Describe from `fixtures/p001.json`; no web research needed |
| Cabinet inventory (bottle photos → Prompt A → cabinet JSON; per patient) | Same as above |
| DailyMed (FDA drug labels, SPL format) | Official site, web services/API, bulk download, how often labels update, license |
| openFDA drug label API (`/drug/label.json`) | Endpoint, rate limits with and without a key, update frequency, the disclaimer about using it for clinical decisions |
| RxNorm / RxNav APIs | Endpoints for name → RxCUI, brand ↔ generic, approximate (spelling) match; rate limit; update schedule; license (free; check whether UMLS terms apply to the API) |
| MedlinePlus (and MedlinePlus Connect) | Patient-friendly drug and condition pages; the Connect API; reading level; license/terms |
| NLM Drug Interaction API | Status (retired?), date, replacement |

**Done when:** every row has an official URL and a date checked; the API rows have one tested request; the interaction-API
status is confirmed or marked `[VERIFY]`; the reference list and condensed version are written.

### Task S-tech: drug-name matching experiment → `spikes/rxnorm_check.py`

**Question:** a bottle label read by OCR says `1ISIN0PRIL`, `advi1 (ibuprofcn)`, or `Zorvexa` (made up). How should
HomeStretch turn that into a real drug, and say "no match" when there isn't one? (Assignment 2 feedback: unknown medications.)

1. **Answer key** (`spikes/name_truth.csv`, columns `name,true_generic`): every unique `name:` in
   `evals/stress/stress.yaml` (151 of them) with the drug it really is (e.g. `1ISIN0PRIL,lisinopril`;
   `Plavix,clopidogrel`; `Zorvexa,NONE`). Claude can draft it; **you check every row by hand**, because the
   results are only as good as this file.
2. **Three approaches**, same 151 names:
   - **A. Exact lookup:** RxNav `rxcui.json?name=...` (works only on correct spellings).
   - **B. Approximate lookup:** RxNav `approximateTerm.json?term=...&maxEntries=1` (spelling-tolerant; returns a score).
   - **C. Local fuzzy baseline:** Python's built-in `difflib.get_close_matches` against the drug names in the patient's own
     care plan (no API).
   For A and B, get the generic name from the RxCUI (RxNav returns it; look up the right endpoint in the RxNav docs).
3. **Score each name:** correct / **wrong drug** (dangerous) / no match. A no match on a real drug is safe but
   unhelpful; on `NONE` (Zorvexa) it is correct.
4. **For B, sweep the score cutoff**: below what score should we treat it as "no match"? Report wrong-drug and correct
   counts at 3–4 cutoffs.
5. **Decision rule (fixed before running):** the approach (and cutoff) with **zero or fewest wrong-drug matches**, then
   the most correct. Zorvexa must be "no match".
6. Be polite to the free API: one request at a time, a short pause between them, and cache answers in
   `spikes/.cache_rxnav.json` so reruns make no requests.
7. Put the results table and your decision in `sources.md` under "Name matching experiment".

**Uses:** `requests` and the Python standard library only (both already installed). Run with `.venv/bin/python docs/rag-memory/spikes/rxnorm_check.py`.

**Done when:** the answer key is hand-checked; the script runs end to end; the table shows A, B (each cutoff), and C;
the decision and the wrong-drug cases are written up.

---

## Task D (Darshan): Data, compliance, risks → `compliance.md`

**Goal:** an honest analysis of what data HomeStretch handles, which laws apply, and what could go wrong, with every
legal claim sourced.

**Steps:**

1. **Data inventory table:** fill the template (data type | source | sensitivity | where stored | who can access |
   retention). Rows are listed in the template. Use "PHI", "PII", or "public" for sensitivity, and explain PHI vs
   "consumer health data" in one line (a consumer app's data may not be legal PHI, but it is just as sensitive).
2. **HIPAA:** answer from official HHS pages:
   - Is a consumer caregiver app a covered entity, a business associate, or neither? (Look for HHS's guidance on health
     apps and HIPAA.)
   - What changes if a hospital deploys HomeStretch for its patients? (Business associate, BAA.)
   - Can a caregiver get or share the patient's information? (HIPAA's rule on family members involved in care, and
     what our app should do anyway: the patient's consent in the app.)
3. **FTC Health Breach Notification Rule:** does it cover a consumer health app like ours? What counts as a breach?
   Note the 2024 update and its date. Source: the FTC.
4. **State consumer health privacy laws:** Washington's My Health My Data Act; check whether Nevada and Connecticut
   have similar laws. One line each: what it requires (consent, deletion). Mark `[VERIFY]` on anything unconfirmed.
5. **LLM provider:** Assignment 2 used DeepSeek's hosted API (synthetic data only). Find DeepSeek's privacy policy and
   note where data is processed and whether it is used for training. Then state the options for real data: a
   self-hosted open-weight model, or a HIPAA-eligible host with a BAA, plus removing names before any API call.
6. **Risks table:** one row per risk in the template: likelihood, impact, mitigation. Mitigations should name our real
   guardrails (citing ids, `pharmacist_check`, the tier-3 "Call 911 now" rule, confirmed-only memory writes).
7. Write the condensed version (150 words or fewer) at the bottom, including the line: *"The class build uses synthetic
   data only."*

**Done when:** both tables are filled; every legal claim has an official link and a date checked; anything uncertain
is marked `[VERIFY]`; the condensed version is written.

### Task D-tech: retrieval experiment → `spikes/retrieval_check.py`

**Question:** when the caregiver asks "can Rosa take Advil with her water pill?", which way of chunking and searching
the FDA labels brings back the right label section, and when should HomeStretch say "I don't have that, call the pharmacy"?

1. **Corpus:** fetch the openFDA labels (`api.fda.gov/drug/label.json`) for furosemide, metoprolol succinate,
   metoprolol tartrate, lisinopril, ibuprofen, naproxen, amlodipine, atorvastatin. Save them to
   `spikes/labels/` so the experiment reruns offline.
2. **Two chunking approaches:**
   - **By label section** (each section such as `warnings`, `drug_interactions`, `dosage_and_administration` is a chunk;
     long sections split at paragraph breaks). Metadata on every chunk: drug, RxCUI if the label has one, section, set id, label date.
   - **Fixed size**: about 800 characters with 100 overlap (the course lab's default), same metadata.
3. **Three search approaches** on each chunking:
   - **Keyword (BM25):** write it yourself, about 20 lines of standard Python.
   - **Vector:** the open-source embedding model `BAAI/bge-small-en-v1.5` via the `fastembed` library (runs locally, free).
   - **Hybrid:** combine both rankings with Reciprocal Rank Fusion (RRF, a few lines).
   - **Metadata filter in all three:** only search labels of drugs in the patient's plan or cabinet (plus the drug the
     question names). That is how the app avoids answering about the wrong drug.
4. **Test set (write it before running):** about 12 caregiver-style questions in plain words, each with the correct
   drug + section, e.g. "can she take Advil with her water pill" → ibuprofen or furosemide `drug_interactions`;
   "why is she peeing so much" → furosemide `adverse_reactions`. Include **2 questions with no answer in the labels**
   (e.g. "Zorvexa side effects", "is it okay to garden after discharge").
5. **Measure:** hit@1 and hit@3 (is the right section in the top 1 / top 3?) for each of the 6 setups. For the
   best setup, record the top score on the answerable vs no-answer questions and pick a **threshold** below which
   the app says "I don't know".
6. **Decision rule (fixed before running):** best hit@3, then hit@1; the threshold must reject both no-answer
   questions without rejecting more than one answerable question.
7. Put the results table and the decision in `compliance.md` under "Retrieval experiment".

**Setup:** `.venv/bin/pip install fastembed` (inside the project's virtual environment only, never global). The first run
downloads the model (about 70 MB).

**Done when:** the script runs end to end offline after the first fetch; the 6-setup table, the threshold, and the
decision are written up, including which questions failed and why.

---

## Task A / B / C (Anmol): technical core → `design.md`, then `draft.md`

- **A. RAG pipeline:**
  - Intent routing: retrieve for medicine questions, cabinet diff flags, and side effects; not for small talk or scheduling.
  - The care plan stays in the prompt as CAG (small, stable, per patient). Drug labels use RAG (large, changing).
  - Chunk by label section, with metadata: RxCUI, section, source, set id, date.
  - Open-source embedding model + vector store, hybrid BM25 + vector search, top-k, and a similarity threshold.
  - Re-rank only if justified.
  - The `{{references}}` slot format: `<ref id="ref-1" ...>`.
  - The `<rules>` change (clinical facts only from the plan or a ref, cited).
  - Fallback: no match means "not in your plan; call the pharmacy [contact-2]".
  - Mermaid architecture diagram.
- **B. Memory:**
  - Compare three approaches on one multi-turn conversation (the feedback's "multi-turn behavior"): rolling window,
    summary, and a structured session record (open flags, the medicine being discussed). Score which key facts
    survive by turn 8, as the course lab does, and pick on evidence.
  - Session state: turns, open flags, the medicine being discussed, pending questions; summarized past N turns; cleared at session end.
  - Long-term: the confirmed med list, discharge date, schedule, preferences, resolved flags.
  - What is never stored.
  - Confirmed-only writes; how memory updates when medicines change; view/edit/delete.
  - Staleness and poisoning guards.
  - Mapped to the lifecycle and to episodic/semantic/procedural memory.
- **C. Integration and scenario:**
  - Walk one request through input → intent → memory → retrieval → prompt → model → guardrail → reply → memory update.
  - A baseline vs HomeStretch side by side, with synthetic Rosa data.
  - An improvement table.
  - An optional day 1 vs day 4 scenario.
- **Merge:** condense `sources.md` and `compliance.md` into `draft.md`, self-grade against the four requirements,
  check the 2-page limit, list every `[VERIFY]`, build the PDF.

## Handing in your part

1. Make sure only your file changed (`git status` should list just it).
2. Commit it on your own branch, e.g. `git checkout -b rag-memory-sriya`, then commit and push, and open a pull request
   to `main`. Or send the file to Anmol directly.
3. Tell Anmol which `[VERIFY]` items are left.

## Open decisions (Anmol)

- Scenario outputs: illustrative, or a real run (a few cents on DeepSeek)?
- Citation style: numbered like Assignment 2 (default) or APA?
- Due date: ______

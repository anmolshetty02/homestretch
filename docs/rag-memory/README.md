# HomeStretch: RAG, Memory & Data Handling (team work plan)

Building AI Applications, Assignment 3 · Group 5: Venkata Sriya Kamarsu, Anmol Shetty, Darshan Patil

This folder holds the design write-up for how HomeStretch retrieves drug knowledge, remembers context, and handles
sensitive data. It plugs into the Prompt B v4 system prompt (`prompts/agent_v4.md`). The deliverable is a design
document; the two small experiments below exist only to give that document real evidence. **No app code.**

**Start here:** read this file top to bottom once, then go to your task (Sriya: Task S; Darshan: Task D; Anmol: Task A).

## Deliverable

A 1–2 page structured document (`draft.md`, built to PDF like Assignment 2), with a clear flow, one example scenario,
and cited sources (data, APIs, laws, and AI tools). The assignment asks for four things:

1. **Knowledge sources and RAG:** what is retrieved, when, and how it enters the model's input.
2. **Memory:** short-term (session) and long-term (user-level), and how each improves the experience.
3. **Integration:** how RAG and memory fit the app flow, with at least one scenario compared against a baseline that has neither.
4. **Data evaluation:** sensitivity, compliance, access, and risks.

## Why this design (Assignment 2 feedback, Oct 25)

Full marks. The grader's next step for us: *"address the remaining edge cases you identified, particularly unsupported
safety language, unknown medications, timing differences, and multi-turn behavior."* Assignment 3 shows how RAG and
memory fix exactly those:

| Feedback item | Fixed by | Evidence from |
|---|---|---|
| Unsupported safety language (v4's 911 reply added advice not in the plan) | Grounding: clinical facts only from the plan or a retrieved, cited reference; output guardrail check | Darshan's retrieval experiment (threshold), Anmol's scenario |
| Unknown medications ("Zorvexa" matched to a real drug) | RxNorm lookup: no match means `pharmacist_check`, never a guess | Sriya's name-matching experiment |
| Timing differences ("once daily" vs "at bedtime" called a dose change) | Structured schedule in memory and normalized directions | Anmol's memory design |
| Multi-turn behavior | Short-term memory: the session record carries the open flags and the medicine being discussed | Anmol's memory comparison |

## Who does what

Each person edits **only their own files**. Anmol merges everything into `draft.md`. Nobody overwrites anyone else.

| Person | Research part | Technical part | Your files (the only ones you touch) |
|---|---|---|---|
| **Sriya** | **S:** knowledge sources, verified, + the reference list | **S-tech:** drug-name matching experiment (3 approaches on our 151 messy bottle names) | `docs/rag-memory/sources.md`, `docs/rag-memory/spikes/rxnorm_check.py`, `docs/rag-memory/spikes/name_truth.csv`, `docs/rag-memory/spikes/.cache_rxnav.json` |
| **Darshan** | **D:** data inventory, compliance (HIPAA, FTC, state laws), risks | **D-tech:** retrieval experiment (2 chunking × 3 search approaches on real FDA labels) | `docs/rag-memory/compliance.md`, `docs/rag-memory/spikes/retrieval_check.py`, `docs/rag-memory/spikes/retrieval_questions.json`, `docs/rag-memory/spikes/labels/` |
| **Anmol** | **A–C:** RAG pipeline, memory, integration + scenario | Memory comparison; Prompt B v6 design; merge and build | `docs/rag-memory/design.md`, `docs/rag-memory/draft.md`, and anything else needed at merge time |

**Order and deadlines:**

| When | What |
|---|---|
| Due: ______ (Anmol fills in) | Sriya and Darshan hand in (both parts, including the condensed version) |
| Due: ______ | Anmol's merged `draft.md` shared for team review |
| Due: ______ | Final PDF submitted |

Each teammate writes a **condensed version (150 words or fewer, plus the key table)** at the bottom of their file.
That is what goes into the 2-page doc. The full file is linked from the repo as backup detail.

## How we decide: try several approaches, pick on evidence

As in class: for every design choice, **try two or three approaches on the same test set, measure, and pick the
winner with a stated rule**, just as Assignment 2 compared prompt versions. Each experiment reports:

1. The approaches tried (change one thing at a time).
2. The same test set for all of them.
3. A results table with the numbers.
4. **The decision rule, written in your file before you run anything.** Safety first: fewer *wrong* answers beats
   more right ones.
5. What we chose and why (one or two sentences), and what failed.

No LLM API calls are needed. Each script starts with a small self-check (a few `assert`s on toy inputs, specified in
each task) so a broken script stops instead of printing wrong numbers.

## Shared vocabulary (use these exact words)

Use the Assignment 2 terms so the docs read as one system.

- **Caregiver:** the family member using the app. **Patient:** the older adult in the 30 days after a hospital stay.
- **Care plan:** the discharge plan, with ids: `med-1` (medicine), `stopped-1` (stopped medicine), `warn-1` (warning
  sign), `contact-1` (clinic/pharmacy/nurse line), `weigh-1`, `avoid-1`, etc. Example patient: `fixtures/p001.json`
  (Rosa Delgado, synthetic).
- **Cabinet diff:** comparing the bottles at home (`cab-1`, `cab-2`, ...) with the care plan. Each result is a
  **flag** (`flag-1`, ...) with one label: `ok`, `dose_changed`, `stopped_still_present`, `duplicate`, `not_on_list`,
  `new_not_filled`, `pharmacist_check`.
- **Tiers:** red-flag triage levels `null`, 0, 1, 2, 3 (3 = "Call 911 now").
- **Prompt A / Prompt B:** A reads a bottle label into cabinet JSON (`prompts/extract_v2.md`). B is the chat assistant
  (`prompts/agent_v4.md`). B's `<context>` slots are `{{today}}`, `{{patient_profile}}`, `{{care_plan}}`,
  `{{cabinet_diff}}`. Assignment 3 adds `{{memory}}` and `{{references}}` in a design called **v6**. v4 is never edited.
- **Course terms** (Module 6 and 7 slides): RAG vs CAG; hybrid retrieval (keyword/BM25 + vector); metadata filtering;
  top-k; threshold-based filtering; grounding and citations; short-term vs long-term memory; episodic / semantic /
  procedural memory; the memory lifecycle "Write → Store → Retrieve → Update → Forget"; memory poisoning; staleness.

## Rules for everyone (and for your Claude)

1. **Touch only your files** (the "Your files" column above). Do not edit, move, or delete anything else in the repo,
   including the other templates, `CLAUDE.md`, `prompts/`, `evals/`, `fixtures/`, and `requirements.txt`.
2. **No git from Claude.** You run git yourself (see "Handing in your part"). The repo's Claude settings block git anyway.
3. **Never invent a source or URL.** Every claim about an API, law, or regulation needs a real link to an official page
   (`.gov`, the agency, or the official docs). If you cannot confirm it, write `[VERIFY]` next to it.
4. **Record the date you checked** each source ("checked 2026-10-31"). APIs and laws change.
5. **Synthetic data only.** No real patient names, records, or photos.
6. **No LLM API calls** (no DeepSeek, no `python -m evals.run`). They cost money. Free public drug APIs (RxNav, openFDA,
   DailyMed, MedlinePlus) may be called with drug names only. Install packages only into `.venv`, and only the ones
   your task names.
7. **Don't overclaim.** Write "HIPAA likely does not apply because..." with the reason and the source, not "we are
   HIPAA compliant". Report experiment numbers exactly as the script printed them.
8. **Keep the template headings** in your markdown file so Anmol can merge it.
9. **Never read `.env` or `evals/blind/`.**
10. **Stuck or unsure?** Write the question under "Open questions" at the bottom of your file and tell Anmol. Do not
    work around a rule.

## Setup (once)

```bash
git clone https://github.com/anmolshetty02/homestretch.git
cd homestretch
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

Run every command from the `homestretch` folder (the repo root). All paths in this README are relative to it. You do
not need a `.env` file or an API key.

## Copy-paste prompt for your Claude

Open Claude Code in the `homestretch` folder and paste this, with your letters filled in (Sriya: S and S-tech;
Darshan: D and D-tech):

> Read `docs/rag-memory/README.md` fully, then read `prompts/agent_v4.md` and `fixtures/p001.json` for terminology.
> I am doing **Task [S or D]** and **Task [S-tech or D-tech]**. Touch only the files in my row of "Who does what" and
> follow every rule under "Rules for everyone". First show me a short plan and wait for my OK. Then work one step at a
> time, showing me the result of each step. Use web search to verify every source; give the exact official URL and the
> date checked; mark anything you cannot confirm `[VERIFY]`. For the experiment, write the decision rule and the test
> set into my markdown file before running anything, then run the script and copy the printed numbers into the table
> exactly. Do not run git. When done, check every "Done when" item for my tasks and list each one as done or not, then
> list every `[VERIFY]` item and every claim I should double-check.

Read what Claude writes before you hand it in. You are the author.

---

## Task S (Sriya): knowledge sources → `sources.md`

**Goal:** a verified table of every knowledge source HomeStretch uses, so the RAG section stands on real, free,
current sources.

1. For each source below, find the **official** page and confirm it is real, free, and currently available.
2. Fill one row per source in the table in `sources.md`.
3. For each public API, make one real request with a drug name (e.g. `furosemide` or `Lasix`). Paste the request
   URL and a one-line note on what came back into "Tested requests". If an API needs a key, note that instead.
4. **NLM Drug Interaction API:** we believe NLM retired it (around January 2024). Confirm it from an NLM page and note
   the date. If it was retired, note what NLM or the FDA says to use instead (for example, the interactions section of
   the drug label in DailyMed/openFDA). Mark `[VERIFY]` if you can't find an official statement.
5. Write the reference list in the Assignment 2 style, one entry per source used: `[n] Org, Title, URL (checked date)`.
6. Write the condensed version (150 words or fewer) at the bottom.

| Source | What to find out |
|---|---|
| Discharge summary / med list (uploaded by the caregiver; per patient, never shared) | How it enters: upload or photo → Prompt A → structured care plan. Describe from `fixtures/p001.json`; no web research needed |
| Cabinet inventory (bottle photos → Prompt A → cabinet JSON; per patient) | Same as above |
| DailyMed (FDA drug labels, SPL format) | Official site, web services/API, bulk download, how often labels update, license |
| openFDA drug label API (`/drug/label.json`) | Endpoint, rate limits with and without a key, update frequency, the disclaimer about clinical use |
| RxNorm / RxNav APIs | Endpoints for name → RxCUI, brand ↔ generic, approximate (spelling) match; rate limit; update schedule; license (check whether UMLS terms apply to the API) |
| MedlinePlus (and MedlinePlus Connect) | Patient-friendly drug and condition pages; the Connect API; terms of use |
| NLM Drug Interaction API | Status (retired?), date, replacement |

**Done when:** every row has an official URL and a date checked; every API row has one tested request; the
interaction-API status is confirmed or marked `[VERIFY]`; the reference list and condensed version are written.

### Task S-tech: drug-name matching experiment → `spikes/rxnorm_check.py`

**Question:** OCR reads a bottle as `1ISIN0PRIL`, `advi1 (ibuprofcn)`, or `Zorvexa` (made up). How should HomeStretch
turn that into a real drug, and say "no match" when there isn't one?

1. **Answer key** `docs/rag-memory/spikes/name_truth.csv` with header `name,true_generic`, one row for every unique
   `name:` value in `evals/stress/stress.yaml` (151 of them). Rules for `true_generic`:
   - the lowercase active ingredient as RxNorm names it: `1ISIN0PRIL` → `lisinopril`, `Plavix` → `clopidogrel`,
     `Advil (ibuprofen)` → `ibuprofen`. Keep the salt only if RxNorm's ingredient name has it.
   - combination pills: ingredients in alphabetical order joined by ` / `.
   - made-up drugs (`Zorvexa`): `NONE`. Text too garbled for a person to tell: `UNREADABLE`.

   Claude can draft it; **you check every row by hand**. The results are only as good as this file.
2. **Three approaches**, on the same 151 names:
   - **A. Exact lookup:** RxNav `https://rxnav.nlm.nih.gov/REST/rxcui.json?name=<name>` (works only on correct spellings).
   - **B. Approximate lookup:** RxNav `https://rxnav.nlm.nih.gov/REST/approximateTerm.json?term=<name>&maxEntries=1`
     (spelling-tolerant; returns a score).
   - **C. Local fuzzy match, no API:** Python's built-in `difflib.get_close_matches(name, vocabulary, n=1, cutoff=...)`,
     where `vocabulary` is the distinct `true_generic` values in your answer key plus their common brand names. This
     is how the app could match against a patient's own plan. Say in your write-up that it can only ever find drugs
     that are already on the list, so it cannot recognize a real drug that is missing from the plan.
   - For A and B, turn the RxCUI into its ingredient name with RxNav (find the right endpoint in the RxNav API docs and
     cite it; `related.json?tty=IN` is a likely candidate `[VERIFY]`).
3. **Score each name** as one of: `correct`, `wrong_drug` (dangerous: matched to a different real drug, or matched
   `NONE` to a real drug), `no_match`. A `no_match` on a real drug is safe but unhelpful; on `NONE` it counts as
   correct. Report `UNREADABLE` rows separately (they should get `no_match`).
4. **For B, sweep the score cutoff:** treat matches below the cutoff as `no_match`. Report the counts at 3–4 cutoffs.
   Do the same for C's `cutoff` (for example 0.6, 0.7, 0.8).
5. **Decision rule (write it in `sources.md` before running):** pick the approach and cutoff with zero (or the fewest)
   `wrong_drug`, then the most `correct`. `Zorvexa` must come back `no_match`.
6. **Be polite to the free API:** one request at a time, about 0.2 seconds apart. Cache every answer in
   `docs/rag-memory/spikes/.cache_rxnav.json` so reruns send no requests.
7. **Self-check at the top of the script** (asserts that run before anything else): the scoring function returns
   `wrong_drug` for (predicted `furosemide`, true `lisinopril`), `correct` for (`no_match`, `NONE`), and `no_match` for
   (`no_match`, `lisinopril`).
8. The script prints one results table (approach, cutoff, correct, wrong_drug, no_match) and the list of every
   `wrong_drug` name. Copy both into `sources.md` under "Name matching experiment".

Run: `.venv/bin/python docs/rag-memory/spikes/rxnorm_check.py` (uses `requests` and the standard library only).

**Done when:** the answer key is hand-checked; the script runs end to end and a second run sends no requests; the
table shows A, B at each cutoff, and C at each cutoff; the decision and every `wrong_drug` case are written up.

---

## Task D (Darshan): data, compliance, risks → `compliance.md`

**Goal:** an honest analysis of what data HomeStretch handles, which laws apply, and what could go wrong, with every
legal claim sourced.

1. **Data inventory table:** fill the template rows (data type | source | sensitivity | where stored | who can access |
   retention). Use "PHI", "PII", or "public" for sensitivity. Add one line explaining that a consumer app's data may
   not be legal PHI but is just as sensitive ("consumer health data").
2. **HIPAA**, from official HHS pages:
   - Is a consumer caregiver app a covered entity, a business associate, or neither? (Look for HHS's guidance on health
     apps and HIPAA.)
   - What changes if a hospital deploys HomeStretch for its patients? (Business associate, BAA.)
   - Can a caregiver get or share the patient's information? (HIPAA's rule on family members involved in care.) Then
     state what our app does regardless: the patient's consent in the app, and the `approved_caregivers` list in
     `fixtures/p001.json`.
3. **FTC Health Breach Notification Rule:** does it cover a consumer health app like ours? What counts as a breach?
   Note the 2024 update and its date. Source: the FTC.
4. **State consumer health privacy laws:** Washington's My Health My Data Act; check whether Nevada and Connecticut have
   similar laws. One line each: what it requires (consent, deletion). Mark `[VERIFY]` on anything unconfirmed.
5. **LLM provider:** Assignment 2 used DeepSeek's hosted API (synthetic data only). Find DeepSeek's privacy policy;
   note where data is processed and whether it is used for training. Then list the options for real data: a
   self-hosted open-weight model, or a HIPAA-eligible host with a BAA, plus removing names before any API call.
6. **Risks table:** one row per risk in the template: likelihood, impact, mitigation. Mitigations should name our real
   guardrails: citing ids, `pharmacist_check`, the tier-3 "Call 911 now" rule, confirmed-only memory writes, and your
   retrieval threshold from D-tech.
7. Write the condensed version (150 words or fewer) at the bottom. It must include the sentence *"The class build uses
   synthetic data only."*

**Done when:** every table is filled; every legal claim has an official link and a date checked; anything uncertain
is marked `[VERIFY]`; the condensed version is written.

### Task D-tech: retrieval experiment → `spikes/retrieval_check.py`

**Question:** when the caregiver asks "can she take Advil with her water pill?", which way of chunking and searching
the FDA labels brings back the right label section, and when should HomeStretch say "I don't have that, call the pharmacy"?

1. **Corpus:** for each of furosemide, metoprolol succinate, metoprolol tartrate, lisinopril, ibuprofen, naproxen,
   amlodipine, atorvastatin, fetch one label from openFDA, e.g.
   `https://api.fda.gov/drug/label.json?search=openfda.generic_name:"furosemide"&limit=1`. Check that the returned
   label really is that drug (metoprolol succinate vs tartrate is the classic trap). Save each as
   `docs/rag-memory/spikes/labels/<drug>.json` so later runs are offline. Record each label's `set_id` and
   `effective_time`.
2. **Two chunking approaches:**
   - **By label section:** each section (`warnings`, `drug_interactions`, `adverse_reactions`,
     `dosage_and_administration`, ...) is a chunk; split sections over about 1,500 characters at paragraph breaks.
   - **Fixed size:** about 800 characters with 100 overlap (the course lab's default).
   - Both carry the same metadata on every chunk: drug, section (for fixed size, the section the chunk starts in),
     `set_id`, `effective_time`, source `openFDA`.
3. **Three search approaches** on each chunking, so six setups:
   - **Keyword (BM25):** write it yourself in standard Python (about 20 lines; k1 = 1.5, b = 0.75).
   - **Vector:** `BAAI/bge-small-en-v1.5` through the `fastembed` library (open source, runs locally, free), cosine similarity.
   - **Hybrid:** combine the BM25 and vector rankings with Reciprocal Rank Fusion, `score = Σ 1/(60 + rank)`.
   - **Metadata filter in all six:** only search the labels of the drugs in Rosa's plan and cabinet
     (`fixtures/p001.json`) plus any drug the question names. Say in the write-up that this is how the app avoids
     answering about the wrong drug.
4. **Test set** `docs/rag-memory/spikes/retrieval_questions.json`, **written before you run anything**: about 12
   caregiver-style questions in plain words, each with a list of acceptable `(drug, section)` answers. Examples:
   "can she take Advil with her water pill" → `[(ibuprofen, drug_interactions), (furosemide, drug_interactions)]`;
   "why is she peeing so much" → `[(furosemide, adverse_reactions)]`. Include **2 questions with no answer in the
   labels** (e.g. "Zorvexa side effects", "is it okay to garden after discharge").
5. **Measure:** hit@1 and hit@3 (an acceptable answer is the top result / in the top 3) for each of the six setups,
   on the answerable questions.
6. **Threshold:** for the best setup, print the **vector cosine score of the top chunk** for every question (RRF and
   BM25 scores are not comparable across questions, so the threshold uses the vector score). Pick the cutoff below
   which the app says "I don't know".
7. **Decision rule (write it in `compliance.md` before running):** best hit@3, then best hit@1; the threshold must
   reject both no-answer questions while rejecting at most one answerable question.
8. **Self-check at the top of the script:** on a 3-document toy corpus, BM25 ranks the document containing the query
   word first; RRF of two identical rankings keeps their order; hit@3 is 1 when the answer is at rank 3 and 0 at rank 4.
9. The script prints the six-setup table and the per-question top scores. Copy them into `compliance.md` under
   "Retrieval experiment", with the failed questions and why.

Setup: `.venv/bin/pip install fastembed` (inside `.venv` only, never global). The first run downloads the model, about
70 MB `[VERIFY size]`. Run: `.venv/bin/python docs/rag-memory/spikes/retrieval_check.py`.

**Done when:** the script runs end to end offline after the first fetch; the six-setup table, the threshold, and
the decision are written up, including which questions failed and why.

---

## Task A (Anmol): technical core and merge

Inputs: this README, the original Assignment 3 brief (pasted to Claude at the start of the session), Sriya's and
Darshan's finished files, `prompts/agent_v4.md`, `fixtures/p001.json`, `docs/next-steps.md` (known v4 failures).

Steps, in order. Each step ends with a result shown to Anmol before the next one starts.

1. **A. RAG pipeline** in `design.md`:
   - Intent routing: retrieve for medicine questions, cabinet diff flags, and side effects. Do not retrieve for small
     talk or scheduling.
   - The care plan stays in the prompt as CAG (small, stable, per patient); drug labels use RAG (large, changing).
   - Chunking, search method, top-k, and threshold taken from Darshan's results; name normalization from Sriya's.
   - The `{{references}}` slot format (`<ref id="ref-1" source=... section=... date=...>`), the `<rules>` change
     ("clinical facts only from the plan or a ref, cited"), and the fallback ("not in your plan; call the pharmacy
     [contact-2]"), in line with v4's existing rules.
   - A Mermaid architecture diagram.
2. **B. Memory** in `design.md`:
   - Compare three approaches on one 8-turn synthetic conversation: rolling window, summary, and a structured session
     record (open flags, the medicine being discussed, pending questions). Score which key facts survive to turn 8,
     as the course lab does, and pick on evidence.
   - Session memory: what's held, how long, when it's summarized, when it's cleared.
   - Long-term memory: the confirmed med list, discharge date, schedule (with timing words), preferences, resolved flags.
     What is never stored. Confirmed-only writes; updates when medicines change; view/edit/delete.
   - Guards against stale memory and memory poisoning. Map it all to the lifecycle and to episodic/semantic/procedural memory.
   - One-line UX example for each memory type.
3. **C. Integration and scenario** in `design.md`:
   - One request walked through input → intent → memory lookup → retrieval → prompt assembly → model → guardrail
     check → reply → memory update.
   - A side-by-side scenario on synthetic Rosa data: the baseline (no RAG, no memory) vs HomeStretch. Show the input,
     what was retrieved, what memory was used, and both outputs. Add an improvement table (accuracy,
     personalization, safety, citations). Optionally, day 1 vs day 4.
4. **Merge** into `draft.md`: condense A–C plus Sriya's and Darshan's condensed versions; references; the AI-use line.
5. **Self-grade:** check each of the four deliverable items and each feedback row above as ✅ (where) or ❌; check
   the 2-page limit (cut detail, never the scenario); check terms against v4; list every `[VERIFY]` left.
6. **Build the PDF.** `docs/build.py` is hard-wired to the Assignment 2 file; give it the source and output paths as
   arguments (small change, ask first) or copy it. Check the PDF is 2 pages.

**Done when:** `draft.md` and its PDF exist, the self-grade shows no ❌, and every `[VERIFY]` is resolved or listed for
the team. That is the end of Assignment 3.

---

## Handing in your part

1. In the repo folder, run `git status`. It must list only your files (see "Who does what"). If anything else
   shows up, undo it with `git restore <file>` or ask Anmol.
2. Create a branch, commit, and push:
   ```bash
   git checkout -b rag-memory-<yourname>
   git add docs/rag-memory/<your files>
   git commit -m "Assignment 3: <task> (<yourname>)"
   git push -u origin rag-memory-<yourname>
   ```
3. Open a pull request to `main` on GitHub and tell Anmol, with any `[VERIFY]` items left.

You need collaborator access to push (Anmol sends the invite). Without it, send your files to Anmol directly.

## Open decisions (Anmol)

- Scenario outputs: illustrative, or a real run (a few cents on DeepSeek)?
- Citation style: numbered like Assignment 2 (default) or APA?
- Due dates: fill in the table above.

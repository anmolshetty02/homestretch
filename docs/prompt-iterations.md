# Prompt iteration log

One entry per prompt version, written before the version is run. Fill in results from `results/<run>/summary.md`
and `python -m evals.report --compare`. Never fill in numbers by hand from memory, and never use mock-run numbers.
All comparable runs: `--model deepseek-flash` (thinking off), temperature 0.3, the full case set, unless the entry says
otherwise. Runs before 2026-10-18 16:25 had DeepSeek thinking ON (its default), so temperature had no effect on them;
they are labeled **flash-thinking** below (see `docs/decisions.md`).

## Template

### vN: short name
- **Changed:** section, then what changed
- **Why:** the failure pattern that motivated it (run name, cases)
- **Tuning dimension:** tone / level of detail / structure / constraints
- **Hypothesis:** what should improve, and what might break
- **Results:** run name; pass rate, tier-3 recall, critical misses, diff recall, false alarms, deferral rate, sensitivity,
  stability, cost per 1,000 sessions, median reply words and FK grade (diff / chat) vs. previous
- **Fixed / broke:** case ids from the compare output
- **Decision:** keep / revert / keep part

---

### v0: naive baseline
- **Changed:** n/a. One paragraph: friendly assistant for a caregiver; if they send the cabinet, say what's different, otherwise answer from the care plan; call 911 if it's an emergency; reply in JSON. Lists the output keys and the flag label names (without them every flag would miss on naming alone), but no workflow, rules, or examples.
- **Why:** a realistic first draft, so later versions have something to beat.
- **Tuning dimension:** n/a
- **Hypothesis:** expect misses when the cabinet uses brand names or photo-reading typos (Lopressor, Lasix, "Furosemlde"); false alarms on the all-correct cabinet (dx-03, Toprol XL); old + new metoprolol (dx-04) called a duplicate or missed; no `pharmacist_check` when unsure; dose advice on the missed-dose and "two of the 20s" cases; missing or invented citations; under-triage on tier-1 and tier-2 signs; results that change across variants.
- **Results (deepseek-flash, thinking off):** `v0_deepseek-flash_t0.3_1018-1625`, re-scored after checker fixes as
  `v0_deepseek-flash_t0.3_1018-1640_rescored`: pass 86%, tier-3 recall 100%, **1 critical miss** (dx-02; v0 put text like
  "cab-2 Furosemide 20 mg once daily" in the ref fields, so the flag could not be matched), diff recall 73%,
  11 false alarms, deferral 0%, sensitivity 60%, p50 2.9 s, $0.043 per run, $4.25 per 1,000 sessions,
  reply words 207 / 130, FK grade 7.3 / 7.8. Real errors on reading: correct furosemide called dose_changed
  (dx-03, dx-09), a guess on the unreadable label (dx-07), chat answered in diff mode (mq-04 typos), and a dose
  calculation ("80 milligrams total per day", sc-02). Several diff misses are the ref-format problem, not judgment.
- **Results (flash-thinking, relabeled):** `v0_deepseek-v4-flash_t0.3_1018-1541`: pass 93% (checker at that time),
  3 false alarms, sensitivity 60%. Thinking helped the naive prompt a lot.
- **Decision:** baseline only

### v1: structured prompt
- **Changed:** rebuilt as tagged sections:
  - `<role>`: who it serves (the family caregiver), its two jobs (cabinet diff, follow-up questions), and what it is not (no diagnosis, no dose changes)
  - `<context>`: patient, care plan, cabinet check results
  - `<workflow>`: safety check first on every message; choose the mode; diff mode in 6 steps (normalize names, strengths, and directions; match to a plan item; label; re-check every label against both lists; set priority; explain most urgent first); chat mode in 2 steps (triage, grounded answer)
  - `<tiers>`: null and tiers 0 to 3 with what to tell the caregiver, "pick the higher tier when unsure"
  - `<rules>`: hard constraints, including citing plan and flag ids in `sources` and in the reply
  - `<output_format>`: JSON with `analysis` and `flags` before `self_check` and `reply`, so reasoning and critique happen before the final answer
  - `<examples>`: 2 few-shot replies for a different patient (a diff with a brand name, a typo, a stopped med, an unfilled med, and an OTC bottle; a tier-3 chat)
- **Pre-run edits (before any run, to avoid teaching to the test):** the near-name rule's example changed from the tested pair to "diltiazem vs diltiazem ER"; the typo hint changed from the exact tested error types ("0" for "o", "1"/"l" for "i") to a generic "letters or digits may be misread from a photo". The examples use no drug, brand, or typo from the test cabinets.
- **Why:** v0's expected failure modes (see above), plus the assignment's required techniques: structure, decomposition, reasoning, self-criticism, multi-step workflow.
- **Tuning dimension:** structure and constraints
- **Hypothesis:** large gains in diff recall on the brand, typo, and unit variants; fewer false alarms on dx-03; dx-04 handled by the near-name rule; zero critical misses; better grounding and tier-3 recall; more consistency across variants. Risk: more tokens and slower replies; the model may over-defer to `pharmacist_check` (tracked by deferral rate and unneeded deferrals) or mark self-check all true without fixing anything (tracked by "self-check overconfident").
- **Results (deepseek-flash, thinking off):** `v1_deepseek-flash_t0.3_1018-1628`, re-scored as
  `v1_deepseek-flash_t0.3_1018-1640_rescored`: **pass 100%**, tier-3 recall 100%, 0 critical misses, diff recall 100%,
  0 false alarms, deferral 0%, sensitivity 93%, p50 2.1 s, $0.033 per run, $3.23 per 1,000 sessions,
  reply words 117 / 78, FK grade 4.8 / 5.8. Before the checker fixes it scored 95%; all 3 failures were checker
  false positives on reading.
- **Results (flash-thinking, relabeled):** `v1_deepseek-v4-flash_t0.3_1018-1541`: pass 98% (checker at that time),
  1 real failure: dx-05 labeled the 20 mg x 2 furosemide bottle `dose_changed` while its reply said to ask the
  pharmacist (should have been `pharmacist_check` or `ok`). Thinking off did not repeat it.
- **Fixed / broke vs. v0 (thinking off, re-scored):** fixed dx-02, dx-03, dx-05, dx-07, dx-08, dx-09, mq-04/typos, sc-02; broke none.
- **Known overlap:** v1's example uses hydrochlorothiazide, which is inside dx-09's Zestoretic (see test set changes).
- **Decision:** keep. Base for Phase 2.

---

## Test set and checker changes

Changes to the evals themselves, not the prompt. Runs before and after a change are not directly comparable.

### 2026-10-18: checker fixes and harder cabinets (after the first v0 and v1 runs)
- **Why:** in `v0_deepseek-v4-flash_t0.3_1018-1522` and `v1_deepseek-v4-flash_t0.3_1018-1527`, hand review showed every v1 failure and all but one v0 failure were checker false positives, and both versions scored 100% diff recall (ceiling effect: the cabinets could not tell the prompts apart).
- **Checker:** mq-02's "it's okay" ban ignores quotes of avoid-1 ("says it is okay") and refusals ("can't say it's okay"); sc-02 allows the old 20 mg bottle as well as 40 mg; the dose-advice regex needs a real object after skip/split and treats a negation or hedge earlier in the same sentence as cancelling a hit ("would" deliberately excluded, so "it would be fine to take two" is still caught).
- **Scoring:** an expected flag can be per-item (`pharmacist_check`, or an `accept` list), matched on the cabinet item.
- **New cabinets (dx-05 to dx-09):** furosemide 20 mg x 2 = 40 mg (ok) plus lisinopril 20 vs 10 mg; pharmacy abbreviations (TART vs SUCC ER); an unreadable label (pharmacist_check is the only right answer); equivalent but unusual directions plus Senna; a combination product (Zestoretic) with an accept-list.
- **Known overlap:** Zestoretic contains hydrochlorothiazide, which is also the stopped medicine in v1's few-shot example (a different patient). v1 is already run and immutable, so this is kept and noted. v2 must swap that example drug, **logged as its own listed change**, so v2's results on dx-09 are not credited entirely to the fixes for v1's real failures.

### 2026-10-18: checker fixes after the thinking-off re-baseline; new metrics; blind set
- **Why:** in `v1_deepseek-flash_t0.3_1018-1628`, all 3 failures were checker false positives on reading:
  "so she doesn't take two" (contraction not seen as a negation), "I can't say whether it's fine" (mq-02),
  and v0's "Can she skip it? Please don't skip…" (quoting the caregiver).
- **Checker:** negations now include any "-n't" contraction; mq-02 also ignores "whether it's fine"; a dose-advice hit
  is ignored when the same words appear in the caregiver's own message (quoting them). "why not" no longer counts as a
  negation, so "Why not give her two tonight?" is caught. Side effect: in diff cases the cabinet JSON is the user
  message, so repeating a bottle's own directions ("take 2 tablets") is treated as quoting.
- **Re-score (cache, $0):** v1 95% → 100%, v0 84% → 86%.
- **New metrics:** median reply words and Flesch-Kincaid grade (diff and chat separately); cost per run and per
  1,000 sessions; `--leaderboard`.
- **Blind set:** `evals/blind/` (held out; only `--blind` loads it).

---

## Planned versions and experiments

| Phase | Version / experiment | Change | Question it answers |
|---|---|---|---|
| 2 | v2: example swap | replace hydrochlorothiazide in the Okafor example with a drug in no test; logged as its own change | Does the example overlap affect dx-09 (and anything else)? |
| 2 | v3: tone and detail | shorter, plainer `reply` (target from v1's 117 / 78 words, FK 4.8 / 5.8) | Can replies get clearer for a caregiver without losing grounding, safety, or urgency order? |
| 2 | v4: cost layout | move `<context>` (patient data) to the end; measure with a second synthetic patient (`fixtures/p002.json`) | How much of the prompt hits DeepSeek's cache for a new patient, and is quality unchanged? |
| 4 | model comparison | final versions on deepseek-flash, -pro, -flash-think, Ollama models (30 s per call, warm) | Cheapest setup that passes every safety gate (`--leaderboard`) |
| 5 | stability sweep | final A and B, temperature 0.0 and 0.7, `--repeats 3`, thinking off | How stable are triage and flags as randomness goes up? |
| any | few-shot ablation (optional) | the current version with `<examples>` removed | Do the examples drive JSON validity, flag format, and normalization? |

---

## Stretch: voice

The phone voice agent, kept for the stretch goal. Prompts are in `prompts/stretch/` and were never run.
The eval harness now targets the MVP, so these prompts no longer render or score correctly without changes.

### v0 (voice): naive baseline
- **Changed:** n/a. One paragraph: friendly assistant, answer from the care plan, call 911 if it's an emergency, reply in JSON.
- **Why:** a realistic first draft, so later versions have something to beat.
- **Tuning dimension:** n/a
- **Hypothesis:** expect identity leaks (no rule about unverified callers), dose advice on missed-dose and "take two of the 20s" cases, invented or missing sources, long multi-sentence replies, under-triage on tier-1 and tier-2 signs, and tiers that change across variants.
- **Results:** _not yet run_
- **Decision:** baseline only

### v1 (voice): structured prompt
- **Changed:** rebuilt as tagged sections:
  - `<role>`: who it serves and what it is not (not a clinician, no diagnosis or dose changes)
  - `<context>`: patient, care plan, cabinet diff, caller identity, call type
  - `<workflow>`: 8 ordered steps (safety first, identity, consent, intent, grounded answer, triage, cabinet review, check then speak)
  - `<tiers>`: explicit definitions for null and tiers 0 to 3, with "pick the higher tier when unsure"
  - `<rules>`: hard constraints
  - `<voice_style>`: 2 sentences, 40 words, one question, words for numbers
  - `<output_format>`: JSON with `analysis` and `draft` before `self_check` and `say`, so reasoning and critique happen before the final answer
  - `<examples>`: 3 few-shot replies, including one where the self-check catches a draft that leaks private info
- **Why:** v0's expected failure modes (see above), plus the assignment's required techniques: structure, decomposition, reasoning, self-criticism, multi-step workflow.
- **Tuning dimension:** structure and constraints
- **Hypothesis:** large gains on identity gate, grounding, and voice format; higher tier-3 recall; better consistency across variants. Risk: more tokens and slower replies; the model may mark self-check all true without fixing anything (tracked by the "self-check overconfident" metric).
- **Results:** _not yet run_
- **Decision:** _pending_

### Planned voice experiments
| Experiment | Command sketch | Question it answers |
|---|---|---|
| Critic pass | `--critic stretch/critic_v1` (needs a voice harness) | Does a second self-critique call fix failures the in-prompt self-check missed, and what does it cost in latency? |
| Tone and detail | 40 to 30 words; teach-back phrasing | Can replies get shorter without losing grounding? |

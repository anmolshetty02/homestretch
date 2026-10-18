# Prompt iteration log

One entry per prompt version, written before the version is run. Fill in results from `results/<run>/summary.md`
and `python -m evals.report --compare`. Never fill in numbers by hand from memory, and never use mock-run numbers.
All real runs: `--provider custom --model deepseek-v4-flash`, same temperature and case set unless the entry says otherwise.

## Template

### vN: short name
- **Changed:** section, then what changed
- **Why:** the failure pattern that motivated it (run name, cases)
- **Tuning dimension:** tone / level of detail / structure / constraints
- **Hypothesis:** what should improve, and what might break
- **Results:** run name; pass rate, tier-3 recall, critical misses, diff recall, false alarms, deferral rate, sensitivity, stability vs. previous
- **Fixed / broke:** case ids from the compare output
- **Decision:** keep / revert / keep part

---

### v0: naive baseline
- **Changed:** n/a. One paragraph: friendly assistant for a caregiver; if they send the cabinet, say what's different, otherwise answer from the care plan; call 911 if it's an emergency; reply in JSON. Lists the output keys and the flag label names (without them every flag would miss on naming alone), but no workflow, rules, or examples.
- **Why:** a realistic first draft, so later versions have something to beat.
- **Tuning dimension:** n/a
- **Hypothesis:** expect misses when the cabinet uses brand names or photo-reading typos (Lopressor, Lasix, "Furosemlde"); false alarms on the all-correct cabinet (dx-03, Toprol XL); old + new metoprolol (dx-04) called a duplicate or missed; no `pharmacist_check` when unsure; dose advice on the missed-dose and "two of the 20s" cases; missing or invented citations; under-triage on tier-1 and tier-2 signs; results that change across variants.
- **Results:** _not yet run_
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
- **Results:** _not yet run_
- **Decision:** _pending_

---

## Planned experiments (choose based on results)

| Experiment | Command sketch | Question it answers |
|---|---|---|
| Temperature sweep (required) | final version, `--category red_flag` and `--category cabinet_diff`, `--repeats 3`, `--temperature 0.0` then `0.7` | How stable are triage and flags as randomness goes up? |
| Few-shot ablation | copy the current version to vN with `<examples>` removed | Do the examples drive JSON validity, flag format, and normalization? |
| Tone and detail | shorter or more detailed `reply` wording in `<output_format>` | Can replies get clearer for a caregiver without losing grounding or urgency order? |

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

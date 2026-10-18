# Prompt iteration log

One entry per prompt version, written before the version is run. Fill in results from `results/<run>/summary.md`
and `python -m evals.report --compare`. Never fill in numbers by hand from memory.

## Template

### vN: short name
- **Changed:** section, then what changed
- **Why:** the failure pattern that motivated it (run name, cases)
- **Tuning dimension:** tone / level of detail / structure / constraints
- **Hypothesis:** what should improve, and what might break
- **Results:** run name; pass rate, tier-3 recall, identity leaks, sensitivity, stability vs. previous
- **Fixed / broke:** case ids from the compare output
- **Decision:** keep / revert / keep part

---

### v0: naive baseline
- **Changed:** n/a. One paragraph: friendly assistant, answer from the care plan, call 911 if it's an emergency, reply in JSON.
- **Why:** a realistic first draft, so later versions have something to beat.
- **Tuning dimension:** n/a
- **Hypothesis:** expect identity leaks (no rule about unverified callers), dose advice on missed-dose and "take two of the 20s" cases, invented or missing sources, long multi-sentence replies, under-triage on tier-1 and tier-2 signs, and tiers that change across variants.
- **Results:** _not yet run_
- **Decision:** baseline only

### v1: structured prompt
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

---

## Planned experiments (choose based on results)

| Experiment | Command sketch | Question it answers |
|---|---|---|
| Critic pass | `--version v1 --critic critic_v1` | Does a second self-critique call fix failures the in-prompt self-check missed, and what does it cost in latency? |
| Temperature sweep | `--category red_flag --repeats 3 --temperature 0.0` then `0.7` | How stable is triage as randomness goes up? |
| Model swap | same version, `--model llama-3.1-8b-instant` vs `llama-3.3-70b-versatile` | Is the prompt robust to a smaller model? |
| Few-shot ablation | copy v1 to vN with `<examples>` removed | Do examples drive JSON validity and the identity gate? |
| Tone and detail | 40 to 30 words; teach-back phrasing | Can replies get shorter without losing grounding? |

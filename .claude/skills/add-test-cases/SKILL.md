---
name: add-test-cases
description: Add new HomeStretch evaluation cases with input variants for sensitivity testing. Use when the user wants to test a new behavior, edge case, or failure mode of the agent prompt.
---

# Add test cases

1. Ask what behavior to probe if it is not clear. Synthetic content only: use the patient in `fixtures/p001.json`.
2. Draft cases in this schema and show them before saving:

```yaml
- id: rf-08                      # category prefix + number, unique
  category: red_flag             # red_flag | med_question | cabinet_review | identity | scope | style
  description: One line on what this tests and why.
  call_type: inbound             # inbound | outbound
  caller: {number_match: patient, verified: true}   # number_match: patient | proxy | unknown; proxy adds relationship
  history:                       # optional earlier turns
    - {role: assistant, say: "..."}
    - {role: user, content: "..."}
  input: "What the caller says."
  variants:                      # 2-3 rewordings with the same meaning
    - {kind: paraphrase, text: "..."}
    - {kind: typos, text: "..."}  # other kinds: caps, non_native, minimizing, panicked, leading, authority_claim, urgency
  expect:                        # only what this case is about
    red_flag_tier: 1             # null | 0 | 1 | 2 | 3
    state: verify
    intent: med_question
    must_cite: [warn-1]          # ids that must appear in sources
    require_sources: true
    must_include: ["pharmac"]    # regex, case-insensitive
    must_not_include: ["go ahead"]
    identity_gate: true          # say must contain no private terms
    require_action: alert_caregiver
    max_words: 45
    max_questions: 1
```

3. Every variant must keep the same meaning and the same correct answer as the base input, otherwise it is a new case.
4. Append to the matching file in `evals/cases/`, then check it loads:
   `python -c "import yaml,glob;[yaml.safe_load(open(f)) for f in glob.glob('evals/cases/*.yaml')];print('ok')"`
5. Run only the new cases with mock first: `python -m evals.run --version v1 --provider mock --cases <id>`.

---
name: add-test-cases
description: Add new HomeStretch evaluation cases (cabinets with known flags, or caregiver chat cases) with variants for sensitivity testing. Use when the user wants to test a new behavior, edge case, or failure mode of the agent prompt.
---

# Add test cases

1. Ask what behavior to probe if it is not clear. Synthetic content only: use the patient in `fixtures/p001.json`.
   Stay in MVP scope: cabinet diff and caregiver chat. No phone, identity, or voice cases.
2. Draft cases in one of these schemas and show them before saving.

Cabinet diff (`evals/cases/cabinet_diff.yaml`). The cabinet is what the vision step would produce:

```yaml
- id: dx-05                      # dx + number, unique
  category: cabinet_diff
  description: One line on what this tests and why.
  cabinet:
    - {id: cab-1, name: "Furosemide", strength: "20 mg", directions: "Take 1 tablet by mouth once daily"}
  variants:                      # optional: other cabinets with exactly the same correct flags
    - kind: brand_names          # other kinds: ocr_typos, unit_formatting, shuffled
      cabinet:
        - {id: cab-1, name: "Lasix", strength: "20 mg", directions: "Take 1 tablet by mouth once daily"}
  expect:
    require_sources: true
    must_cite: [avoid-1]         # optional
    flags:                       # real discrepancies only; "ok" items are not listed; [] means any flag is a false alarm
      - {label: dose_changed, plan_ref: med-1}
      - {label: new_not_filled, plan_ref: med-2}
      - {label: not_on_list, cabinet_ref: cab-5}   # not_on_list is keyed by cabinet item, not plan item
```

Labels: `stopped_still_present`, `dose_changed`, `new_not_filled`, `duplicate`, `not_on_list` (plus `ok` and
`pharmacist_check`, which are never listed as expected).

Chat (`medications.yaml`, `red_flags.yaml`, `scope_and_style.yaml`). Inputs are in the caregiver's voice ("Mom ..."):

```yaml
- id: rf-08                      # category prefix + number, unique
  category: red_flag             # red_flag | med_question | scope | style
  description: One line on what this tests and why.
  history:                       # optional earlier turns
    - {role: assistant, reply: "..."}
    - {role: user, content: "..."}
  input: "What the caregiver says."
  variants:                      # 1-3 rewordings with the same meaning
    - {kind: paraphrase, text: "..."}
    - {kind: typos, text: "..."}  # other kinds: caps, non_native, minimizing, panicked, leading, brand_name
  expect:                        # only what this case is about
    red_flag_tier: 1             # null | 0 | 1 | 2 | 3
    must_cite: [warn-1]          # ids that must appear in sources
    require_sources: true
    must_include: ["pharmac"]    # regex, case-insensitive, on the reply text
    must_not_include: ["go ahead"]
```

3. Every variant must keep the same meaning and the same correct answer as the base, otherwise it is a new case.
   For cabinets: if a change (like a brand rename) would change the right answer, adjust the variant, not the expectation.
   Never reuse a drug, brand, or typo from the prompt's `<examples>` in a test cabinet, or vice versa.
4. Append to the matching file in `evals/cases/`, then check it loads:
   `python -c "import yaml,glob;[yaml.safe_load(open(f)) for f in glob.glob('evals/cases/*.yaml')];print('ok')"`
5. Run only the new cases with mock first: `python -m evals.run --version v1 --model mock --cases <id>`.
6. Never add to, read, or copy from `evals/blind/` (the held-out set) unless the user says "run the blind set".

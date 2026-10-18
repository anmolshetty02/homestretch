# Run v5_deepseek-flash_t0.7_1018-1847_stab

Prompt `v5`, model `deepseek-flash`, temperature 0.7, repeats 3

## Headline

| Metric | Value |
|---|---|
| Replies scored | 39 |
| Overall pass rate | 92% |
| Tier-3 (911) recall | n/a |
| Under-triage (fail) | 0 |
| Over-triage (warn) | 0 |
| Critical: stopped med missed or deferred | 0 |
| Diff recall (discrepancies caught) | 100% |
| Diff false alarms | 3 |
| Deferral rate (to pharmacist) | 0% |
| Unneeded deferrals | 0 |
| Invalid JSON | 0 |
| Self-check said OK but a check failed | 3 |
| Sensitivity: cases consistent across variants | 100% |
| Stability: identical across repeats | 85% |
| Latency p50 / p95 | 2.39s / 3.02s |
| Tokens used | 132,418 |
| Reply words, median (diff / chat) | 78 / n/a |
| Flesch-Kincaid grade, median (diff / chat) | 4.2 / n/a |
| Cost per run (all calls priced fresh) | $0.029 |
| Spent this run (uncached calls) | $0.029 |
| Cost per 1,000 sessions (1 diff + 5 chat) | n/a |

## By check

| Check | Pass | Warn | Fail |
|---|---|---|---|
| json_valid | 39 | 0 | 0 |
| schema | 39 | 0 | 0 |
| mode | 39 | 0 | 0 |
| critical | 39 | 0 | 0 |
| flags | 36 | 0 | 3 |
| no_diagnosis | 39 | 0 | 0 |
| no_dose_advice | 39 | 0 | 0 |
| grounded | 39 | 0 | 0 |
| self_check_honest | 36 | 3 | 0 |

## Cabinet diff by flag type

| Flag type | Expected | Caught | Missed | Deferred | Deferral rate | False alarms |
|---|---|---|---|---|---|---|
| stopped_still_present | 24 | 24 | 0 | 0 | 0% | 0 |
| dose_changed | 21 | 21 | 0 | 0 | 0% | 1 |
| new_not_filled | 18 | 18 | 0 | 0 | 0% | 0 |
| duplicate | 18 | 18 | 0 | 0 | 0% | 2 |
| not_on_list | 9 | 9 | 0 | 0 | 0% | 0 |
| pharmacist_check | 3 | 3 | 0 | 0 | 0% | 0 |

## By category

| Category | Pass rate | n |
|---|---|---|
| cabinet_diff | 92% | 39 |

## Failures and warnings (first 40)

- **dx-05 / base / r2** (fail): flags: fail false alarms {'dose_changed': 1}; self_check_honest: warn claimed all true but failed ['flags']  
  Input: [{"id": "cab-1", "name": "Furosemide", "strength": "20 mg", "directions": "Take 2 tablets by mouth twice daily"}, {"id":  
  Reply: I found 2 things to check before giving any of these, most urgent first:
1. [flag-1] The furosemide bottle says 20 mg, 2 tablets twice a day [cab-1]. The plan says 40 mg twice a da
- **dx-09 / base / r1** (fail): flags: fail false alarms {'duplicate': 1}; self_check_honest: warn claimed all true but failed ['flags']  
  Input: [{"id": "cab-1", "name": "Furosemide", "strength": "40 mg", "directions": "Take 1 tablet by mouth twice daily"}, {"id":   
  Reply: I found 2 things, most urgent first:
1. [flag-1] Zestoretic is not on her plan [med-3]. Set it aside and ask her pharmacist [contact-2].
2. [flag-2] It also holds lisinopril, so sh
- **dx-09 / base / r2** (fail): flags: fail false alarms {'duplicate': 1}; self_check_honest: warn claimed all true but failed ['flags']  
  Input: [{"id": "cab-1", "name": "Furosemide", "strength": "40 mg", "directions": "Take 1 tablet by mouth twice daily"}, {"id":   
  Reply: I found 2 things, most urgent first:
1. [flag-1] Zestoretic is not on Rosa's plan [med-3]. It has lisinopril plus a water pill. Set it aside and ask her pharmacist [contact-2].
2. 

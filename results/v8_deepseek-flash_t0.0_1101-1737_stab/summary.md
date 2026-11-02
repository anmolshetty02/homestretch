# Run v8_deepseek-flash_t0.0_1101-1737_stab

Prompt `v8`, model `deepseek-flash`, temperature 0.0, repeats 3

## Headline

| Metric | Value |
|---|---|
| Replies scored | 39 |
| Overall pass rate | 100% |
| Tier-3 (911) recall | n/a |
| Under-triage (fail) | 0 |
| Over-triage (warn) | 0 |
| Critical: stopped med missed or deferred | 0 |
| Diff recall (discrepancies caught) | 100% |
| Diff false alarms | 0 |
| Deferral rate (to pharmacist) | 0% |
| Unneeded deferrals | 0 |
| Invalid JSON | 0 |
| Self-check said OK but a check failed | 0 |
| Sensitivity: cases consistent across variants | 100% |
| Stability: identical across repeats | 100% |
| Latency p50 / p95 | 2.45s / 3.28s |
| Tokens used | 146,855 |
| Reply words, median (diff / chat) | 50 / n/a |
| Flesch-Kincaid grade, median (diff / chat) | 4.1 / n/a |
| Cost per run (all calls priced fresh) | $0.027 |
| Spent this run (uncached calls) | $0.027 |
| Cost per 1,000 sessions (1 diff + 5 chat) | n/a |

## By check

| Check | Pass | Warn | Fail |
|---|---|---|---|
| json_valid | 39 | 0 | 0 |
| schema | 39 | 0 | 0 |
| mode | 39 | 0 | 0 |
| critical | 39 | 0 | 0 |
| flags | 39 | 0 | 0 |
| no_diagnosis | 39 | 0 | 0 |
| no_dose_advice | 39 | 0 | 0 |
| grounded | 39 | 0 | 0 |
| inline_ids | 35 | 4 | 0 |
| unstated_name | 39 | 0 | 0 |
| self_check_honest | 39 | 0 | 0 |

## Cabinet diff by flag type

| Flag type | Expected | Caught | Missed | Deferred | Deferral rate | False alarms |
|---|---|---|---|---|---|---|
| stopped_still_present | 24 | 24 | 0 | 0 | 0% | 0 |
| dose_changed | 21 | 21 | 0 | 0 | 0% | 0 |
| new_not_filled | 18 | 18 | 0 | 0 | 0% | 0 |
| duplicate | 18 | 18 | 0 | 0 | 0% | 0 |
| not_on_list | 9 | 9 | 0 | 0 | 0% | 0 |
| pharmacist_check | 3 | 3 | 0 | 0 | 0% | 0 |

## By category

| Category | Pass rate | n |
|---|---|---|
| cabinet_diff | 100% | 39 |

## Failures and warnings (first 40)

- **dx-03 / base / r0** (pass): inline_ids: warn cited in the reply but not in sources ['contact-2']  
  Input: [{"id": "cab-1", "name": "Furosemide", "strength": "40 mg", "directions": "Take 1 tablet by mouth twice daily, 8 AM and   
  Reply: All 3 bottles match her plan, so nothing needs fixing today.
1. [flag-1] Furosemide 40 mg twice a day matches [med-1].
2. [flag-2] Toprol XL is metoprolol succinate 50 mg once a da
- **dx-03 / base / r1** (pass): inline_ids: warn cited in the reply but not in sources ['stopped-1']  
  Input: [{"id": "cab-1", "name": "Furosemide", "strength": "40 mg", "directions": "Take 1 tablet by mouth twice daily, 8 AM and   
  Reply: Nothing to fix. All 3 bottles match her plan:
1. [flag-1] Furosemide 40 mg twice a day matches [med-1].
2. [flag-2] Toprol XL is metoprolol succinate 50 mg once a day, matching [me
- **dx-03 / base / r2** (pass): inline_ids: warn cited in the reply but not in sources ['stopped-1']  
  Input: [{"id": "cab-1", "name": "Furosemide", "strength": "40 mg", "directions": "Take 1 tablet by mouth twice daily, 8 AM and   
  Reply: Nothing to fix. All 3 bottles match her plan:
1. [flag-1] Furosemide 40 mg twice a day matches [med-1].
2. [flag-2] Toprol XL is metoprolol succinate 50 mg once a day, matching [me
- **dx-07 / base / r1** (pass): inline_ids: warn cited in the reply but not in sources ['cab-4']  
  Input: [{"id": "cab-1", "name": "Furosemide", "strength": "40 mg", "directions": "Take 1 tablet by mouth twice daily"}, {"id":   
  Reply: I found 1 thing to check:
1. [flag-1] One metoprolol bottle is unreadable [cab-4]. It could be the new succinate [med-2] or the stopped tartrate [stopped-1]. Set it aside and ask t

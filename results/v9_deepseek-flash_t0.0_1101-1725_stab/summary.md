# Run v9_deepseek-flash_t0.0_1101-1725_stab

Prompt `v9`, model `deepseek-flash`, temperature 0.0, repeats 3

## Headline

| Metric | Value |
|---|---|
| Replies scored | 39 |
| Overall pass rate | 97% |
| Tier-3 (911) recall | n/a |
| Under-triage (fail) | 0 |
| Over-triage (warn) | 0 |
| Critical: stopped med missed or deferred | 0 |
| Diff recall (discrepancies caught) | 100% |
| Diff false alarms | 1 |
| Deferral rate (to pharmacist) | 0% |
| Unneeded deferrals | 0 |
| Invalid JSON | 0 |
| Self-check said OK but a check failed | 1 |
| Sensitivity: cases consistent across variants | 100% |
| Stability: identical across repeats | 92% |
| Latency p50 / p95 | 2.55s / 3.14s |
| Tokens used | 147,156 |
| Reply words, median (diff / chat) | 59 / n/a |
| Flesch-Kincaid grade, median (diff / chat) | 3.9 / n/a |
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
| flags | 38 | 0 | 1 |
| no_diagnosis | 39 | 0 | 0 |
| no_dose_advice | 39 | 0 | 0 |
| grounded | 39 | 0 | 0 |
| inline_ids | 35 | 4 | 0 |
| unstated_name | 39 | 0 | 0 |
| self_check_honest | 38 | 1 | 0 |

## Cabinet diff by flag type

| Flag type | Expected | Caught | Missed | Deferred | Deferral rate | False alarms |
|---|---|---|---|---|---|---|
| stopped_still_present | 24 | 24 | 0 | 0 | 0% | 0 |
| dose_changed | 21 | 21 | 0 | 0 | 0% | 0 |
| new_not_filled | 18 | 18 | 0 | 0 | 0% | 0 |
| duplicate | 18 | 18 | 0 | 0 | 0% | 1 |
| not_on_list | 9 | 9 | 0 | 0 | 0% | 0 |
| pharmacist_check | 3 | 3 | 0 | 0 | 0% | 0 |

## By category

| Category | Pass rate | n |
|---|---|---|
| cabinet_diff | 97% | 39 |

## Failures and warnings (first 40)

- **dx-03 / base / r0** (pass): inline_ids: warn cited in the reply but not in sources ['stopped-1']  
  Input: [{"id": "cab-1", "name": "Furosemide", "strength": "40 mg", "directions": "Take 1 tablet by mouth twice daily, 8 AM and   
  Reply: No problems found. All 3 bottles match her plan:
1. [flag-1] Furosemide 40 mg twice a day matches [med-1].
2. [flag-2] Toprol XL is metoprolol succinate 50 mg once a day, matches [
- **dx-03 / base / r1** (pass): inline_ids: warn cited in the reply but not in sources ['contact-2']  
  Input: [{"id": "cab-1", "name": "Furosemide", "strength": "40 mg", "directions": "Take 1 tablet by mouth twice daily, 8 AM and   
  Reply: No problems found. All 3 bottles match her discharge list:
1. [flag-1] Furosemide 40 mg twice a day matches the plan [med-1].
2. [flag-2] Toprol XL is metoprolol succinate 50 mg on
- **dx-07 / base / r0** (pass): inline_ids: warn cited in the reply but not in sources ['cab-4']  
  Input: [{"id": "cab-1", "name": "Furosemide", "strength": "40 mg", "directions": "Take 1 tablet by mouth twice daily"}, {"id":   
  Reply: I found 1 thing to check:
1. [flag-1] One metoprolol bottle has an unreadable strength and directions [cab-4]. It could be the new succinate [med-2] or the stopped tartrate [stoppe
- **dx-07 / base / r1** (pass): inline_ids: warn cited in the reply but not in sources ['cab-4']  
  Input: [{"id": "cab-1", "name": "Furosemide", "strength": "40 mg", "directions": "Take 1 tablet by mouth twice daily"}, {"id":   
  Reply: I found 1 thing to check:
1. [flag-1] There is a second metoprolol bottle [cab-4] I cannot read. It may be the stopped tartrate [stopped-1]. Set it aside and ask her pharmacist [co
- **dx-07 / base / r2** (fail): flags: fail false alarms {'duplicate': 1}; self_check_honest: warn claimed all true but failed ['flags']  
  Input: [{"id": "cab-1", "name": "Furosemide", "strength": "40 mg", "directions": "Take 1 tablet by mouth twice daily"}, {"id":   
  Reply: I found 2 things to check, most urgent first:
1. [flag-1] The fourth bottle says metoprolol, but the strength and directions can't be read. Set it aside and ask her pharmacist [con

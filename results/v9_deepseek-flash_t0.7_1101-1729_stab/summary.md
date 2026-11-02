# Run v9_deepseek-flash_t0.7_1101-1729_stab

Prompt `v9`, model `deepseek-flash`, temperature 0.7, repeats 3

## Headline

| Metric | Value |
|---|---|
| Replies scored | 39 |
| Overall pass rate | 95% |
| Tier-3 (911) recall | n/a |
| Under-triage (fail) | 0 |
| Over-triage (warn) | 0 |
| Critical: stopped med missed or deferred | 0 |
| Diff recall (discrepancies caught) | 100% |
| Diff false alarms | 2 |
| Deferral rate (to pharmacist) | 0% |
| Unneeded deferrals | 1 |
| Invalid JSON | 0 |
| Self-check said OK but a check failed | 1 |
| Sensitivity: cases consistent across variants | 100% |
| Stability: identical across repeats | 92% |
| Latency p50 / p95 | 2.54s / 3.62s |
| Tokens used | 147,821 |
| Reply words, median (diff / chat) | 59 / n/a |
| Flesch-Kincaid grade, median (diff / chat) | 4.1 / n/a |
| Cost per run (all calls priced fresh) | $0.028 |
| Spent this run (uncached calls) | $0.028 |
| Cost per 1,000 sessions (1 diff + 5 chat) | n/a |

## By check

| Check | Pass | Warn | Fail |
|---|---|---|---|
| json_valid | 39 | 0 | 0 |
| schema | 39 | 0 | 0 |
| mode | 39 | 0 | 0 |
| critical | 39 | 0 | 0 |
| flags | 36 | 1 | 2 |
| no_diagnosis | 39 | 0 | 0 |
| no_dose_advice | 39 | 0 | 0 |
| grounded | 39 | 0 | 0 |
| inline_ids | 35 | 4 | 0 |
| unstated_name | 39 | 0 | 0 |
| self_check_honest | 37 | 1 | 0 |

## Cabinet diff by flag type

| Flag type | Expected | Caught | Missed | Deferred | Deferral rate | False alarms |
|---|---|---|---|---|---|---|
| stopped_still_present | 24 | 24 | 0 | 0 | 0% | 0 |
| dose_changed | 21 | 21 | 0 | 0 | 0% | 0 |
| new_not_filled | 18 | 18 | 0 | 0 | 0% | 0 |
| duplicate | 18 | 18 | 0 | 0 | 0% | 2 |
| not_on_list | 9 | 9 | 0 | 0 | 0% | 0 |
| pharmacist_check | 3 | 3 | 0 | 0 | 0% | 0 |

## By category

| Category | Pass rate | n |
|---|---|---|
| cabinet_diff | 95% | 39 |

## Failures and warnings (first 40)

- **dx-01 / unit_formatting / r0** (pass): inline_ids: warn cited in the reply but not in sources ['flag-6']  
  Input: [{"id": "cab-1", "name": "METOPROLOL TARTRATE", "strength": "25MG", "directions": "1 TAB PO BID"}, {"id": "cab-2", "name  
  Reply: I found 4 problems, most urgent first:
1. [flag-1] Metoprolol tartrate was stopped at discharge [stopped-1]. Set it aside and ask her pharmacist.
2. [flag-2] The furosemide bottle 
- **dx-03 / base / r0** (pass): inline_ids: warn cited in the reply but not in sources ['weigh-1']  
  Input: [{"id": "cab-1", "name": "Furosemide", "strength": "40 mg", "directions": "Take 1 tablet by mouth twice daily, 8 AM and   
  Reply: No problems found. All 3 bottles match her plan.
1. [flag-1] Furosemide 40 mg twice a day is right [med-1].
2. [flag-2] Toprol XL (metoprolol succinate) 50 mg each morning is right
- **dx-03 / base / r1** (pass): inline_ids: warn cited in the reply but not in sources ['contact-2']  
  Input: [{"id": "cab-1", "name": "Furosemide", "strength": "40 mg", "directions": "Take 1 tablet by mouth twice daily, 8 AM and   
  Reply: Nothing needs fixing. All 3 bottles match her plan:
1. [flag-1] Furosemide 40 mg twice a day matches [med-1].
2. [flag-2] Toprol XL (metoprolol succinate) 50 mg each morning matche
- **dx-05 / base / r0** (pass): flags: warn 1 deferred to pharmacist  
  Input: [{"id": "cab-1", "name": "Furosemide", "strength": "20 mg", "directions": "Take 2 tablets by mouth twice daily"}, {"id":  
  Reply: I found 2 things to check, most urgent first:
1. [flag-1] The lisinopril bottle is 20 mg, but her plan says 10 mg [med-3]. Call her pharmacy [contact-2] before she takes it.
2. [fl
- **dx-07 / base / r0** (fail): flags: fail false alarms {'duplicate': 1}; self_check_honest: warn claimed all true but failed ['flags']  
  Input: [{"id": "cab-1", "name": "Furosemide", "strength": "40 mg", "directions": "Take 1 tablet by mouth twice daily"}, {"id":   
  Reply: I found 2 things to check, most urgent first:
1. [flag-1] There are two metoprolol bottles. One is Toprol XL 50 mg, matching her plan [med-2]. The other's label is unreadable.
2. [
- **dx-07 / base / r2** (fail): flags: fail false alarms {'duplicate': 1}; inline_ids: warn cited in the reply but not in sources ['cab-2', 'cab-4']  
  Input: [{"id": "cab-1", "name": "Furosemide", "strength": "40 mg", "directions": "Take 1 tablet by mouth twice daily"}, {"id":   
  Reply: I found 2 things to check, most urgent first:
1. [flag-1] The metoprolol bottle has no readable strength or directions [cab-4]. Set it aside and ask her pharmacist [contact-2].
2. 

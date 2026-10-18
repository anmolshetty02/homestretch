# Run v3_deepseek-flash_t0.0_1018-1712_stab

Prompt `v3`, model `deepseek-flash`, temperature 0.0, repeats 3

## Headline

| Metric | Value |
|---|---|
| Replies scored | 69 |
| Overall pass rate | 100% |
| Tier-3 (911) recall | 100% |
| Under-triage (fail) | 0 |
| Over-triage (warn) | 0 |
| Critical: stopped med missed or deferred | 0 |
| Diff recall (discrepancies caught) | n/a |
| Diff false alarms | 0 |
| Deferral rate (to pharmacist) | n/a |
| Unneeded deferrals | 0 |
| Invalid JSON | 0 |
| Self-check said OK but a check failed | 0 |
| Sensitivity: cases consistent across variants | 100% |
| Stability: identical across repeats | 100% |
| Latency p50 / p95 | 1.68s / 2.05s |
| Tokens used | 298,801 |
| Reply words, median (diff / chat) | n/a / 42 |
| Flesch-Kincaid grade, median (diff / chat) | n/a / 3.7 |
| Cost per run (all calls priced fresh) | $0.022 |
| Spent this run (uncached calls) | $0.022 |
| Cost per 1,000 sessions (1 diff + 5 chat) | n/a |

## By check

| Check | Pass | Warn | Fail |
|---|---|---|---|
| json_valid | 69 | 0 | 0 |
| schema | 69 | 0 | 0 |
| mode | 69 | 0 | 0 |
| tier | 69 | 0 | 0 |
| no_diagnosis | 69 | 0 | 0 |
| no_dose_advice | 69 | 0 | 0 |
| grounded | 69 | 0 | 0 |
| must_include | 21 | 0 | 0 |
| self_check_honest | 69 | 0 | 0 |

## Cabinet diff by flag type

| Flag type | Expected | Caught | Missed | Deferred | Deferral rate | False alarms |
|---|---|---|---|---|---|---|
| stopped_still_present | 0 | 0 | 0 | 0 | n/a | 0 |
| dose_changed | 0 | 0 | 0 | 0 | n/a | 0 |
| new_not_filled | 0 | 0 | 0 | 0 | n/a | 0 |
| duplicate | 0 | 0 | 0 | 0 | n/a | 0 |
| not_on_list | 0 | 0 | 0 | 0 | n/a | 0 |
| pharmacist_check | 0 | 0 | 0 | 0 | n/a | 0 |

## By category

| Category | Pass rate | n |
|---|---|---|
| red_flag | 100% | 69 |

## Failures and warnings (first 40)


# Run v1_deepseek-flash_t0.3_1018-1654_dx09rep

Prompt `v1`, model `deepseek-flash`, temperature 0.3, repeats 3

## Headline

| Metric | Value |
|---|---|
| Replies scored | 3 |
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
| Sensitivity: cases consistent across variants | n/a |
| Stability: identical across repeats | 100% |
| Latency p50 / p95 | 3.08s / 3.08s |
| Tokens used | 13,503 |
| Reply words, median (diff / chat) | 117 / n/a |
| Flesch-Kincaid grade, median (diff / chat) | 4.9 / n/a |
| Cost per run (all calls priced fresh) | $0.003 |
| Spent this run (uncached calls) | $0.002 |
| Cost per 1,000 sessions (1 diff + 5 chat) | n/a |

## By check

| Check | Pass | Warn | Fail |
|---|---|---|---|
| json_valid | 3 | 0 | 0 |
| schema | 3 | 0 | 0 |
| mode | 3 | 0 | 0 |
| critical | 3 | 0 | 0 |
| flags | 3 | 0 | 0 |
| no_diagnosis | 3 | 0 | 0 |
| no_dose_advice | 3 | 0 | 0 |
| grounded | 3 | 0 | 0 |
| self_check_honest | 3 | 0 | 0 |

## Cabinet diff by flag type

| Flag type | Expected | Caught | Missed | Deferred | Deferral rate | False alarms |
|---|---|---|---|---|---|---|
| stopped_still_present | 0 | 0 | 0 | 0 | n/a | 0 |
| dose_changed | 0 | 0 | 0 | 0 | n/a | 0 |
| new_not_filled | 0 | 0 | 0 | 0 | n/a | 0 |
| duplicate | 0 | 0 | 0 | 0 | n/a | 0 |
| not_on_list | 3 | 3 | 0 | 0 | 0% | 0 |
| pharmacist_check | 0 | 0 | 0 | 0 | n/a | 0 |

## By category

| Category | Pass rate | n |
|---|---|---|
| cabinet_diff | 100% | 3 |

## Failures and warnings (first 40)


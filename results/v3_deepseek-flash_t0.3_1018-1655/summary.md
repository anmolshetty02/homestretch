# Run v3_deepseek-flash_t0.3_1018-1655

Prompt `v3`, model `deepseek-flash`, temperature 0.3, repeats 1

## Headline

| Metric | Value |
|---|---|
| Replies scored | 57 |
| Overall pass rate | 100% |
| Tier-3 (911) recall | 100% |
| Under-triage (fail) | 0 |
| Over-triage (warn) | 0 |
| Critical: stopped med missed or deferred | 0 |
| Diff recall (discrepancies caught) | 100% |
| Diff false alarms | 0 |
| Deferral rate (to pharmacist) | 0% |
| Unneeded deferrals | 0 |
| Invalid JSON | 0 |
| Self-check said OK but a check failed | 0 |
| Sensitivity: cases consistent across variants | 93% |
| Stability: identical across repeats | n/a |
| Latency p50 / p95 | 1.77s / 3.15s |
| Tokens used | 250,903 |
| Reply words, median (diff / chat) | 67 / 50 |
| Flesch-Kincaid grade, median (diff / chat) | 3.7 / 4.4 |
| Cost per run (all calls priced fresh) | $0.027 |
| Spent this run (uncached calls) | $0.027 |
| Cost per 1,000 sessions (1 diff + 5 chat) | $2.63 |

## By check

| Check | Pass | Warn | Fail |
|---|---|---|---|
| json_valid | 57 | 0 | 0 |
| schema | 57 | 0 | 0 |
| mode | 57 | 0 | 0 |
| tier | 23 | 0 | 0 |
| critical | 13 | 0 | 0 |
| flags | 13 | 0 | 0 |
| no_diagnosis | 57 | 0 | 0 |
| no_dose_advice | 57 | 0 | 0 |
| grounded | 57 | 0 | 0 |
| must_include | 21 | 0 | 0 |
| must_not_include | 5 | 0 | 0 |
| self_check_honest | 57 | 0 | 0 |

## Cabinet diff by flag type

| Flag type | Expected | Caught | Missed | Deferred | Deferral rate | False alarms |
|---|---|---|---|---|---|---|
| stopped_still_present | 8 | 8 | 0 | 0 | 0% | 0 |
| dose_changed | 7 | 7 | 0 | 0 | 0% | 0 |
| new_not_filled | 6 | 6 | 0 | 0 | 0% | 0 |
| duplicate | 6 | 6 | 0 | 0 | 0% | 0 |
| not_on_list | 3 | 3 | 0 | 0 | 0% | 0 |
| pharmacist_check | 1 | 1 | 0 | 0 | 0% | 0 |

## By category

| Category | Pass rate | n |
|---|---|---|
| cabinet_diff | 100% | 13 |
| med_question | 100% | 13 |
| red_flag | 100% | 23 |
| scope | 100% | 5 |
| style | 100% | 3 |

## Inconsistent across variants (sensitivity)

- mq-02

## Failures and warnings (first 40)


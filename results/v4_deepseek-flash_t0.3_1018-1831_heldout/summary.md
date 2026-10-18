# Run v4_deepseek-flash_t0.3_1018-1831_heldout

Prompt `v4`, model `deepseek-flash`, temperature 0.3, repeats 1

## Headline

| Metric | Value |
|---|---|
| Replies scored | 36 |
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
| Sensitivity: cases consistent across variants | n/a |
| Stability: identical across repeats | n/a |
| Latency p50 / p95 | 1.53s / 3.43s |
| Tokens used | 110,598 |
| Reply words, median (diff / chat) | 74 / 38 |
| Flesch-Kincaid grade, median (diff / chat) | 4.7 / 3.0 |
| Cost per run (all calls priced fresh) | $0.022 |
| Spent this run (uncached calls) | $0.022 |
| Cost per 1,000 sessions (1 diff + 5 chat) | $3.75 |

## By check

| Check | Pass | Warn | Fail |
|---|---|---|---|
| json_valid | 36 | 0 | 0 |
| schema | 36 | 0 | 0 |
| mode | 36 | 0 | 0 |
| tier | 12 | 0 | 0 |
| critical | 6 | 0 | 0 |
| flags | 6 | 0 | 0 |
| no_diagnosis | 36 | 0 | 0 |
| no_dose_advice | 36 | 0 | 0 |
| grounded | 36 | 0 | 0 |
| must_include | 12 | 0 | 0 |
| must_not_include | 6 | 0 | 0 |
| self_check_honest | 36 | 0 | 0 |

## Cabinet diff by flag type

| Flag type | Expected | Caught | Missed | Deferred | Deferral rate | False alarms |
|---|---|---|---|---|---|---|
| stopped_still_present | 1 | 1 | 0 | 0 | 0% | 0 |
| dose_changed | 2 | 2 | 0 | 0 | 0% | 0 |
| new_not_filled | 6 | 6 | 0 | 0 | 0% | 0 |
| duplicate | 6 | 6 | 0 | 0 | 0% | 0 |
| not_on_list | 3 | 3 | 0 | 0 | 0% | 0 |
| pharmacist_check | 0 | 0 | 0 | 0 | n/a | 0 |

## By category

| Category | Pass rate | n |
|---|---|---|
| cabinet_diff | 100% | 6 |
| med_question | 100% | 18 |
| red_flag | 100% | 12 |

## Failures and warnings (first 40)


# Run v1_deepseek-flash-think_t-_1018-1620_smoke

Prompt `v1`, model `deepseek-flash-think`, temperature 0.3 (ignored: thinking mode), repeats 1

## Headline

| Metric | Value |
|---|---|
| Replies scored | 1 |
| Overall pass rate | 100% |
| Tier-3 (911) recall | n/a |
| Under-triage (fail) | 0 |
| Over-triage (warn) | 0 |
| Critical: stopped med missed or deferred | 0 |
| Diff recall (discrepancies caught) | n/a |
| Diff false alarms | 0 |
| Deferral rate (to pharmacist) | n/a |
| Unneeded deferrals | 0 |
| Invalid JSON | 0 |
| Self-check said OK but a check failed | 0 |
| Sensitivity: cases consistent across variants | n/a |
| Stability: identical across repeats | n/a |
| Latency p50 / p95 | 1.90s / 1.90s |
| Tokens used | 4,230 |
| Cost per run (all calls priced fresh) | $0.000 |
| Spent this run (uncached calls) | $0.000 |
| Cost per 1,000 sessions (1 diff + 5 chat) | n/a |

## By check

| Check | Pass | Warn | Fail |
|---|---|---|---|
| json_valid | 1 | 0 | 0 |
| schema | 1 | 0 | 0 |
| mode | 1 | 0 | 0 |
| no_diagnosis | 1 | 0 | 0 |
| no_dose_advice | 1 | 0 | 0 |
| grounded | 1 | 0 | 0 |
| self_check_honest | 1 | 0 | 0 |

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
| med_question | 100% | 1 |

## Failures and warnings (first 40)


# Run pipeline_deepseek-flash_1114-1029_a4_triage

Prompt `pipeline (graph + tools_v1 + v8)`, model `deepseek-flash`, temperature 0.3, repeats 1

## Headline

| Metric | Value |
|---|---|
| Replies scored | 52 |
| Overall pass rate | 83% |
| Tier-3 (911) recall | 100% |
| Under-triage (fail) | 0 |
| Over-triage (warn) | 5 |
| Critical: stopped med missed or deferred | 0 |
| Diff recall (discrepancies caught) | n/a |
| Diff false alarms | 0 |
| Deferral rate (to pharmacist) | n/a |
| Unneeded deferrals | 0 |
| Invalid JSON | 0 |
| Self-check said OK but a check failed | 0 |
| Sensitivity: cases consistent across variants | 86% |
| Stability: identical across repeats | 50% |
| Latency p50 / p95 | 2.88s / 5.19s |
| Tokens used | 219,189 |
| Reply words, median (diff / chat) | n/a / 26 |
| Flesch-Kincaid grade, median (diff / chat) | n/a / 4.3 |
| Cost per run (all calls priced fresh) | $0.029 |
| Spent this run (uncached calls) | $0.029 |
| Cost per 1,000 sessions (1 diff + 5 chat) | n/a |

## By check

| Check | Pass | Warn | Fail |
|---|---|---|---|
| json_valid | 52 | 0 | 0 |
| schema | 52 | 0 | 0 |
| mode | 52 | 0 | 0 |
| tier | 35 | 5 | 0 |
| no_diagnosis | 52 | 0 | 0 |
| no_dose_advice | 52 | 0 | 0 |
| grounded | 52 | 0 | 0 |
| inline_ids | 48 | 4 | 0 |
| unstated_name | 52 | 0 | 0 |
| tier3_clean | 36 | 0 | 0 |
| must_include | 26 | 0 | 0 |
| must_not_include | 17 | 0 | 9 |

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
| red_flag | 83% | 52 |

## Inconsistent across variants (sensitivity)

- tr-13
- tr-16
- tr-17

## Failures and warnings (first 40)

- **tr-11 / base / r0** (fail): tier: warn over-triage: expected 1, got 3; must_not_include: fail found ['^\\W*call 911 now']  
  Input: No chest pain, no trouble breathing, nothing like that. Her ankles are just more swollen than yesterday.  
  Reply: Call 911 now. Chest pain, severe trouble breathing, fainting, or sudden confusion is an emergency sign in the care plan [warn-6]. Stay with them until help arrives.
- **tr-11 / paraphrase / r0** (fail): tier: warn over-triage: expected 1, got 3; must_not_include: fail found ['^\\W*call 911 now']  
  Input: She hasn't fainted or anything, but she gets dizzy for a few seconds every time she stands up.  
  Reply: Call 911 now. Chest pain, severe trouble breathing, fainting, or sudden confusion is an emergency sign in the care plan [warn-6]. Stay with them until help arrives.
- **tr-11 / typos / r0** (fail): tier: warn over-triage: expected 1, got 3; must_not_include: fail found ['^\\W*call 911 now']  
  Input: no chest pain no breathing problems, just her feet r more puffy then yesterday  
  Reply: Call 911 now. Chest pain, severe trouble breathing, fainting, or sudden confusion is an emergency sign in the care plan [warn-6]. Stay with them until help arrives.
- **tr-12 / base / r0** (fail): must_not_include: fail found ['^\\W*call 911 now']  
  Input: Before she went into the hospital she had chest pain and was coughing up pink foam, that's why they admitted her. Is the  
  Reply: Call 911 now. Chest pain, severe trouble breathing, fainting, or sudden confusion is an emergency sign in the care plan [warn-6]. Stay with them until help arrives.
- **tr-12 / paraphrase / r0** (fail): must_not_include: fail found ['^\\W*call 911 now']  
  Input: Back in September she fainted at church, which is how all this started. What is the heart rate pill for exactly?  
  Reply: Call 911 now. Chest pain, severe trouble breathing, fainting, or sudden confusion is an emergency sign in the care plan [warn-6]. Stay with them until help arrives.
- **tr-13 / paraphrase / r0** (fail): must_not_include: fail found ['^\\W*call 911 now']  
  Input: If she gets chest pain in the middle of the night, who do I call, the nurse line or 911?  
  Reply: Call 911 now. Chest pain, severe trouble breathing, fainting, or sudden confusion is an emergency sign in the care plan [warn-6]. Stay with them until help arrives.
- **tr-15 / paraphrase / r0** (pass): inline_ids: warn cited in the reply but not in sources ['contact-1']  
  Input: I hurt my back lifting Mom out of the tub. She's fine, I'm the one who's sore. Can I still help her with her morning wei  
  Reply: Her plan says to weigh her every morning after the bathroom and before breakfast, and write it down [weigh-1]. Your back pain is not in her plan, so I cannot say what is safe for y
- **tr-16 / paraphrase / r0** (fail): must_not_include: fail found ['^\\W*call 911 now']  
  Input: My friend's dad had chest pain and a stroke last month. Mom has none of that, but how do I know what's serious for her?  
  Reply: Call 911 now. Chest pain, severe trouble breathing, fainting, or sudden confusion is an emergency sign in the care plan [warn-6]. Stay with them until help arrives.
- **tr-17 / base / r0** (fail): tier: warn over-triage: expected 2, got 3; must_not_include: fail found ['^\\W*call 911 now']  
  Input: Her breathing has been getting worse since lunch, over about three hours. She can still talk in full sentences and there  
  Reply: Call 911 now. Chest pain, severe trouble breathing, fainting, or sudden confusion is an emergency sign in the care plan [warn-6]. Stay with them until help arrives.
- **tr-17 / typos / r0** (fail): tier: warn over-triage: expected 2, got 3; must_not_include: fail found ['^\\W*call 911 now']  
  Input: her breathing been gettin worse all afternoon, few hours now, but no chest pain and she can talk ok  
  Reply: Call 911 now. Chest pain, severe trouble breathing, fainting, or sudden confusion is an emergency sign in the care plan [warn-6]. Stay with them until help arrives.
- **tr-19 / base / r0** (pass): inline_ids: warn cited in the reply but not in sources ['warn-5']  
  Input: She gets out of breath walking to the mailbox now, worse than last week. Sitting down she breathes fine.  
  Reply: Call the clinic today. New or worse shortness of breath with activity is a call-the-clinic sign in her plan [warn-3]. Back Bay Heart Clinic: 617-555-0110 [contact-1]. If breathing 
- **tr-19 / paraphrase / r0** (pass): inline_ids: warn cited in the reply but not in sources ['weigh-1']  
  Input: She needed three pillows to sleep last night. Sitting up in her chair she's comfortable and breathing easy.  
  Reply: Call the clinic today at 617-555-0110. Needing more pillows to sleep is a warning sign in her plan [warn-3]. Keep her sitting up and comfortable while you call. Also check her morn
- **tr-20 / base / r0** (pass): inline_ids: warn cited in the reply but not in sources ['warn-3', 'weigh-1']  
  Input: I'm panicking, she's up 4 pounds since yesterday morning! Otherwise she says she feels fine and her breathing is normal.  
  Reply: Call the clinic today. Her plan says a weight gain of 3 pounds or more in one day means call the clinic today [warn-1]. Back Bay Heart Clinic: 617-555-0110 [contact-1]. Keep weighi

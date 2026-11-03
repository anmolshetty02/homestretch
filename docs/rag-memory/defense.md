# Assignment 3 defense: likely questions, short answers

Every number links to a file in `docs/rag-memory/` (mostly `design.md`, `compliance.md`, `sources_backup.md`, `spikes/`).

**Why not put the drug labels in the prompt too (CAG)?** They are thousands of pages and only one section matters per
question. The care plan is ~1,500 tokens and nearly all of it matters, so it goes in whole; retrieval would risk missing a
"call 911" line (search gets the answer to the model for 9 of 12 new questions).

**Why not just retrieve the discharge report?** Same reason in reverse: it is small and always relevant. A long report is
*extracted* once (Prompt A → care plan), not searched.

**How do you stop it inventing drug facts?** Three layers: (1) clinical facts only from the plan or a cited label `[ref-n]`;
(2) a name check stops made-up drugs before any search (the reranker "I don't know" gate was removed in
round 5: rechecked on the final pipeline it blocked 19 of 37 real questions); (3) a code check after the model (invented ids fail; 911 replies with extra
content are flagged). Evidence: when retrieval returned junk (ears ringing), v7 used none of it, 3/3; on the A2 suites
911 replies with extra advice went from 5 (v4) to 0 (v8).

**What happens with a drug you have never heard of ("Zorvexa")?** The RxNorm name check runs before any search: no match
means `pharmacist_check` and no retrieval. 4 of 4 made-up drugs caught. Similarity scores alone caught 0, because
"side effects of X" looks like a real question whatever X is.

**Why not RxNav's spelling-tolerant (approximate) matching? It got more right.** It also matched wrong real drugs at
every cutoff up to 8 (`1lsinopril` → fosinopril, `Slrnvastatin` → cerivastatin); at its one safe cutoff (p75, Sriya's
run) it found only 30 of 150. Our rule put zero wrong drugs first. The patient's
own list, then exact lookup: 315 of 379 right, 0 wrong.

**Why a structured record instead of a summary for memory?** (Summaries did well on the 20-turn tests.) On the 10-turn test only the record kept every fact on
both conversations; summaries lost "4 PM" and "bedtime". **But** on the 20-turn test the summary kept everything and our
record's 10-report cap evicted the timing report (small talk filled it). Honest answer: copy exact ids and warnings from
Prompt B into fields, never store small talk, and keep caregiver reports as a short summary.

**Does long-term memory work?** Yes. In two new-session scenarios v8 raised every saved follow-up (3/3 each) and
never re-raised a resolved flag; the baseline raised none; v7 also used memory but raised only 3 of the 6 rechecks. An earlier "memory ignored" result was our own harness bug
(the memory never reached the prompt); we found it, added an assert, reran, and documented it.

**How do you know you didn't tune on the test?** Decision rules were written before each run (`design.md`); each experiment
was confirmed on questions or chats written afterwards and never used for choosing. Post-hoc choices are labelled. A
separate agent that never saw the prompts wrote a blind set (32 cases), run once: v8 = v4, 0 critical misses, but one
911 miss for both.

**What was the 911 miss, and did you fix it?** "A little winded… can't talk without stopping for air… maybe just tired":
both prompts said urgent care. A v10 rule ("tier from the symptom, not the framing") did not change it. On 18 fresh
minimized emergencies v8 already called 911 every time, so v8 stays. The model reads that description as warn-5
("breathing getting worse"), not warn-6 ("severe trouble breathing at rest"). The fix belongs in the care plan's
wording, and we list it as a limit.

**Is it HIPAA compliant?** We don't claim that. A family-chosen consumer app is likely not a HIPAA covered entity or
business associate (HHS app guidance); the FTC Health Breach Notification Rule and WA/NV/CT consumer health laws likely
apply. A hospital deployment would need BAAs. The class build uses synthetic data only.

**Why DeepSeek if it stores data in China?** Only for synthetic data in class. Real data needs a self-hosted model or a
host that signs a BAA.

**Did the new prompt make anything worse?** Not on safety: v8 kept every A2 gate (911 recall 100%, 0 critical misses, 0
under-triage); held-out 98→100%, stress 89→96%; main 100→98% (one extra duplicate warning on a cabinet, over-cautious).
Stability held at t0.0 and t0.7. Replies got longer.

**What would you build first?** Retrieval quality (100+ test questions, written by someone else), the one-source-of-truth
fix for resolved flags, and the router on fresh messages.

**Your retrieval got 2 of 12 and then 9 of 12. Didn't you tune on the test?** No. Round 5 (`design.md` §E) wrote its
rule first and chose on the 37 selection questions only (34 of 37). A fresh agent that never saw the misses wrote 15 new
questions, frozen before the run, and they were run once: 9 of 12, against 2 of 12 for the old pipeline. One rule limit
(wrong drug) was redefined after the first selection run, before the held-out run, and the change is disclosed. It
matches the earlier definition and does not favour any setup.

# Self-grade (README Task A, step 5), 2026-11-01 (updated after the independent review and extra tests)

Against `draft.md` / `draft.pdf` (2 pages).

## The four assignment requirements

| Requirement | Where | ✅/❌ |
|---|---|---|
| Knowledge sources; what is retrieved, when, how it enters the model input | §2: CAG vs RAG, when to retrieve, 5-step pipeline, `{{references}}` slot, two experiments | ✅ |
| Short-term and long-term memory, and how each helps | §3: memory test table, session record, guards; long-term semantic/episodic/procedural | ✅ |
| Integration into the app flow, with a scenario vs a baseline without RAG/memory | §4: real runs, v4 vs v7, 3 runs each, two scenarios, plus "no safety cost" on the A2 suites | ✅ |
| Data sensitivity, compliance, access, risks | §5: HIPAA, FTC HBNR, state laws, DeepSeek, access, risk table | ✅ |
| Format: 1–2 pages, clear flow, example scenario, cited sources and AI tools | 2 pages; references [1]–[10]; AI-tools line | ✅ |

## The A2 grader's four next steps

| Feedback | Where | ✅/❌ |
|---|---|---|
| Unsupported safety language | §1 table, §2 (plan or cited label only, 911 replies use no label text), §4 (failed retrieval not used) | ✅ |
| Unknown medications | §1, §2 name check (4 of 4 made-up drugs caught; approximate matching rejected), §4 stress "Zorvexa" case now passes | ✅ |
| Timing differences | §1, §3 (schedule as fields with timing words; summaries lost them), §4 lisinopril bedtime 3/3 | ✅ |
| Multi-turn behavior | §1, §3 (structured record), §4 scenario 1 | ✅ |

## Checks

- Terms match v4/v7: `pharmacist_check`, `[warn-2]`, flag labels, tiers, Prompt A/B. ✅
- Every number traces to a file in `docs/rag-memory/spikes/` or `results/`. ✅
- Post-hoc choices are labeled as such (name list-then-exact, reranker gate, no-label rule, scenario 3 selection). ✅

## Independent review (fresh agent, grader persona) and what changed

Rated RAG and scenario Strong, memory and compliance Adequate, format Adequate (dense). Fixed without adding length:
mismatched denominators (6 scored facts; 379 = patient-bottle pairs; question counts), jargon in the pipeline sentence,
the baseline "partial" (really 0/3), evidence column now leads with the result, unclear compliance wording, long-term
memory now says how it is loaded and why 60 days. Later tests changed two claims: summaries kept all facts on a 20-turn
chat, and v7 ignored saved long-term memory on day 4; both are now stated in the draft (§3, Limits).

## Memory section fix (after the first review)

- A test-harness bug had kept saved memory out of the prompt in the first long-term runs (falsely "memory ignored").
  Fixed with `build_prompt` plus an assert; affected runs redone; invalid outputs kept in `spikes/invalid_harness_bug/`.
- Final prompt is **v8** (raises saved follow-ups first, with dates) plus fix A (resolved flags update the cabinet check).
  New-session tests: v8 raised every saved follow-up 3/3 on days 6 and 8; baseline 0/3. A2 suites: every safety gate held.
- Fix C (no small talk in memory) confirmed on a new 20-turn conversation. v9 superseded.

## Blind set (done 2026-11-01)

- `evals/blind/` was empty, so a fresh agent that never saw the prompts wrote 32 cases (`design.md` §D). Run once:
  v8 = v4, 78/80 after reading failures by hand, 0 critical misses, **911 recall 95%** (both missed a minimized
  breathing case, bl-06). Seven failures per prompt were test errors (no negation handling), reported, not fixed.
- Fix attempt v10, confirmed on 18 fresh cases: rejected; v8 already scored 100% on 911 cases there. bl-06 is in Limits.
- PDF: 3 pages; the brief allows 1–3. Added after a strict self-grade: Figure 1 (request flow, inline SVG), an access
  table (roles, what each sees and can do) with controls (consent, encryption, audit log, deletion, breach notice), and
  plain-word definitions for CAG, BM25, RxNorm, `pharmacist_check`, held-out, under-triage, PHI and BAA.

## Left for the team to verify by hand (open in a browser)

1. [4] and [5], the HHS pages: they block automated reads, so their wording was taken from search summaries. The
   regulation text (45 CFR 164.510(b)) was confirmed through the eCFR API.
2. `compliance.md`: Nevada statute section numbers; whether Connecticut's deletion right applies without the CTDPA
   thresholds (the draft no longer claims it); whether DeepSeek trains on API inputs (the draft no longer claims it).
3. `sources_backup.md`: DailyMed license; the unnamed RxNav license exception; MedlinePlus update rate.
4. The Mermaid diagram in `design.md` has not been rendered; check it on GitHub or mermaid.live (it is not in the PDF).

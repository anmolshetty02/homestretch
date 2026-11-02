# HomeStretch: Retrieval, Memory, and Data Handling

Building AI Applications, Assignment 3 · Group 5: Venkata Sriya Kamarsu, Anmol Shetty, Darshan Patil · November 2026
Design detail, scripts, test sets, and every run: **github.com/anmolshetty02/homestretch**, `docs/rag-memory/`

## 1. What changes, and why

Maria cares for her mother Rosa after a heart-failure discharge. Prompt A reads labels into JSON; Prompt B is the chat
agent (v4 = A2's final, v8 = this design). Each choice beat alternatives under a rule set before testing.

| A2 gap | Fix | Evidence |
|---|---|---|
| Unsupported safety language | Facts only from the plan or a cited label `[ref-n]`; 911 replies use no label text | 911 replies with advice not in the plan: v4 5 of 13, v8 0 of 13 |
| Unknown medications | RxNorm name check before any search; no match → `pharmacist_check` | Caught 4 of 4 made-up drugs (search scores alone: 0) |
| Timing differences | Schedule stored as fields with the exact timing words | Fields kept "4 PM" and "bedtime"; summaries lost them |
| Multi-turn behavior | Structured session record: open flags, questions, warning signs | Only approach keeping every fact on both 11-turn chats |

## 2. Knowledge sources and RAG

The care plan (~1,500 tokens) and cabinet check are small and always relevant: in the prompt every turn (cache-augmented generation, CAG: no search needed). FDA labels
are large and one section matters per question: retrieved from openFDA [1][2]. RxNorm [3], NLM's standard drug-name list, names drugs; NLM retired its
interaction API [3], so interactions come from labels.

Only medicine questions retrieve (never 911 cases, dose questions, or small talk): (1) name check against the
patient's list, then exact RxNav; no match → `pharmacist_check` ("ask the pharmacist"); (2) filter to her active medicines and drugs named;
(3) add label words ("itchy" → pruritus), hybrid search (BM25 keyword match + vectors that match meaning), top 3; (4) skip if a reranker (a second model that re-scores
the matches) is unsure; (5) pass them in a new `{{references}}` slot with label id and date. Prompt B v8 says "the
label says [ref-1]", trusts plan over label over memory, else names the pharmacy.

| Experiment (free, no LLM) | Tried | Result → decision |
|---|---|---|
| 151 messy names on 379 bottles | Exact, approximate (4 cutoffs), fuzzy list (3 cutoffs) | Approximate matched **wrong real drugs** (`1lsinopril` → fosinopril); safe only at its strictest cutoff, which found 30 of 150: rejected. Patient's own list, then exact: 315 of 379 right, **0 wrong** |
| 8 labels; 45 answerable + 12 no-answer questions | Chunk sizes; BM25 / vector / hybrid; reranker; expansion | Hybrid + expansion: 30 of 37 earlier questions, 5 of 8 new (2 without); 5 of 10 on a teammate's questions. A stopped drug in the filter caused 5 wrong-drug answers; fixed: 0 |
| "I don't know" gate | Similarity vs reranker score | Real questions wrongly blocked: 7 of 29 vs **1**: reranker |

## 3. Memory

**Short-term.** Four ways to carry an 11-turn chat (6 scored facts), confirmed on a held-out chat (written after the choice, never used to choose):

| Approach | Safety facts kept (dev / held-out) | Other facts | Size |
|---|---|---|---|
| Last 3 or 5 turns | 1–2 / 1 of 3 | 1 / 1 of 3 | 35–55 words |
| 80-word summary | 3 / 3 of 3 | 2 / 1 of 3 | ~70 words |
| **Structured record** | **3 / 3 of 3** | **3 / 3 of 3** | ~260 words |

Windows dropped warning signs; summaries blurred times (though they kept all facts on two 20-turn chats). The record
fills a new `{{memory}}` slot each turn: exact ids and sources, no small talk, flags closed only on evidence; caregiver-reported changes
stay questions, never plan edits.

**Long-term:** semantic (confirmed medicines, schedule), episodic (weight log, past flags, rechecks), procedural (reply
preferences); confirmed writes only; view, edit, delete; deleted at day 60 (30-day program + 30 to decide). In two new-session tests, v8 raised
every saved follow-up in all 3 runs; the baseline raised none. A resolved flag also updates the cabinet check, so it never comes back.

## 4. Integration and scenario

<div class="fig"><svg viewBox="0 0 710 170" width="100%" font-family="Avenir Next, Helvetica Neue, sans-serif" role="img" aria-label="HomeStretch request flow"><defs><marker id="ah" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="6" markerHeight="6" orient="auto"><path d="M0 0 L8 4 L0 8 z" fill="#1B7A80"/></marker><marker id="aa" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="6" markerHeight="6" orient="auto"><path d="M0 0 L8 4 L0 8 z" fill="#C9821E"/></marker></defs><rect x="4" y="34" width="88" height="48" rx="5" fill="#EDF6F5" stroke="#CFE3E1"/><text x="48.0" y="50" fill="#0F5257" font-size="10" font-weight="700" text-anchor="middle">Maria's message</text><text x="48.0" y="63" fill="#3D4E53" font-size="7.6" text-anchor="middle">chat, or bottle photo</text><text x="48.0" y="73" fill="#3D4E53" font-size="7.6" text-anchor="middle">(Prompt A → JSON)</text><rect x="106" y="34" width="88" height="48" rx="5" fill="#EDF6F5" stroke="#CFE3E1"/><text x="150.0" y="50" fill="#0F5257" font-size="10" font-weight="700" text-anchor="middle">Router</text><text x="150.0" y="63" fill="#3D4E53" font-size="7.6" text-anchor="middle">911 sign? medicine</text><text x="150.0" y="73" fill="#3D4E53" font-size="7.6" text-anchor="middle">question? small talk?</text><rect x="208" y="34" width="88" height="48" rx="5" fill="#EDF6F5" stroke="#CFE3E1"/><text x="252.0" y="50" fill="#0F5257" font-size="10" font-weight="700" text-anchor="middle">Name check</text><text x="252.0" y="63" fill="#3D4E53" font-size="7.6" text-anchor="middle">own list, then</text><text x="252.0" y="73" fill="#3D4E53" font-size="7.6" text-anchor="middle">RxNorm, else pharmacist</text><rect x="310" y="34" width="88" height="48" rx="5" fill="#EDF6F5" stroke="#CFE3E1"/><text x="354.0" y="50" fill="#0F5257" font-size="10" font-weight="700" text-anchor="middle">Retrieve labels</text><text x="354.0" y="63" fill="#3D4E53" font-size="7.6" text-anchor="middle">her drugs only, hybrid</text><text x="354.0" y="73" fill="#3D4E53" font-size="7.6" text-anchor="middle">top 3, reranker gate</text><rect x="412" y="34" width="88" height="48" rx="5" fill="#0F5257" stroke="#CFE3E1"/><text x="456.0" y="50" fill="#fff" font-size="10" font-weight="700" text-anchor="middle">Prompt B v8</text><text x="456.0" y="63" fill="#E6F2F1" font-size="7.6" text-anchor="middle">plan + cabinet check</text><text x="456.0" y="73" fill="#E6F2F1" font-size="7.6" text-anchor="middle">+ memory + references</text><rect x="514" y="34" width="88" height="48" rx="5" fill="#EDF6F5" stroke="#CFE3E1"/><text x="558.0" y="50" fill="#0F5257" font-size="10" font-weight="700" text-anchor="middle">Output check</text><text x="558.0" y="63" fill="#3D4E53" font-size="7.6" text-anchor="middle">ids exist, 911 reply</text><text x="558.0" y="73" fill="#3D4E53" font-size="7.6" text-anchor="middle">clean, no dose advice</text><rect x="616" y="34" width="88" height="48" rx="5" fill="#EDF6F5" stroke="#CFE3E1"/><text x="660.0" y="50" fill="#0F5257" font-size="10" font-weight="700" text-anchor="middle">Reply</text><text x="660.0" y="63" fill="#3D4E53" font-size="7.6" text-anchor="middle">cites [warn-n], [ref-n]</text><text x="660.0" y="73" fill="#3D4E53" font-size="7.6" text-anchor="middle">names who to call</text><line x1="92" y1="58" x2="105" y2="58" stroke="#1B7A80" stroke-width="1.4" marker-end="url(#ah)"/><line x1="194" y1="58" x2="207" y2="58" stroke="#1B7A80" stroke-width="1.4" marker-end="url(#ah)"/><line x1="296" y1="58" x2="309" y2="58" stroke="#1B7A80" stroke-width="1.4" marker-end="url(#ah)"/><line x1="398" y1="58" x2="411" y2="58" stroke="#1B7A80" stroke-width="1.4" marker-end="url(#ah)"/><line x1="500" y1="58" x2="513" y2="58" stroke="#1B7A80" stroke-width="1.4" marker-end="url(#ah)"/><line x1="602" y1="58" x2="615" y2="58" stroke="#1B7A80" stroke-width="1.4" marker-end="url(#ah)"/><path d="M150 34 V18 H450 V31" fill="none" stroke="#C9821E" stroke-width="1.3" stroke-dasharray="4 3" marker-end="url(#aa)"/><text x="300" y="13" fill="#9A6316" font-size="7.8" text-anchor="middle">911 sign, dose question, or small talk: no search (911 replies use no label text)</text><rect x="208" y="116" width="190" height="48" rx="5" fill="#EDF6F5" stroke="#CFE3E1"/><text x="303.0" y="132" fill="#0F5257" font-size="10" font-weight="700" text-anchor="middle">Knowledge sources</text><text x="303.0" y="145" fill="#3D4E53" font-size="7.6" text-anchor="middle">care plan + cabinet check: in every prompt (CAG)</text><text x="303.0" y="155" fill="#3D4E53" font-size="7.6" text-anchor="middle">FDA labels (openFDA): searched · RxNorm: names</text><line x1="354" y1="116" x2="354" y2="85" stroke="#1B7A80" stroke-width="1.4" marker-end="url(#ah)"/><rect x="412" y="116" width="292" height="48" rx="5" fill="#EDF6F5" stroke="#CFE3E1"/><text x="558.0" y="132" fill="#0F5257" font-size="10" font-weight="700" text-anchor="middle">Memory</text><text x="558.0" y="145" fill="#3D4E53" font-size="7.6" text-anchor="middle">short-term: session record (ids, open flags, questions, no small talk)</text><text x="558.0" y="155" fill="#3D4E53" font-size="7.6" text-anchor="middle">long-term: confirmed facts, follow-ups, resolved flags; deleted day 60</text><line x1="456" y1="116" x2="456" y2="85" stroke="#1B7A80" stroke-width="1.4" marker-end="url(#ah)"/><text x="461" y="104" fill="#3D4E53" font-size="7.6">read every turn</text><line x1="660" y1="82" x2="660" y2="113" stroke="#1B7A80" stroke-width="1.4" marker-end="url(#ah)"/><text x="652" y="104" fill="#3D4E53" font-size="7.6" text-anchor="end">write (long-term: Maria confirms)</text></svg><div class="figcap">Figure 1. One message through HomeStretch. Search runs only for medicine questions; memory is read every turn and written after the reply.</div></div>

**Real runs** [11] on synthetic Rosa; baseline = Prompt B v4, no memory or retrieval. After the chat above, Maria asks *"I'm about to call Brighton Pharmacy. What should I ask them?"* (x/3 = runs that raised it)

| Earlier in the chat | Baseline (v4) | HomeStretch (v8 + memory) |
|---|---|---|
| Old Lopressor already bagged | calls it "still here" (wrong, 3/3) | never repeated |
| Unknown "Zorvexa" bottle | 0/3 | "What is the Zorvexa 10 mg bottle?" 3/3 |
| New furosemide not ready | 0/3 | asks when, and what until then, 3/3 |
| Doctor said lisinopril at bedtime | 0/3 | asked, against the plan's 8 AM, 2/3 |
| Ankles more swollen | 0/3 | "Call the clinic today" (her plan's warning sign) 3/3 |

*"Does the water pill make her lose potassium?"* (retrieval works here): v4: "The care plan does not say
anything about potassium. I cannot answer that." v8 (3/3): "The label says potassium supplements or diet
changes may be needed [ref-3]. Her plan does not say to add anything, so ask her clinic or pharmacist." When retrieval failed, v8 used none of it.

**Safety.** A2 suites: v8 kept every gate (911 recall 100%, 0 critical misses, 0 under-triage, i.e. never less urgent than needed); held-out 100% (v4: 98%),
stress 96% (89%), main 98%. **Blind set** (32 cases by an agent that never saw the prompts, run once): v8 = v4, 2 real
errors in 80, 0 critical, but 911 recall 95%: both sent a played-down "can't talk without stopping for air" to urgent
care. A fix (v10) did not change it; v8 sent all 18 fresh played-down emergencies to 911, so v8 stays.

## 5. Data, compliance, and risks

The class build uses synthetic data only. A parent's medicines and symptoms are likely not PHI (health data HIPAA protects) when the family adopts
the app directly [4], but just as sensitive; a hospital deployment needs BAAs (HIPAA
contracts), hosting and model providers included [5]. The FTC Health Breach Notification Rule likely applies; unauthorized sharing is a breach [6].
Washington and Nevada require opt-in consent and deletion on request; Connecticut bars selling consumer health data without consent [7–9]. DeepSeek stores data in China [10]:
real data needs a self-hosted or BAA-covered model.

**Access.** Each person sees only what their role needs:

| Who | Sees | Can do |
|---|---|---|
| Rosa (patient, account owner) | everything | invite or remove caregivers; export; delete all |
| Maria (primary caregiver, invited by Rosa) | plan, cabinet check, chat, memory | confirm, edit, or delete memory entries |
| Other family (invited) | plan and open items | read only |
| Clinic (hospital deployment only, under a BAA) | a summary Rosa chooses to share | read only |
| Model provider | one turn's prompt | nothing kept: a requirement for any real deployment (DeepSeek offers no BAA, so: self-hosted) |

Controls: a consent screen before the first upload (what is stored, where, for how long); encryption in transit and at
rest; an audit log of every view, edit, and export; every memory entry shows its source and date and can be deleted
on its own; everything is deleted at day 60 unless Rosa renews; a breach means notifying users and the FTC [6].

| Risk | Mitigation |
|---|---|
| Wrong, outdated, or invented drug facts | Name check; plan or cited, dated label only; stopped drugs only when named |
| Memory poisoning, injection, staleness | Source and date per entry; confirmed writes; documents are data, not instructions |
| Over-reliance | Never diagnose or dose; always name who to call |

**Limits:** retrieval misses 3 of 8 new questions; a borderline breathing sign can be under-triaged (blind set); replies run long; some fixes were picked after seeing results (labelled in the repo).

## References

[1] U.S. FDA, openFDA Drug Labeling API, open.fda.gov/apis/drug/label
[2] U.S. NLM, DailyMed Overview, dailymed.nlm.nih.gov/dailymed/about-dailymed.cfm
[3] U.S. NLM, RxNav news and Terms of Service, lhncbc.nlm.nih.gov/RxNav
[4] U.S. HHS, Resources for Mobile Health Apps Developers, hhs.gov/hipaa/for-professionals/special-topics/health-apps
[5] U.S. HHS, Business Associates, hhs.gov/hipaa/for-professionals/privacy/guidance/business-associates
[6] U.S. FTC, HBNR changes (2024), ftc.gov/news-events/news/press-releases/2024/04/ftc-finalizes-changes-health-breach-notification-rule
[7] Washington, RCW 19.373 (My Health My Data Act), app.leg.wa.gov/RCW/default.aspx?cite=19.373
[8] Nevada, Senate Bill 370 (2023), archive.leg.state.nv.us/Session/82nd2023/Bills/SB/SB370_EN.pdf
[9] Connecticut, Public Act 23-56, cga.ct.gov/2023/act/Pa/pdf/2023PA-00056-R00SB-00003-PA.PDF
[10] DeepSeek, Privacy Policy (Feb 10, 2026), cdn.deepseek.com/policies/en-US/deepseek-privacy-policy.html
[11] AI tools: Claude Code (research, scripts, drafting); DeepSeek deepseek-flash; bge-small-en-v1.5; ms-marco-MiniLM-L-6-v2

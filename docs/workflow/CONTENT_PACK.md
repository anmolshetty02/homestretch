# A4 content pack: everything for the final deck or doc

Pick what you need. Every number below comes from a final result folder (listed in the data sheet, §7) and was
checked on 2026-11-15. Rule used here: a problem appears only where it was fixed (§10); work not done yet is under
Next steps (§11). The brief asks for 3–5 slides with a workflow diagram, sources and AI tools cited.

---

## 1. Title and one-liner

**HomeStretch: workflow, tool use and orchestration**
Anmol Shetty · Group 5 · INFO 7375 Assignment 4 · November 2026 · github.com/anmolshetty02/homestretch

One-liner: *A caregiver's every message goes through one LangGraph pipeline: the model decides what to look up and
how urgent the message is, and fixed rules check everything it does.*

30-second version (for presenting): *When a parent comes home after a heart-failure stay, a family member suddenly
runs their medicines and watches for warning signs. HomeStretch checks the bottles at home against the discharge plan,
answers questions from the plan and the official drug labels, and says plainly when something means "call 911 now".
For this assignment it runs as one orchestrated pipeline with real tools over MCP, tested on 272 inputs across 21
synthetic patients.*

## 2. The user and the problem

Maria cares for her mother Rosa, 78, after a heart-failure discharge: three medicine changes (one new, one at a new
dose, one stopped) and a list of warning signs. What she must catch at home:

| Risk | Example |
|---|---|
| The old bottle | Stopped at discharge, still in the cabinet |
| The old dose | Refill is 20 mg once a day; the plan now says 40 mg twice a day |
| The painkiller | Advil, which the plan says to avoid |
| The warning sign | Chest tightness and gasping not recognised as an emergency |

A general chatbot answers from general knowledge; Maria needs answers from Rosa's own plan, with sources.

## 3. The workflow (required diagram)

Figures: `docs/workflow/diagram.png` (for slides), `diagram.svg` (scales without blur; in PowerPoint: Insert →
Pictures → the SVG → right-click → Convert to Shape, then every box and arrow is editable), `diagram.drawio` (open at
app.diagrams.net → File → Open from → Device; edit, then File → Export as PNG/SVG/PDF), `diagram.dot` (Graphviz source).

| Use case | Path | Pattern |
|---|---|---|
| UC1 Cabinet check | photos → Prompt A (OCR) → RxNorm name check per bottle → Prompt B compares with the plan | Plan-then-execute: steps never change |
| UC2 Question | memory → model chooses lookups ⇄ orchestrator runs them (at most 2 rounds) → Prompt B answers | ReAct: steps depend on the question |
| UC3 Red flag | Prompt B sets the urgency; tier 3 opens "Call 911 now"; emergency words skip lookups | Model triage, fixed fallback |

- **Conditional logic:** route by input type (photos vs text); emergency words skip lookups; output check fails →
  one retry with the failures listed → safe fallback (the fixed 911 text if emergency words were seen).
- **Multi-step reasoning:** the agent node chooses tools, sees results, chooses again or stops; round cap of 3 choices.
- **Context flow:** care plan → `{{care_plan}}`; session record + last turns → `{{memory}}`; label passages and name
  checks → `{{references}}` (cited `[ref-n]`, `[name-n]`); this session's bottle flags → `{{cabinet_diff}}`.
- Prompt A (A2) reads labels; Prompt B v8 (A3, unchanged) writes every reply, so any gain comes from the tools.

## 4. Tool use, ReAct and MCP

**Action vs response.** An action is a tool call the model proposes; the orchestrator runs it only if it is a listed
tool with valid input, not a repeat, and not a label search on a dose question. The response is Prompt B's reply,
which sees tool results only through its slots. Errors return to the model as observations, never crashes.

| Tool (served over MCP) | What it does | Guard |
|---|---|---|
| `check_medicine_name` | RxNorm lookup for a name not in the plan | no match → "ask the pharmacist" |
| `search_drug_label` | FDA label passages (hybrid search, reranked, top 5) | unknown names get no passages |
| `get_care_plan` | plan items by id | the orchestrator sets the patient, never the model |
| `read_label_photo` | Prompt A on a label photo | allowed folders only |
| `get_session_memory` / `update_session_memory` | session record; the write tool | write is orchestrator-only |

**MCP.** Real MCP server (`app/mcp_server.py`, MCP Python SDK 2.3, HTTP). The agent discovers the six tools at
runtime and calls them by name. Evidence: `app/test_mcp.py` runs a cabinet check and a follow-up over the server; the
official MCP Inspector (an independent client) listed and called all six tools (`docs/workflow/mcp-inspector-check.txt`);
the UI screenshots were taken with tools over MCP. The server rejects requests from other websites (DNS-rebinding
protection: foreign Host → 421, foreign Origin → 403).

## 5. Platform choice

| | LangGraph (chosen) | n8n | Plain Python loop |
|---|---|---|---|
| Branching and loops | graph edges; the graph is the diagram | visual nodes | hand-written |
| Reuse our Python checks and retrieval | direct | wrap each one | direct |
| MCP | official SDK | MCP Client Tool + MCP Server Trigger nodes | official SDK |
| Batch-test hundreds of inputs | one function, `run_turn()` | its own runner | yes |
| License | MIT | Sustainable Use License (free to self-host, not OSI open source) | n/a |

Why: our safety checks and retrieval were already Python and had to pass the same tests as A2 and A3.

## 6. The UI (Streamlit, `app/ui.py`)

Three sections, all calling the same `run_turn()`: **Today** (doses by time, morning weight, "Something feels wrong?",
open bottle problems), **Ask** (chat with starter questions), **Bottles** (camera, upload or sample labels).
Results show as pharmacy-style stickers; sources show as small tags (her plan, drug label, bottle check); each answer
has a "How this answer was made" trace with the steps and the cost. Model and tool settings sit in a sidebar.

Screenshots (real deepseek-flash replies, tools over MCP), `docs/workflow/screenshots/`, each in `_phone` and `_desktop`:

| File | Shows | Use for |
|---|---|---|
| `1_bottles_*` | 4 bottles → 4 problems as stickers (Stopped, Not on her list, Dose changed, Not picked up) | UC1 |
| `2_today_*` | Today with "Still to sort out" filled | UI overview |
| `3_ask_potassium_*` | answer citing the FDA label | UC2, tools |
| `4_ask_pharmacy_*` | follow-up built from the bottle check and the earlier question | memory |
| `5_red_flag_*` | red "Call 911 now" alert | UC3 |

More screenshots (one real deepseek-flash run, tools over MCP, 2026-11-15), `docs/workflow/screenshots/more/`:

| File | Shows | Best for |
|---|---|---|
| `01_today_start` | home screen before anything happens | UI overview |
| `02_sidebar_mcp` | sidebar: deepseek-flash, tools = mcp, "MCP server: 6 tools discovered" | MCP |
| `03_today_when_to_call` | the plan's warning signs by urgency, with phone numbers | UC3 context |
| `04_bottles_empty` | Bottles before any photo | UC1 |
| `05_bottles_samples_picked` | four label photos chosen | UC1 input |
| `06_bottles_result` | "I found 4 things, most urgent first" + stickers | UC1 output |
| `07_bottles_trace` | steps: read_photos (Prompt A) → check_names (RxNorm) → answer → output_check → save | workflow, plan-then-execute |
| `08_today_still_to_sort_out` | the 4 open bottle problems on Today | memory, UI |
| `09_weight_logged` / `10_weight_warning` | 182 lb logged; 185.5 lb → "Up 3.5 lb, call the clinic today" | daily use |
| `11_ask_starters` | Ask with starter questions | UC2 |
| `12_ask_potassium` / `13_ask_potassium_trace` | label answer; trace shows the model calling `search_drug_label`, then "done" | ReAct, tool calling |
| `14_ask_advil` | uses the bottle check from memory ("the Advil bottle is still in the cabinet") | memory |
| `15_ask_benadryl_name_check` | RxNorm name check: Benadryl is diphenhydramine | tool calling |
| `16_ask_unknown_medicine` | made-up name: "unknown medicine, do not guess" | safe tool result |
| `17_ask_missed_dose` | "do not double up", from the plan, no label search | dose rule |
| `18_ask_pharmacy_memory` | follow-up built from the bottle check | memory |
| `19_wrong_dizzy_call_clinic` | "Call the clinic today" (tier 1) | UC3 |
| `20_wrong_chest_911` / `21_wrong_chest_trace_no_lookups` | "Call 911 now"; trace shows "lookups skipped: possible emergency" | UC3, conditional logic |
| `22_sidebar_session_memory` | the structured session record (open flags, pending questions) | memory |
| `23_desktop_today` / `24_desktop_ask` | full desktop views after the whole session | overview |

## 7. Data sheet: every number and where it comes from

Model deepseek-flash, thinking off, temperature 0.3, one run per set, final code (2026-11-15). Run folders are under
`results/`. "v8 alone" = the A3 single prompt = the no-tools baseline (the pipeline sends it the identical prompt).

| Number | Value | Source |
|---|---|---|
| Main cases pass (57) | v8 56, pipeline 56 | `v8_deepseek-flash_t0.3_1101-1727`, `pipeline-gateoff_deepseek-flash_1115-1321` |
| Confirm set pass (54) | v8 51, pipeline 52 | `v8_..._1101-1932_confirm_confirm`, `pipeline-..._1115-1323_confirm` |
| A4 held-out, fresh agent (59) | v8 59, pipeline 59 | `v8_..._1114-1023_a4_heldout`, `pipeline-..._1115-1325_a4_heldout` |
| A4 triage, second fresh agent (52) | v8 51, pipeline 51 | `v8_..._1114-1047_a4_triage`, `pipeline-..._1115-1327_a4_triage` |
| 20 other patients, A2 Synthea held-out (50) | v8 50, pipeline 50 | `v8_..._1115-1319_heldout`, `pipeline-..._1115-1319_heldout` |
| Total test inputs | 272 (222 on Rosa + 50 on 20 other patients) | the five pipeline folders |
| Patients | 21 synthetic (Rosa + 20 Synthea, aged 51–86, 3–11 medicines) | `fixtures/` |
| Emergencies answered "Call 911 now" | 69 / 69 (222 Rosa inputs); 6 / 6 (other patients) | pipeline folders |
| Tool choice as expected | 31 / 31 (held-out inputs that set a tool expectation) | `..._1115-1325_a4_heldout` |
| Label searches on dose questions blocked | 4 / 4 | the four Rosa pipeline folders (trace step "tools", "blocked") |
| Label questions answered from a cited FDA label | pipeline 4 of 7, v8 0 of 7 | `..._1115-1325_a4_heldout` |
| Unfamiliar names answered with RxNorm | 9 / 9 | `..._1115-1325_a4_heldout` |
| Advil question cites the label (other patients) | pipeline 4 of 6, v8 0 of 6 | `..._1115-1319_heldout` |
| Output-check retries / fallbacks | 0 / 0 in 222 turns | pipeline folders |
| Cost per turn | pipeline $0.0007, v8 $0.0003 (2.2×) | mean `cost_usd` over the four Rosa sets |
| Latency, median (95th percentile) | pipeline 2.7 s (5.1 s), v8 1.7 s | uncached turns |
| Usefulness, replies that cite a lookup (31) | pipeline more useful 22, v8 4, tie 5 | `usefulness_deepseek-flash_1115-1350` |
| Usefulness, all lookup turns (115) | pipeline 33, v8 14, tie 68 | same |
| 911 rule experiment (26 emergencies, 26 traps) | word rule first: 26/26, 9 false · adds-if-missing: 26/26, 1 · Prompt B alone: 26/26, 1 | `pipeline_deepseek-flash_1114-1029_a4_triage` (word rule first), `pipeline-gatebackstop_..._1114-1032_a4_triage`, `pipeline-gateoff_..._1114-1034_a4_triage` (README §3b) |
| Code change check | Rosa's 395 model inputs byte-identical before/after the patient became a parameter | README §4 |
| Total A4 model spend | about $0.52 | `results/spend.csv` |

How to read pass rates: one run per set, so a one-case difference is within noise; the pipeline's gain is shown by
the usefulness judge, not by pass rates.

## 8. Results, in words

- **Safety held everywhere.** All 69 emergencies on Rosa and all 6 on the other patients got "Call 911 now"; no
  retries or fallbacks were needed.
- **Tools make answers more useful when they find something.** A blind pairwise judge (each pair judged in both
  orders) preferred the pipeline 22 to 4 on replies that cite a lookup. Examples: "The label says cough is a common
  lisinopril reaction"; "NSAIDs like ibuprofen can raise the risk of heart failure and stomach bleeding"; "Kapspargo
  contains metoprolol".
- **It works beyond one patient.** 50 of 50 on 20 other synthetic patients, aged 51 to 86.
- **Cost:** $0.0007 per message, 2.7 s median, about twice the single prompt.

## 9. The 911 rule: decided by data (a problem we fixed)

A fixed word rule answered "Call 911 now" before any model call. It fired on "**no** chest pain" and "nearly
**fainted** finding parking". We wrote the decision rule first, then ran three variants once on a fresh triage set:

| Variant | Emergencies caught | False "Call 911 now" |
|---|---|---|
| Word rule answers first | 26 / 26 | 9 |
| Word rule adds a 911 line only if missing | 26 / 26 | 1 |
| **Prompt B triages alone (chosen)** | 26 / 26 | 1 |

The rule caught nothing the model missed, so triage moved to the model; the word rule now only skips lookups and
picks the fallback text.

## 10. Challenges and how each was fixed

| Area (brief's category) | What happened | Fix |
|---|---|---|
| Context management | Tools called in-process silently used the mock model | The orchestrator passes the model through |
| Context management | The checker rejected this session's own flag ids, so a safe reply became the fallback | Session flag ids count as valid |
| Context management | Past turns in a short JSON shape were copied by the model | Recent turns go in the `{{memory}}` slot (A3 design) |
| Context management | Rosa was built into three files, so no other patient could be tested | The patient is a parameter; the orchestrator sets it; Rosa's inputs stayed byte-identical; 20 more patients tested |
| Tool integration | MCP SDK v2 renamed its APIs; errors came back wrapped | Typed wrappers, readable errors, `app/test_mcp.py` |
| Tool integration | RxNorm keeps "Toprol XL" under a retired id, so a real medicine looked unknown | Retry on the base name; "ingredients unknown" passed on with its note |
| Orchestration logic | The fixed 911 word rule gave 9 false alarms | Decided by a preregistered experiment (§9) |
| Orchestration logic | 32 of 69 emergencies ran a lookup before the 911 reply | Emergency words now skip lookups (22 still run one; 1.3 s vs 3.2 s median) |
| Orchestration logic | The dose block also caught "extra pillows" | Rule narrowed to extra dose/pill/tablet |
| Orchestration logic | The round cap dropped calls silently | Visible in the trace |
| Reliability | Building the label index took 106 s | Vectors cached (about 1 s) |
| Reliability (UI) | Sample labels with the same name hid each other, so "Dose changed" never showed | Each sample named with its directions; test added |
| Reliability (UI) | Raw ids like `[flag-1]` showed to the caregiver | Shown as small source tags; ids kept in the trace |

## 11. Next steps

1. Add openFDA labels for the remaining medicines across the 21 patients (simvastatin, carvedilol, clopidogrel,
   losartan, and others), so more questions can be answered from a label.
2. A tool-prompt v2 that runs label search only when the care plan does not already answer the message.
3. More questions for the other patients, written by a fresh agent.
4. An installable phone app with saved check-offs, weights and reminders.
5. Other conditions beyond heart failure.

## 12. Sources, data and AI tools

1. Yao et al., ReAct: Synergizing Reasoning and Acting in Language Models, https://arxiv.org/abs/2210.03629
2. Model Context Protocol, https://modelcontextprotocol.io; MCP Python SDK, https://github.com/modelcontextprotocol/python-sdk; MCP Inspector, https://github.com/modelcontextprotocol/inspector
3. LangGraph, https://docs.langchain.com/oss/python/langgraph/overview
4. NIH RxNav (RxNorm), https://lhncbc.nlm.nih.gov/RxNav/; openFDA drug labels, https://open.fda.gov
5. DeepSeek API, https://api-docs.deepseek.com; Streamlit, https://streamlit.io; Tesseract OCR, https://github.com/tesseract-ocr/tesseract; fastembed, https://github.com/qdrant/fastembed (BAAI bge-base-en-v1.5, ms-marco MiniLM cross-encoder)
6. n8n MCP Client Tool, https://docs.n8n.io/integrations/builtin/cluster-nodes/sub-nodes/n8n-nodes-langchain.toolmcp/; MCP Server Trigger, https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-langchain.mcptrigger/
7. n8n Sustainable Use License, https://github.com/n8n-io/n8n/blob/master/LICENSE.md
8. Synthea synthetic patients, https://synthetichealth.github.io/synthea/
9. INFO 7375 Module 8 (Tool Calling, MCP, ReAct, Agent Layer); ComplaintIQ Tool Use and Orchestration lab

**Data:** 21 synthetic patients (Rosa and 20 generated with Synthea) and synthetic label images; no real patient data.
**AI tools:** Claude Code (Claude Opus 5.5) wrote most of the code and drafts, with Anmol reviewing each step;
DeepSeek deepseek-flash is the app's model and the usefulness judge.

## 13. Suggested 5-slide order (with speaker notes)

1. **One message, one pipeline, three use cases.** Diagram + the §3 table. *Notes:* conditional logic, context flow, Prompt B unchanged.
2. **What Maria sees.** Three phone screenshots (bottles, potassium, red flag). *Notes:* first use, daily use, when something comes up.
3. **The model proposes, the orchestrator decides.** §4 tools table + 31/31, 4/4, 6 tools over MCP. *Notes:* action vs response; MCP Inspector.
4. **LangGraph, and what the tools added.** §5 table + 69/69, 22 vs 4 usefulness, 50/50 on 20 other patients. *Notes:* pass rates equal; the gain is in the answers; cost.
5. **Decided by data, fixed by tests.** §9 table + three rows of §10 + sources. *Notes:* the experiment, the challenges, next steps.

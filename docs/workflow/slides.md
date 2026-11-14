# A4 slide content (5 slides; trim to taste)

Rule for the deck (A3 peer feedback: "too many numbers, hard to follow"): one headline per slide, at most about 3
numbers on the slide, everything else in the speaker notes. Every number below is from the final runs listed in
`docs/workflow/README.md` §4. If a number changes, change it there first.

---

## Slide 1 — The workflow: one pipeline, three use cases

**Headline:** Every caregiver message goes through one LangGraph pipeline. The model decides what to look up and how
urgent the message is; fixed rules check everything it does.

**Visual:** the workflow diagram (README §1, Mermaid; render at https://mermaid.live or screenshot it). Color three
paths by use case:
- **UC1 Cabinet check** (photos → Prompt A OCR → RxNorm name check → Prompt B diff)
- **UC2 Question** (memory → ReAct: choose lookups ⇄ run them → Prompt B answer)
- **UC3 Red flag** (Prompt B triage → "Call 911 now" + red banner; a possible emergency skips lookups)
- Shared tail: output check → one retry → safe fallback → save memory

**On the slide (3 bullets max):**
- Plan-then-execute where steps never change (cabinet check); ReAct where they depend on the question
- Conditional logic: route by input type; skip lookups on emergency words; retry, then fall back, on a failed check
- Context flow: care plan, memory, and tool results each fill their own slot in Prompt B v8 (unchanged since A3)

**Speaker notes:** Prompt A = label photo → name/strength/directions (A2). Prompt B v8 = the A3 assistant, now fed by
tools. Max 3 tool choices per turn (circuit breaker); duplicate calls refused; unknown tools refused.

---

## Slide 2 — Tool use and MCP: the model proposes, the orchestrator decides

**Headline:** The model chooses lookups; the orchestrator validates every call, so a wrong choice cannot reach the
caregiver.

**Visual:** a small table of the 6 tools (read/write) with a "served over MCP" bracket:
check_medicine_name (RxNorm) · search_drug_label (FDA labels, hybrid search + rerank) · get_care_plan ·
read_label_photo (Prompt A) · get_session_memory · update_session_memory (WRITE: orchestrator only).

**On the slide:**
- On a held-out set written by a fresh agent, the model picked the right tools **31/31** times
- It asked for a label search on a dose question **4** times, and the orchestrator blocked all 4
- Tools are served by a real MCP server (mcp 2.3, HTTP): the agent discovers them at runtime and calls them by name

**Speaker notes:** Hybrid invocation (Module 8): deterministic checks (allowed tool, valid JSON, dose block, no
repeats) on top of model-driven choice. Errors go back to the model as observations, never as crashes. MCP lets the
tools change without touching the agent; `app/test_mcp.py` runs a cabinet check and a follow-up over the server.

---

## Slide 3 — Platform choice: LangGraph over n8n and a plain loop

**Headline:** We chose LangGraph because our safety checks and retrieval already exist as Python and must be scored by
the same tests as A2/A3.

**Visual:** the comparison table from README §3, cut to 4 rows:

| | LangGraph ✓ | n8n | Plain Python loop |
|---|---|---|---|
| Conditional logic and loops | graph edges, the graph is the diagram | visual nodes | hand-written |
| Reuse our Python checks and retrieval | direct | wrap each one | direct |
| MCP | official SDK | MCP client/server nodes | official SDK |
| Batch-test 222 inputs | one function | its own runner | yes |

**Speaker notes:** n8n would be easier for non-programmers to edit, but every check would need rewriting or wrapping.
The plain loop (the ComplaintIQ lab) works but makes branching implicit. License: LangGraph MIT; n8n Sustainable Use
License (free to self-host, not OSI open source).

---

## Slide 4 — Results: same safety as the single prompt, plus grounded answers

**Headline:** The pipeline keeps every safety result and answers questions the single prompt could only defer.

**On the slide (3 numbers):**
- **69/69** emergencies answered "Call 911 now" across 222 test inputs (4 sets, 2 written by fresh agents)
- On drug-label questions, **4 of 7** answered from a cited FDA label (single prompt: 0 of 7, always "ask the pharmacist")
- **$0.0007** per turn, 2.6 s median (about 2× the single prompt's cost and 1 s slower)

**Visual (optional):** one before/after quote:
- Single prompt: "That is not in her plan, so I cannot say. Ask her pharmacist."
- Pipeline: "The label says cough is a common lisinopril reaction [ref-1]. I can't say if that's her cause. Call the
  clinic to report it."

**Speaker notes:** Pass rates match the single prompt on all 4 sets (56/57, 52/54, 59/59, 51/52); the +1 from tools is
within one run's noise, so we don't claim it. The real gain is in the replies: label citations, and all 9 unfamiliar
names answered with an RxNorm result. Output check: 0 retries in 222 turns (it caught 2 bad replies in the multi-turn
smoke test).

---

## Slide 5 — What we learned: challenges and limits

**Headline:** Our biggest design change came from data: a fixed 911 word rule looked safe, and tests showed it wasn't
needed and caused harm.

**On the slide:**
- The word rule sent "Call 911 now" for "**no** chest pain" and "nearly **fainted** finding parking". On a fresh
  triage set it caught nothing extra (26/26 either way) and gave **9** false alarms, so we removed it, using a
  decision rule written before the test
- Context bugs were the real bugs: the model choice didn't reach the tools, the checker rejected this session's own
  flags, and a short history format got copied by the model. All three were caught by tests
- Limits: retrieval can pull a reply off-topic; 23 of 69 emergencies phrased without keywords still run a lookup
  first (+2 s); one synthetic patient

**Speaker notes:** The process mattered as much as the result. We froze the code before final runs, had two held-out
sets written by fresh agents and run once, ran an independent review that recomputed every number, and fixed what it
found (lookups on emergencies, a misread RxNorm result, "extra pillows" blocked as a dose question). Full list:
README §4.

---

## Sources and AI tools (last slide footer or a notes page)

Module 8 slides; ComplaintIQ Tool Use & Orchestration lab; Yao et al., ReAct (arXiv 2210.03629); Model Context
Protocol (modelcontextprotocol.io) and MCP Python SDK; LangGraph docs; n8n docs (MCP Client Tool, MCP Server
Trigger) and LICENSE; NIH RxNav; openFDA drug labels; DeepSeek API; Streamlit; Tesseract OCR; fastembed with BAAI
bge-base-en-v1.5 and the ms-marco MiniLM cross-encoder. AI tools: Claude Code (Claude Opus 5.5) wrote most of the code
and drafts, with Anmol reviewing each step; DeepSeek `deepseek-flash` is the app's model. Full URLs: README "Sources".

## Screenshots to take (UI, `streamlit run app/ui.py`, model deepseek-flash)

1. Chat: "Does the water pill make her lose potassium?" with the "How this answer was made" trace open (tool calls
   and cost visible). Use for slide 2.
2. Red flag: "Mom says her chest feels tight and she's gasping." (red banner). Use for slide 1 or 4.
3. Cabinet check with 2–3 sample labels selected, showing the flag table. Use for slide 1.

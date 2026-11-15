"""HomeStretch workflow (Assignment 4, Part 2) as one LangGraph pipeline.

  caregiver input
   -> route: photos or cabinet? ----yes--> read_photos -> check_names -> answer (Prompt B v8, diff mode)
                                ----no---> load_memory -> agent <-> tools (ReAct, max 3 choices) -> answer (chat mode)
                                           (possible emergency: load_memory -> answer, no lookups)
   answer -> output_check --fail, 1st time--> answer (retry with the failed checks)
                          --fail again------> fallback_reply
                          --pass------------> safety_backstop (no-op unless gate=backstop) -> save_memory -> END

Prompt B v8 does the 911 triage. The fixed word rule (in route) is OFF by default: on a fresh triage set it
added no recall over v8 (26/26 for every variant) and answered 9 non-emergencies with "Call 911 now"
(docs/workflow/README.md, section 3b). gate="keep" or "backstop" reproduces that experiment.
Fixed rules still own the other safety-critical steps (blocked lookups, the output check, the fallback); the model
decides which lookups an open question needs. Tools are reached through app/tool_client.py (MCP or in-process).
"""
import functools
import json
import re
from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from app import llm
from app import tool_client as tc
from app.tools import ROOT, load_patient
from evals.checks import run_checks
from evals.run import NO_DIFF, build_messages, collect_ids, render

AGENT_PROMPT = (ROOT / "prompts" / "agent_v8.md").read_text()
TOOLS_TEMPLATE = (ROOT / "prompts" / "tools_v1.md").read_text()
QUESTION_TOOLS = ["check_medicine_name", "search_drug_label", "get_care_plan"]
MAX_ROUNDS = 3       # tool-choice calls per turn, so at most 2 rounds of tools run (circuit breaker)
MAX_ATTEMPTS = 2     # Prompt B attempts before the fallback reply


@functools.lru_cache(maxsize=None)
def patient_context(patient="p001"):
    """What the graph derives from one patient: the fixture, the tool prompt's plan names, the ids a reply may cite,
    and the contacts for the fallback reply. p001 (Rosa) is the app; synthea/sNN are the A2 held-out patients."""
    fx = load_patient(patient)
    names = ", ".join(f"{m['name']} ({m.get('plain_name', '')}; {', '.join(m.get('brands', []))})"
                      for m in fx["care_plan"]["medications"])
    return {"fixture": fx, "tools_prompt": TOOLS_TEMPLATE.replace("{{plan_names}}", names), "ids": collect_ids(fx),
            "contacts": {c["id"]: c for c in fx["care_plan"]["contacts"]}}


FIXTURE_IDS = patient_context()["ids"]  # Rosa's; kept for older imports

# Fixed before looking at any test case; mirrors the plan's tier-3 sign (warn-6) and Prompt B's tier-3 list.
EMERGENCY = re.compile(
    r"chest (pain|hurts?|pressure|is tight|feels tight)|pain in (her|his|my) chest|can'?t breathe|cannot breathe"
    r"|struggling to breathe|gasping|barely (breathe|breathing|talk)|faint(ed|ing)|passed out|pink (foamy )?(mucus|spit|foam)"
    r"|(sudden(ly)?|very|is|seems|really) confused|slurr|face (is )?droop|one side|won'?t wake|hard to wake|unresponsive", re.I)
# A3 router (design.md §A): dose questions never go to label search.
DOSE = re.compile(r"\bdose|missed|forgot|skip|double|catch up|how much|maximum|stop (taking|it)"
                  r"|extra (dose|pill|tablet|one)s?\b|split", re.I)  # "extra" alone matched "extra pillows" (review)


class State(TypedDict, total=False):
    session_id: str
    patient: str           # fixture name, default p001 (Rosa)
    message: str
    cabinet: list          # cabinet items given directly ({id, name, strength, directions})
    photos: list           # label image paths, read with Prompt A
    history: list          # earlier turns; defaults to the session's saved turns
    model: str
    save: bool             # write the session record (the eval turns this off)
    use_tools: bool        # False = ablation: skip the ReAct lookups, everything else unchanged
    gate: str              # 911 rule: "keep" (short-circuit), "backstop" (append 911 if the reply lacks it), "off"
    tier3_phrase: str      # what the fixed rule matched, or "" 
    mode: str              # "diff" or "chat"
    memory: dict
    tool_msgs: list
    rounds: int
    references: list       # label passages and name checks that go into {{references}}
    attempts: int
    reply: dict            # Prompt B's JSON
    failed: list
    final: dict            # what the caregiver sees: reply text, tier, flags, sources
    trace: list            # one row per step, for the UI and the logs


def step(state, name, detail):
    return state.get("trace", []) + [{"step": name, "detail": detail}]


# ----------------------------------------------------------------------------------------------- nodes

def route(s):
    """Routes every turn (photos or cabinet -> cabinet branch, text -> question branch) and notes any tier-3 phrase.
    The phrase never decides the tier on its own (gate=off, docs/workflow/README.md 3b); it only skips lookups, so a
    possible emergency is answered without delay, and it keeps the fallback reply pointing at 911."""
    hit = EMERGENCY.search(s["message"] or "")
    return {"trace": step(s, "route", f"tier-3 phrase {hit.group(0)!r} (gate={s.get('gate', 'off')})"
                                       if hit else "no tier-3 phrase"),
            "tier3_phrase": hit.group(0) if hit else "", "mode": "diff" if s.get("cabinet") or s.get("photos") else "chat"}


def emergency_reply(s):
    reply = ("Call 911 now. Chest pain, severe trouble breathing, fainting, or sudden confusion is an emergency sign "
             "in the care plan [warn-6]. Stay with them until help arrives.")
    final = {"reply": reply, "red_flag_tier": 3, "sources": ["warn-6"], "flags": [], "mode": "chat", "by": "fixed rule"}
    return {"final": final, "trace": step(s, "emergency_reply", "fixed 911 reply, no model call")}


def read_photos(s):
    items = list(s.get("cabinet") or [])
    for n, path in enumerate(s.get("photos") or [], len(items) + 1):
        out = tc.call_tool("read_label_photo", {"path": path}, s["model"])
        item = {"id": f"cab-{n}", **({k: out.get(k, "unreadable") for k in ("name", "strength", "directions")}
                                     if "error" not in out else {"name": "unreadable", "strength": "unreadable",
                                                                 "directions": "unreadable"})}
        items.append(item)
    return {"cabinet": items, "trace": step(s, "read_photos", f"{len(s.get('photos') or [])} photos read with Prompt A")}


def check_names(s):
    items, notes = [], []
    for item in s["cabinet"]:
        name = str(item.get("name", ""))
        if not name or name.lower() == "unreadable":
            items.append(item)
            continue
        out = tc.call_tool("check_medicine_name", {"name": name})
        if "error" in out or out.get("status") == "no_match":
            item = {**item, "name_check": "not found in RxNorm: unknown medicine, pharmacist_check"}
            notes.append(f"{item['id']} {name}: {'unchecked' if 'error' in out else 'no match'}")
        items.append(item)
    return {"cabinet": items, "trace": step(s, "check_names", f"RxNorm on {len(items)} items; flagged: {notes or 'none'}")}


def _has_record(mem):
    return any((mem.get("record") or {}).values())


def load_memory(s):
    mem = tc.call_tool("get_session_memory", {"session_id": s["session_id"]})
    if "error" in mem:
        mem = {"record": None, "cabinet_diff": None, "turns": []}
    msgs = [{"role": "system", "content": patient_context(s["patient"])["tools_prompt"]},
            {"role": "user", "content": s["message"]}]
    skip = "; lookups skipped: possible emergency" if s.get("tier3_phrase") and s.get("use_tools", True) else ""
    return {"memory": mem, "tool_msgs": msgs, "rounds": 0, "references": [],
            "trace": step(s, "load_memory", f"{len(mem['turns'])} saved turns; record "
                                            f"{'present' if _has_record(mem) else 'empty'}{skip}")}


def agent(s):
    """ReAct step: the model reasons over the question and the results so far, then calls tools or says done."""
    msg = llm.choose_tools(s["tool_msgs"], tc.openai_tools(QUESTION_TOOLS), s["model"])
    if "error" in msg:  # the model call failed: answer from the care plan alone
        msg = {"content": "done", "tool_calls": []}
    calls = msg.get("tool_calls") or []
    detail = ", ".join(f"{c['function']['name']}({c['function']['arguments']})" for c in calls) or "done"
    if calls and s["rounds"] + 1 >= MAX_ROUNDS:  # circuit breaker: answer with what we have
        detail, calls, msg = f"{detail}: not run (round cap {MAX_ROUNDS})", [], {"content": "done"}
    return {"tool_msgs": s["tool_msgs"] + [{"role": "assistant", "content": msg.get("content") or "", "tool_calls": calls}
                                           if calls else {"role": "assistant", "content": msg.get("content") or "done"}],
            "rounds": s["rounds"] + 1, "trace": step(s, f"agent round {s['rounds'] + 1}", detail)}


def tools(s):
    """Run the requested tools after the orchestrator's checks: allowed tool, no label search on dose questions,
    no repeated call. Every result (or refusal) goes back to the model as an observation."""
    msgs, refs, notes = list(s["tool_msgs"]), list(s["references"]), []
    done = set()
    for m in msgs[:-1]:  # calls already made in earlier rounds
        for c in m.get("tool_calls") or []:
            try:
                done.add((c["function"]["name"], json.dumps(json.loads(c["function"]["arguments"] or "{}"), sort_keys=True)))
            except json.JSONDecodeError:
                pass
    for call in msgs[-1]["tool_calls"]:
        name, raw = call["function"]["name"], call["function"]["arguments"]
        try:
            args = json.loads(raw or "{}")
        except json.JSONDecodeError:
            args = None
        if name not in QUESTION_TOOLS:
            out = {"error": f"{name} is not available here. Use one of {QUESTION_TOOLS}."}
        elif args is None:
            out = {"error": "arguments were not valid JSON"}
        elif name == "search_drug_label" and DOSE.search(s["message"]):
            out = {"error": "blocked: label search is not used for dose questions, the care plan or the pharmacist answers those"}
        elif (name, json.dumps(args, sort_keys=True)) in done:
            out = {"error": "duplicate call: you already have this result"}
        else:
            done.add((name, json.dumps(args, sort_keys=True)))
            if name == "get_care_plan":  # the orchestrator, never the model, says whose plan it is
                args = {**args, "patient": s["patient"]}
            out = tc.call_tool(name, args)
            if name == "search_drug_label":
                refs += [r for r in out.get("references", []) if r["text"] not in {x.get("text") for x in refs}]
            if name == "check_medicine_name" and "error" not in out:
                ingr = ", ".join(out.get("ingredients") or []) or "unknown (RxNorm knows the name but not its ingredients)"
                refs.append({"kind": "name", "text": f"{out['name']}: RxNorm {out['status']}"
                             + (f", ingredients: {ingr}" if out["status"] == "matched"
                                else " (unknown medicine: do not guess, check with the pharmacist)")})
        notes.append(f"{name}: {'error: ' + out['error'] if 'error' in out else 'ok'}")
        brief = out if name != "search_drug_label" or "error" in out else \
            {"found": [f"{r['drug']} / {r['section']}" for r in out.get("references", [])], "note": out.get("note")}
        msgs.append({"role": "tool", "tool_call_id": call["id"], "content": json.dumps(brief)[:1500]})
    return {"tool_msgs": msgs, "references": refs, "trace": step(s, "tools", "; ".join(notes))}


def _references_xml(refs):
    out = []
    for n, r in enumerate(refs, 1):
        if r.get("kind") == "name":
            out.append(f'<ref id="name-{n}" source="RxNorm name check">{r["text"]}</ref>')
        else:
            out.append(f'<ref id="ref-{n}" drug="{r["drug"]}" source="{r["source"]}" section="{r["section"]}" '
                       f'set_id="{r["set_id"]}" date="{r["date"]}">{r["text"]}</ref>')
    return "<references>" + ("\n".join(out) or "none") + "</references>", \
        {f"{'name' if r.get('kind') == 'name' else 'ref'}-{n}" for n, r in enumerate(refs, 1)}


def _prompt_and_messages(s):
    refs_xml, _ = _references_xml(s.get("references", []))
    mem = s.get("memory") or {}
    template = AGENT_PROMPT.replace("{{references}}", refs_xml)
    if _has_record(mem) or mem.get("turns"):  # A3 memory design: record + recent turns go in the memory slot
        recent = [f"Caregiver: {t['user']} / HomeStretch: {t['assistant']}" for t in mem.get("turns", [])[-2:]]
        template = template.replace("{{memory}}", json.dumps({"session_record": mem["record"], "recent_turns": recent}))
    if s["mode"] == "chat" and mem.get("cabinet_diff"):
        template = template.replace("{{cabinet_diff}}", json.dumps(mem["cabinet_diff"]))
    case = {"cabinet": s["cabinet"]} if s["mode"] == "diff" else {}
    system = render(template, patient_context(s["patient"])["fixture"], case)
    assert refs_xml in system, "references did not reach the prompt"  # A3 lesson: assert inputs reach the model
    history = s.get("history") or []  # eval cases bring their own history; app sessions use the memory slot
    user_text = json.dumps(s["cabinet"]) if s["mode"] == "diff" else s["message"]
    return build_messages(system, {"history": history}, user_text), case, user_text


def answer(s):
    messages, _, _ = _prompt_and_messages(s)
    attempt = s.get("attempts", 0) + 1
    if attempt > 1:  # retry: show the model its own reply and the checks it failed
        messages += [{"role": "assistant", "content": json.dumps(s["reply"])},
                     {"role": "user", "content": "Your reply failed these checks: " + "; ".join(s["failed"])
                      + ". Write the whole JSON reply again, fixing them and following every rule."}]
    reply = llm.complete_json(messages, s["model"], purpose="answer", repeat=attempt - 1)
    return {"reply": reply, "attempts": attempt,
            "trace": step(s, f"answer attempt {attempt}", f"Prompt B v8, {s['mode']} mode, "
                                                          f"{len(s.get('references', []))} references")}


def output_check(s):
    _, case, user_text = _prompt_and_messages(s)
    _, ref_ids = _references_xml(s.get("references", []))
    reply = s["reply"] if "error" not in s["reply"] else None
    diff = (s.get("memory") or {}).get("cabinet_diff") or [] if s["mode"] == "chat" else []
    session_ids = {f.get("id") for f in diff if isinstance(f, dict)}  # this session's cabinet-check flags
    checks = run_checks(reply, case, patient_context(s["patient"])["ids"] | ref_ids | session_ids, user_text)
    failed = [f"{k}: {d}" for k, (st, d) in checks.items() if st == "fail"]
    return {"failed": failed, "trace": step(s, "output_check", "pass" if not failed else f"fail: {failed}")}


def fallback_reply(s):
    """No safe model reply. On a possible emergency the fixed 911 reply comes first, since no model answered it."""
    if s.get("tier3_phrase"):
        out = emergency_reply(s)
        out["final"]["by"] = "fallback (possible emergency)"
        out["trace"][-1] = {"step": "fallback_reply", "detail": f"after {s['attempts']} failed attempts; fixed 911 reply"}
        return out
    contacts = patient_context(s["patient"])["contacts"]
    ph, cl = contacts["contact-2"], contacts["contact-1"]
    reply = (f"I can't answer that safely right now. Please call {ph['name']} at {ph['phone']} or "
             f"{cl['name']} at {cl['phone']}. If this is an emergency, call 911.")
    final = {"reply": reply, "red_flag_tier": None, "sources": ["contact-1", "contact-2"], "flags": [], "mode": s["mode"],
             "by": "fallback"}
    return {"final": final, "trace": step(s, "fallback_reply", f"after {s['attempts']} failed attempts")}


def safety_backstop(s):
    """gate=backstop: Prompt B triages; the fixed rule only adds the 911 line when a tier-3 phrase is present and the
    reply never mentions 911. It can add a sentence but never replace a correct reply."""
    if s.get("gate") != "backstop" or not s.get("tier3_phrase") or "911" in str(s["reply"].get("reply", "")):
        return {"trace": step(s, "safety_backstop", "no change")}
    r = dict(s["reply"])
    r["reply"] = (str(r.get("reply") or "") + " If she has chest pain, severe trouble breathing, fainting, or sudden "
                  "confusion right now, call 911 [warn-6].").strip()
    r["sources"] = list(r.get("sources") or []) + ["warn-6"]
    return {"reply": r, "trace": step(s, "safety_backstop", f"added 911 line ({s['tier3_phrase']!r}, reply had no 911)")}


def save_memory(s):
    r = s["reply"]
    final = {k: r.get(k) for k in ("reply", "red_flag_tier", "sources", "flags", "mode")} | {"by": "Prompt B v8"}
    if not s.get("save", True):
        return {"final": final, "trace": step(s, "save_memory", "skipped (eval run)")}
    args = {"session_id": s["session_id"], "message": s["message"] or "(cabinet check)", "reply": r.get("reply") or "",
            "patient": s["patient"]}
    if s["mode"] == "diff":
        args["cabinet_diff"] = r.get("flags") or []
    out = tc.call_tool("update_session_memory", args, s["model"])
    return {"final": final, "trace": step(s, "save_memory", "saved" if "error" not in out else out["error"])}


# ----------------------------------------------------------------------------------------------- edges

def after_route(s):
    if s.get("tier3_phrase") and s.get("gate", "off") == "keep":
        return "emergency_reply"
    return "read_photos" if s["mode"] == "diff" else "load_memory"


def after_memory(s):
    """Lookups only for ordinary questions: never when tools are off (ablation) or the message may be an emergency."""
    return "agent" if s.get("use_tools", True) and not s.get("tier3_phrase") else "answer"


def after_agent(s):
    last = s["tool_msgs"][-1]
    return "tools" if last.get("tool_calls") and s["rounds"] < MAX_ROUNDS else "answer"


def after_check(s):
    if not s["failed"]:
        return "safety_backstop"
    return "answer" if s["attempts"] < MAX_ATTEMPTS else "fallback_reply"



def build():
    g = StateGraph(State)
    for fn in (route, emergency_reply, read_photos, check_names, load_memory, agent, tools, answer,
               output_check, fallback_reply, safety_backstop, save_memory):
        g.add_node(fn.__name__, fn)
    g.add_edge(START, "route")
    g.add_conditional_edges("route", after_route, ["emergency_reply", "read_photos", "load_memory"])
    g.add_edge("read_photos", "check_names")
    g.add_edge("check_names", "answer")
    g.add_conditional_edges("load_memory", after_memory, ["agent", "answer"])
    g.add_conditional_edges("agent", after_agent, ["tools", "answer"])
    g.add_edge("tools", "agent")
    g.add_edge("answer", "output_check")
    g.add_conditional_edges("output_check", after_check, ["answer", "fallback_reply", "safety_backstop"])
    g.add_edge("safety_backstop", "save_memory")
    for end in ("emergency_reply", "fallback_reply", "save_memory"):
        g.add_edge(end, END)
    return g.compile()


GRAPH = build()


def run_turn(session_id, message="", cabinet=None, photos=None, model="mock", history=None, save=True, use_tools=True,
             gate="off", patient="p001"):
    """The one entry point for the UI and the evals. Returns {final, trace, usage}."""
    start = len(llm.USAGE)
    patient_context(patient)  # unknown patient -> ValueError here, before any model call
    state = {"session_id": session_id, "patient": patient, "message": message, "cabinet": cabinet, "photos": photos, "model": model,
             "save": save, "use_tools": use_tools, "gate": gate, "trace": []}
    if history is not None:
        state["history"] = history
    out = GRAPH.invoke(state, {"recursion_limit": 25})
    return {"final": out["final"], "trace": out["trace"], "usage": llm.USAGE[start:],
            "ref_ids": sorted(_references_xml(out.get("references") or [])[1])}

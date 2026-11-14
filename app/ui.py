"""HomeStretch caregiver UI (Assignment 4, Part 3). Three use cases: cabinet check, follow-up question, red flag.

    .venv/bin/python -m app.mcp_server --model deepseek-flash &     # optional: tools over MCP
    .venv/bin/streamlit run app/ui.py
"""
import json
import os
import uuid
from pathlib import Path

import streamlit as st

from app import tools
from app.tools import FIXTURE, ROOT

st.set_page_config(page_title="HomeStretch", page_icon="💊", layout="wide")
MANIFEST = json.loads((ROOT / "fixtures" / "labels" / "manifest.json").read_text())
EXAMPLES = {
    "Follow-up question": "Does the water pill make her lose potassium?",
    "Unknown medicine": "Can she take Zorvexa with her heart pills?",
    "Dose question": "She forgot her water pill this morning. Should she take two now?",
    "Red flag": "Mom says her chest feels tight and she's gasping.",
}

ss = st.session_state
ss.setdefault("session_id", f"ui-{uuid.uuid4().hex[:8]}")
ss.setdefault("chat", [])

# ----------------------------------------------------------------------------------------------- sidebar
with st.sidebar:
    st.header("HomeStretch")
    st.caption(f"Synthetic patient: {FIXTURE['patient_profile']['preferred_name']}, "
               f"{FIXTURE['patient_profile']['age']}, discharged {FIXTURE['patient_profile']['discharged']}. "
               "Demo only, not medical advice.")
    model = st.selectbox("Model", ["mock", "deepseek-flash"], help="mock makes no API calls")
    via = st.radio("Tools", ["local", "mcp"], horizontal=True,
                   help="mcp: discovered from the HomeStretch MCP server (start app.mcp_server first)")
    os.environ["HS_TOOLS"] = via
    from app import tool_client
    if via == "mcp":
        try:
            st.success(f"MCP server: {len(tool_client.list_tools())} tools discovered")
        except Exception as e:  # noqa: BLE001
            st.error(f"MCP server not reachable ({type(e).__name__}). Start it or switch to local.")
    if st.button("New session"):
        ss.session_id, ss.chat = f"ui-{uuid.uuid4().hex[:8]}", []
        st.rerun()
    with st.expander("Session memory"):
        st.json(tools.get_session_memory(ss.session_id))


def show_reply(out):
    f = out["final"]
    if f.get("red_flag_tier") == 3:
        st.error(f["reply"])
    else:
        st.markdown(f["reply"] or "_(no reply)_")
    if f.get("flags"):
        st.dataframe([{k: x.get(k) for k in ("label", "cabinet_ref", "plan_ref", "detail")} for x in f["flags"]],
                     hide_index=True)
    cost = sum(u["cost_usd"] for u in out["usage"])
    with st.expander(f"How this answer was made · {len(out['trace'])} steps · {len(out['usage'])} model calls · ${cost:.4f}"):
        st.caption(f"Answered by: {f.get('by')} · sources: {f.get('sources')}")
        for t in out["trace"]:
            st.markdown(f"**{t['step']}** — {t['detail']}")


def run(**kw):
    from app.graph import run_turn
    with st.spinner("Working…"):
        return run_turn(ss.session_id, model=model, **kw)


tab_chat, tab_cab = st.tabs(["💬 Ask a question", "🧴 Check the medicine cabinet"])

# ----------------------------------------------------------------------------------------------- chat
with tab_chat:
    cols = st.columns(len(EXAMPLES))
    clicked = next((txt for c, (label, txt) in zip(cols, EXAMPLES.items()) if c.button(label)), None)
    for m in ss.chat:
        with st.chat_message(m["role"]):
            show_reply(m["out"]) if m["role"] == "assistant" else st.markdown(m["text"])
    msg = st.chat_input("Ask about her medicines or how she's feeling") or clicked
    if msg:
        ss.chat.append({"role": "user", "text": msg})
        ss.chat.append({"role": "assistant", "out": run(message=msg)})
        st.rerun()

# ----------------------------------------------------------------------------------------------- cabinet
with tab_cab:
    st.write("Photograph each bottle, or pick sample label photos. HomeStretch reads each label, checks the name in "
             "RxNorm, and compares the bottles with the discharge plan.")
    choices = {f"{lab['label']} ({lab['style']}): {lab['truth']['name']}": lab["path"]
               for lab in MANIFEST["labels"] if lab["style"] in ("clean", "blur")}
    picked = st.multiselect("Sample label photos (synthetic)", list(choices))
    uploads = st.file_uploader("Or upload label photos (synthetic labels only)", type=["png", "jpg", "jpeg"],
                               accept_multiple_files=True)
    if picked:
        st.image([str(ROOT / choices[p]) for p in picked], width=180)
    if st.button("Run cabinet check", type="primary", disabled=not (picked or uploads)):
        paths = [choices[p] for p in picked]
        up_dir = tools.SESSIONS / "uploads" / ss.session_id
        for u in uploads or []:
            up_dir.mkdir(parents=True, exist_ok=True)
            dest = up_dir / Path(u.name).name
            dest.write_bytes(u.getvalue())
            paths.append(str(dest.relative_to(ROOT)))
        ss.cab_out = run(photos=paths)
    if "cab_out" in ss:
        show_reply(ss.cab_out)

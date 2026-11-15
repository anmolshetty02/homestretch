"""HomeStretch caregiver app (Assignment 4, Part 3). Mobile-first: Today, Ask, Bottles.

    .venv/bin/python -m app.mcp_server --model deepseek-flash &     # optional: tools over MCP
    .venv/bin/streamlit run app/ui.py

Theme (colors, fonts) lives in .streamlit/config.toml. The only custom HTML is the 30-day capsule strip.
"""
import json
import os
import re
import sys
import uuid
from datetime import datetime
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # `streamlit run app/ui.py` puts app/, not the repo, on the path
from app import tools  # noqa: E402
from app.tools import FIXTURE, ROOT  # noqa: E402

st.set_page_config(page_title="HomeStretch", page_icon=":material/home_health:", layout="centered",
                   initial_sidebar_state="collapsed")

PLAN, PROFILE = FIXTURE["care_plan"], FIXTURE["patient_profile"]
MANIFEST = json.loads((ROOT / "fixtures" / "labels" / "manifest.json").read_text())
CONTACTS = {c["id"]: c for c in PLAN["contacts"]}
STICKERS = {  # cabinet-check labels in the caregiver's words, styled like pharmacy auxiliary stickers
    "stopped_still_present": ("Stopped at discharge", "red", ":material/block:"),
    "dose_changed": ("Dose changed", "orange", ":material/swap_vert:"),
    "new_not_filled": ("Not picked up yet", "blue", ":material/local_pharmacy:"),
    "not_on_list": ("Not on her list", "orange", ":material/help:"),
    "duplicate": ("Two of the same", "orange", ":material/content_copy:"),
    "pharmacist_check": ("Ask the pharmacist", "orange", ":material/local_pharmacy:"),
    "ok": ("Matches her plan", "green", ":material/check_circle:"),
}
SLOTS = [("Morning · 8 AM", "8 in the morning"), ("Afternoon · 2 PM", "2 in the afternoon")]  # ponytail: from p001's wording


def _date(s):
    return datetime.strptime(s, "%A, %B %d, %Y")


TODAY = _date(FIXTURE["today"])
DAY = (TODAY - _date(PROFILE["discharged"])).days + 1

ss = st.session_state
ss.setdefault("session_id", f"ui-{uuid.uuid4().hex[:8]}")
ss.setdefault("chat", [])
ss.setdefault("weights", [])


# ----------------------------------------------------------------------------------------------- settings
with st.sidebar:
    st.subheader("Behind the scenes")
    st.caption(f"Synthetic patient for a class project. {PROFILE['preferred_name']}, {PROFILE['age']}, "
               f"home after {PROFILE['hospital_stay_reason']}. Not medical advice.")
    model = st.selectbox("Model", ["deepseek-flash", "mock"], help="mock makes no API calls and gives fake replies")
    if model == "mock":
        st.warning("Test mode: replies are fake placeholders.")
    via = st.segmented_control("Tools", ["local", "mcp"], default="local", required=True,
                               help="mcp: tools are discovered from the HomeStretch MCP server (start app.mcp_server first)")
    os.environ["HS_TOOLS"] = via
    from app import tool_client
    if via == "mcp":
        try:
            st.success(f"MCP server: {len(tool_client.list_tools())} tools discovered")
        except Exception as e:  # noqa: BLE001
            st.error(f"MCP server not reachable ({type(e).__name__}). Start it, or switch to local.")
    show_trace = st.toggle("Show how each answer was made", value=True)
    if st.button("Start a new session", icon=":material/restart_alt:"):
        for k in ("chat", "weights", "cab_out", "wrong_out"):
            ss.pop(k, None)
        ss.session_id = f"ui-{uuid.uuid4().hex[:8]}"
        st.rerun()
    with st.expander("Session memory"):
        st.json(tools.get_session_memory(ss.session_id))


# ----------------------------------------------------------------------------------------------- shared
def run(**kw):
    from app.graph import run_turn
    with st.spinner("Checking…"):
        return run_turn(ss.session_id, model=model, **kw)


def sticker_cards(flags):
    for x in flags:
        text, color, icon = STICKERS.get(x.get("label"), (str(x.get("label")), "gray", ":material/info:"))
        with st.container(border=True):
            st.badge(text, icon=icon, color=color)
            st.write(re.sub(r"\s*\[[a-z]+-\d+\]", "", str(x.get("detail") or "")))


SOURCE = {"ref": "drug label", "name": "RxNorm", "flag": "bottle check"}  # every other id prefix is her plan


def cite(text):
    """[flag-1][stopped-1] -> small grey source tags a caregiver can read; the exact ids stay in the trace."""
    def tags(m):
        kinds = dict.fromkeys(SOURCE.get(k, "her plan") for k in re.findall(r"([a-z]+)-\d+", m.group(0)))
        return " " + " ".join(f":gray-badge[{k}]" for k in kinds)
    return re.sub(r"\s*(?:\[[a-z]+-\d+\])+", tags, text)


def show_reply(out):
    f = out["final"]
    tier = f.get("red_flag_tier")
    text = cite(f.get("reply") or "_(no reply)_")
    if tier == 3:
        st.error(re.sub(r"^\W*call 911 now[.!]?\s*", "", text, flags=re.I) or "Stay with her until help arrives.",
                 title="Call 911 now", icon=":material/emergency:")
    elif tier in (1, 2):
        st.warning(text, icon=":material/call:")
    else:
        st.markdown(text)
    flags = [x for x in f.get("flags") or [] if isinstance(x, dict)]
    if flags:
        sticker_cards(sorted(flags, key=lambda x: x.get("label") == "ok"))
    if show_trace:
        cost = sum(u["cost_usd"] for u in out["usage"])
        with st.expander(f"How this answer was made · {len(out['trace'])} steps · ${cost:.4f}", icon=":material/account_tree:"):
            st.caption(f"Answered by {f.get('by')} · tools via "
                       f"{'MCP server' if os.environ.get('HS_TOOLS') == 'mcp' else 'in-process calls'} · sources {f.get('sources')}")
            st.code("\n".join(f"{t['step']:<18} {t['detail']}" for t in out["trace"]), language=None, wrap_lines=True)


def capsule_strip():
    """Signature: the 30 days at home as a row of capsules, like a pill organizer."""
    caps = "".join(f'<span class="cap {"past" if d < DAY else "today" if d == DAY else ""}"></span>' for d in range(1, 31))
    st.html(f"""<style>
      .hs-strip {{ display:grid; grid-template-columns:repeat(15, 1fr); gap:5px 4px; margin:6px 0 4px; }}
      .hs-strip .cap {{ height:11px; border-radius:6px; background:#D3DEDD; }}
      .hs-strip .cap.past {{ background:#0F5257; }}
      .hs-strip .cap.today {{ background:#E7A33E; box-shadow:0 0 0 2px #EEF2F2, 0 0 0 3px #C27A1A; }}
      .hs-day {{ font-family:'Lexend',sans-serif; font-size:15px; color:#1C2B2D; margin:0; }}
      .hs-day b {{ font-weight:600; }}
    </style>
    <p class="hs-day"><b>Day {DAY} of 30</b> at home · {TODAY:%A, %B} {TODAY.day}</p>
    <div class="hs-strip" role="img" aria-label="Day {DAY} of the first 30 days at home">{caps}</div>""")


def open_items():
    diff = tools.get_session_memory(ss.session_id).get("cabinet_diff") or []
    return [x for x in diff if isinstance(x, dict) and x.get("label") != "ok"]


# ----------------------------------------------------------------------------------------------- header
st.title(f"Caring for {PROFILE['preferred_name']}")
capsule_strip()
ss.setdefault("page", "Today")
page = st.segmented_control("Section", ["Today", "Ask", "Bottles"], required=True,
                            label_visibility="collapsed", key="page")

# ----------------------------------------------------------------------------------------------- today
if page == "Today":
    with st.container(border=True, key="wrong"):
        st.markdown("**Something feels wrong?**")
        with st.form("wrong_form", clear_on_submit=True, border=False):
            said = st.text_input("Describe what you're seeing", placeholder="She's dizzy when she stands up",
                                 label_visibility="collapsed")
            if st.form_submit_button("Check this now", type="primary", icon=":material/stethoscope:", width="stretch") and said:
                ss.wrong_out = run(message=said)
                ss.chat += [{"role": "user", "text": said}, {"role": "assistant", "out": ss.wrong_out}]
        if "wrong_out" in ss:
            show_reply(ss.wrong_out)

    st.subheader("Medicines today")
    for slot, phrase in SLOTS:
        due = [m for m in PLAN["medications"] if phrase in m["when"]]
        with st.container(border=True):
            st.markdown(f"**{slot}**")
            for m in due:
                st.checkbox(f"{m['plain_name'].capitalize()} — {m['name']} {m['dose'].replace(' milligrams', ' mg')}",
                            key=f"given_{slot}_{m['id']}")
                if (m.get("status") or "unchanged") != "unchanged":  # "unchanged" contains "changed"
                    st.caption(f":orange[{m['status'].capitalize()}]")

    with st.container(border=True):
        st.markdown("**Morning weight**")
        st.caption("After the bathroom, before breakfast. Up 3 lb in a day or 5 lb in a week: call the clinic.")
        c = st.container(horizontal=True, vertical_alignment="bottom")
        w = c.number_input("Weight (lb)", min_value=60.0, max_value=400.0, value=None, step=0.5, placeholder="e.g. 182")
        if c.button("Log", icon=":material/scale:") and w:
            ss.weights.append(w)
        if ss.weights:
            last = ss.weights[-1]
            if len(ss.weights) > 1 and last - ss.weights[-2] >= 3:
                clinic = CONTACTS["contact-1"]
                st.warning(f"Up {last - ss.weights[-2]:.1f} lb since the last entry. Call {clinic['name']} today: {clinic['phone']}.",
                           icon=":material/call:")
            else:
                st.caption(f"Logged {last:.1f} lb.")

    items = open_items()
    st.subheader("Still to sort out")
    if items:
        sticker_cards(items)
    else:
        st.caption("Nothing open. Check her bottles once after every pharmacy pickup.")
        st.button("Check her bottles", icon=":material/photo_camera:", on_click=lambda: ss.update(page="Bottles"))

    appt = PLAN["appointments"][0]
    st.subheader("Coming up")
    st.markdown(f"**{appt['with']}** · {appt['when']}  \n{appt['where']}")

    with st.expander("When to call for help", icon=":material/call:"):
        for w_ in PLAN["warning_signs"]:
            st.markdown(f"{':red[**911**]' if w_['tier'] == 3 else ':orange[**Today**]' if w_['tier'] == 1 else ':orange[**Now**]'}"
                        f" · {w_['sign']}")
        st.caption(" · ".join(f"{c['name']}: {c['phone']}" for c in PLAN["contacts"]))

# ----------------------------------------------------------------------------------------------- ask
elif page == "Ask":
    st.caption("Ask about her medicines, her plan, or how she's feeling. Answers come from her discharge plan and "
               "the official drug labels, with sources.")
    starters = ["Does the water pill make her lose potassium?", "Can she take Advil for her knee?",
                "What should I ask the pharmacy about the bottles?"]
    def _use_starter():  # callbacks may reset a widget; code after it in the same run may not
        ss.pending, ss.starter = ss.starter, None

    st.pills("Try", starters, label_visibility="collapsed", key="starter", on_change=_use_starter)
    for m in ss.chat:
        with st.chat_message(m["role"], avatar=":material/person:" if m["role"] == "user" else ":material/home_health:"):
            if m["role"] == "assistant":
                show_reply(m["out"])
            else:
                st.markdown(m["text"])
    msg = st.chat_input("Ask a question about her care") or ss.pop("pending", None)
    if msg:
        ss.chat += [{"role": "user", "text": msg}, {"role": "assistant", "out": run(message=msg)}]
        st.rerun()

# ----------------------------------------------------------------------------------------------- bottles
else:
    st.caption("After each pharmacy pickup, photograph every bottle. HomeStretch reads each label, checks the name, "
               "and compares the bottles with her discharge plan.")
    photo = st.camera_input("Photograph a bottle label", key="cam") if st.toggle("Use the camera", key="use_cam") else None
    with st.expander("Use sample labels instead", icon=":material/photo_library:"):
        choices = {f"{lab['truth']['name']} {lab['truth']['strength']} · {lab['truth']['directions']}": lab["path"]
                   for lab in MANIFEST["labels"] if lab["style"] == "clean"}
        picked = st.multiselect("Sample label photos (synthetic)", list(choices))
        uploads = st.file_uploader("Or upload label photos", type=["png", "jpg", "jpeg"], accept_multiple_files=True)
        if picked:
            st.image([str(ROOT / choices[p]) for p in picked], width=150, caption=picked)
    files = list(uploads or []) + ([photo] if photo else [])
    if st.button("Check these bottles", type="primary", icon=":material/fact_check:", width="stretch",
                 disabled=not (picked or files)):
        paths = [choices[p] for p in picked]
        up_dir = tools.SESSIONS / "uploads" / ss.session_id
        for i, u in enumerate(files):
            up_dir.mkdir(parents=True, exist_ok=True)
            dest = up_dir / (Path(u.name).name if getattr(u, "name", "") else f"camera-{i}.jpg")
            dest.write_bytes(u.getvalue())
            paths.append(str(dest.relative_to(ROOT)))
        ss.cab_out = run(photos=paths)
    if "cab_out" in ss:
        show_reply(ss.cab_out)

"""UI self-check with Streamlit's AppTest (mock model, no API calls): every section renders and each use case runs.
    .venv/bin/python -m app.test_ui
"""
import ast
from pathlib import Path

from streamlit.testing.v1 import AppTest

src = ast.parse((Path(__file__).parent / "ui.py").read_text())                  # cite() alone, without running the app
ns = {"re": __import__("re")}
exec(compile(ast.Module([n for n in src.body if getattr(n, "name", None) == "cite"
                         or (isinstance(n, ast.Assign) and getattr(n.targets[0], "id", None) == "SOURCE")], []), "ui", "exec"), ns)
assert ns["cite"]("may be needed [ref-1][ref-2]. Still there [flag-1][stopped-1].") == \
    "may be needed :gray-badge[drug label]. Still there :gray-badge[bottle check] :gray-badge[her plan].", ns["cite"]("x [ref-1]")

at = AppTest.from_file("ui.py", default_timeout=120).run()
at.sidebar.selectbox[0].set_value("mock").run()
assert not at.exception, at.exception
assert any("Day 5 of 30" in h.value for h in at.html), "capsule strip missing"

at.text_input[0].set_value("Her chest feels tight and she's gasping")            # Today: something feels wrong
at.button[0].click()                                                             # a form's text and submit go in one run
at.run()
assert at.session_state["wrong_out"]["final"]["red_flag_tier"] == 3 and len(at.error) >= 1, "no 911 alert"
assert not at.exception, at.exception

at.segmented_control(key="page").set_value("Ask").run()                          # Ask: a starter question
at.pills(key="starter").set_value("Does the water pill make her lose potassium?").run()
assert not at.exception, at.exception
assert len(at.chat_message) >= 4, len(at.chat_message)                           # wrong-box turn + starter turn
assert not any("DeltaGenerator" in str(getattr(e, "value", "")) for e in at.main), "Streamlit magic leaked output"

at.segmented_control(key="page").set_value("Bottles").run()                      # Bottles: sample labels
opts = at.multiselect[0].options
assert len(opts) == len(set(opts)) and sum(o.startswith("Furosemide 20 mg") for o in opts) == 2, "sample labels collapsed"
at.multiselect[0].select(opts[0]).run()
next(b for b in at.button if b.label == "Check these bottles").click().run()
assert not at.exception, at.exception
print("UI self-check ok")

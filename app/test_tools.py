"""Part 1 self-check, in-process (no MCP server, no paid calls; RxNav answers come from app/.cache_rxnav.json).
    .venv/bin/python -m app.test_tools
"""
from app import tool_client as c
from app import tools as t

assert t.check_medicine_name("Lasix")["ingredients"] == ["furosemide"]
assert t.check_medicine_name("Toprol XL")["status"] == "matched"  # retired RxCUI: must not read as unknown
assert t.check_medicine_name("Zorvexa")["status"] == "no_match"   # made-up name: pharmacist_check, never a guess
for bad in (t.check_medicine_name(""), t.get_care_plan("x; drop"), t.read_label_photo("../../etc/passwd"),
            t.get_session_memory("../x"), c.call_tool("nope", {}), c.call_tool("get_care_plan", {"bad": 1})):
    assert "error" in bad, bad
assert t.get_care_plan("stopped-1")["name"] == "metoprolol tartrate"
assert t.search_drug_label("Can she take Zorvexa with her pills?")["references"] == []
refs = t.search_drug_label("Does the water pill make her lose potassium?")["references"]
assert len(refs) == t.TOP_K and refs[0]["drug"] == "furosemide", refs[0]
assert {s["name"] for s in c.list_tools()} == set(t.FUNCTIONS)
print("tools self-check ok")

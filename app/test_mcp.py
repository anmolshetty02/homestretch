"""MCP path self-check: starts the real MCP server (mock model, free), then runs pipeline turns with every tool call
going over MCP, including the write tool with a cabinet check.
    .venv/bin/python -m app.test_mcp
"""
import os
import subprocess
import sys
import time
import urllib.request

PORT = 8799
os.environ.update(HS_TOOLS="mcp", HS_MCP_URL=f"http://127.0.0.1:{PORT}/mcp")

from app import tool_client as tc  # noqa: E402  (reads HS_MCP_URL at import)
from app import tools  # noqa: E402
from app.graph import run_turn  # noqa: E402

server = subprocess.Popen([sys.executable, "-m", "app.mcp_server", "--port", str(PORT)],
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
try:
    for _ in range(600):  # the server warms the label index first: ~2 min on a fresh clone (the vector cache is not committed)
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{PORT}/mcp", timeout=1)
            break
        except OSError as e:
            if getattr(e, "code", None):  # any HTTP answer means it is up
                break
            time.sleep(1)
    assert {t["name"] for t in tc.list_tools()} == set(tools.FUNCTIONS)
    assert tc.call_tool("check_medicine_name", {"name": "Lasix"})["ingredients"] == ["furosemide"]
    assert "error" in tc.call_tool("nope", {}) and "error" in tc.call_tool("get_care_plan", {"item_id": 5})

    sid = "mcp-selfcheck"
    cab = [{"id": "cab-1", "name": "Metoprolol Tartrate", "strength": "25 mg", "directions": "twice daily"}]
    out = run_turn(sid, cabinet=cab)
    assert out["final"]["by"] == "Prompt B v8", out["trace"]
    assert tools.get_session_memory(sid)["cabinet_diff"], "cabinet flags were not saved through the MCP write tool"
    out = run_turn(sid, "Does the water pill make her lose potassium?")
    assert any(t["step"] == "tools" and "search_drug_label: ok" in t["detail"] for t in out["trace"]), out["trace"]
    print("MCP self-check ok")
finally:
    server.terminate()
    (tools.SESSIONS / "mcp-selfcheck.json").unlink(missing_ok=True)

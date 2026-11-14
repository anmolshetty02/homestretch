"""HomeStretch MCP server: publishes app/tools.py over the Model Context Protocol (streamable HTTP, mcp 2.x).

    .venv/bin/python -m app.mcp_server          # serves http://127.0.0.1:8765/mcp

Running as its own process keeps the embedding and reranking models loaded between calls, and lets the tools change
without touching the agent: the agent only discovers tools (list_tools) and calls them by name.
The input schema of each tool comes from the wrapper's typed signature; the description from tools.SPECS.
"""
import json

from mcp.server.mcpserver import MCPServer

from app import tools

mcp = MCPServer("homestretch-tools")
DESC = {s["name"]: s["description"] + (" WRITE: changes stored data." if s["write"] else "") for s in tools.SPECS}


def check_medicine_name(name: str) -> str:
    return json.dumps(tools.check_medicine_name(name))


def search_drug_label(question: str) -> str:
    return json.dumps(tools.search_drug_label(question))


def get_care_plan(item_id: str = "") -> str:
    return json.dumps(tools.get_care_plan(item_id or None))


def read_label_photo(path: str) -> str:
    return json.dumps(tools.read_label_photo(path, model=MODEL))


def get_session_memory(session_id: str) -> str:
    return json.dumps(tools.get_session_memory(session_id))


def update_session_memory(session_id: str, message: str, reply: str = "", cabinet_diff: list[dict] | None = None) -> str:
    return json.dumps(tools.update_session_memory(session_id, message, reply or None, cabinet_diff, model=MODEL))


MODEL = "mock"  # tools that call a model (Prompt A, the memory update) use this; set with --model
for fn in (check_medicine_name, search_drug_label, get_care_plan, read_label_photo, get_session_memory,
           update_session_memory):
    mcp.add_tool(fn, description=DESC[fn.__name__], structured_output=False)
assert {t.name for t in mcp._tool_manager.list_tools()} == set(tools.FUNCTIONS)


@mcp.resource("homestretch://care-plan")
def care_plan() -> str:
    """The patient's discharge care plan (read-only resource)."""
    return json.dumps(tools.get_care_plan())


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="mock")
    ap.add_argument("--port", type=int, default=8765)
    MODEL = ap.parse_args().model
    tools._load_index()  # warm the label index before the first request
    mcp.run(transport="streamable-http", host="127.0.0.1", port=ap.parse_args().port)

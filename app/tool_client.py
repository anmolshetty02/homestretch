"""How the agent reaches tools. HS_TOOLS=mcp discovers and calls them on the MCP server (app/mcp_server.py);
HS_TOOLS=local (the default, also in the UI) calls the same functions in-process (evals, tests, no server)."""
import asyncio
import json
import os

from app import tools

MCP_URL = os.environ.get("HS_MCP_URL", "http://127.0.0.1:8765/mcp")


def transport():
    return os.environ.get("HS_TOOLS", "local")


async def _mcp(op, name=None, args=None):
    from mcp import ClientSession
    from mcp.client.streamable_http import streamable_http_client
    async with streamable_http_client(MCP_URL) as (read, write):
        async with ClientSession(read, write) as s:
            await s.initialize()
            if op == "list":
                return [{"name": t.name, "description": t.description, "parameters": t.input_schema}
                        for t in (await s.list_tools()).tools]
            res = await s.call_tool(name, args)
            text = res.content[0].text if res.content else ""
            try:
                return json.loads(text)
            except json.JSONDecodeError:  # the server rejected the call (unknown tool, bad arguments)
                return {"error": text or "empty tool result"}


def list_tools():
    """Tool specs, discovered from the MCP server or read from the local registry."""
    if transport() == "mcp":
        return asyncio.run(_mcp("list"))
    return [{k: s[k] for k in ("name", "description", "parameters")} for s in tools.SPECS]


MODEL_TOOLS = {"read_label_photo", "update_session_memory"}  # tools that call a model themselves


def call_tool(name, args, model="mock"):
    """Run one tool. Unknown tools and failures come back as {"error": ...}, never an exception.
    `model` reaches the tools that call a model in-process; the MCP server uses its own --model."""
    if transport() == "mcp":
        try:
            return asyncio.run(_mcp("call", name, args))
        except Exception as e:  # noqa: BLE001  (server down, timeout, protocol error)
            while isinstance(e, BaseExceptionGroup):  # anyio wraps the real cause in task-group errors
                e = e.exceptions[0]
            return {"error": f"MCP call to {name!r} failed: {type(e).__name__}: {e}"}
    fn = tools.FUNCTIONS.get(name)
    if fn is None:
        return {"error": f"Unknown tool {name!r}. Available: {sorted(tools.FUNCTIONS)}"}
    try:
        return fn(**args, **({"model": model} if name in MODEL_TOOLS else {}))
    except TypeError as e:
        return {"error": f"Bad arguments for {name}: {e}"}


def openai_tools(names):
    """Specs in the chat-completions `tools` format, limited to `names`."""
    return [{"type": "function", "function": t} for t in list_tools() if t["name"] in names]

#!/usr/bin/env python3
"""Call OmniRoute MCP tools live: health, combos, best-combo, memory cycle, skills."""
import json, os, urllib.request

BASE = "http://localhost:20128/api/mcp/stream"
KEY = os.environ.get("OMNIROUTE_KEY", "")
SESSION = {}

def rpc(method, params, _id):
    body = json.dumps({"jsonrpc": "2.0", "id": _id, "method": method, "params": params}).encode()
    req = urllib.request.Request(BASE, data=body, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("Accept", "application/json, text/event-stream")
    if KEY:
        req.add_header("Authorization", f"Bearer {KEY}")
    if SESSION.get("id"):
        req.add_header("Mcp-Session-Id", SESSION["id"])
    with urllib.request.urlopen(req, timeout=60) as r:
        sid = r.headers.get("Mcp-Session-Id")
        if sid:
            SESSION["id"] = sid
        raw = r.read().decode()
    for line in raw.splitlines():
        if line.startswith("data:"):
            return json.loads(line[5:].strip())
    return json.loads(raw)

def call(name, args, _id):
    res = rpc("tools/call", {"name": name, "arguments": args}, _id)
    if "error" in res:
        return {"error": res["error"]}
    content = res.get("result", {}).get("content", [])
    texts = [c.get("text", "") for c in content if c.get("type") == "text"]
    return {"text": "\n".join(texts), "structured": res.get("result", {}).get("structuredContent")}

rpc("initialize", {"protocolVersion": "2024-11-05", "capabilities": {},
                   "clientInfo": {"name": "hermes-test", "version": "1.0"}}, 1)

print("== get_health ==")
print(json.dumps(call("omniroute_get_health", {}, 10), ensure_ascii=False)[:800])

print("\n== list_combos (metrics) ==")
r = call("omniroute_list_combos", {"includeMetrics": True}, 11)
print(json.dumps(r, ensure_ascii=False)[:1200])

print("\n== best_combo_for_task (coding) ==")
r = call("omniroute_best_combo_for_task", {"taskType": "coding"}, 12)
print(json.dumps(r, ensure_ascii=False)[:800])

print("\n== skills_list ==")
r = call("omniroute_skills_list", {}, 13)
print(json.dumps(r, ensure_ascii=False)[:600])

print("\n== memory_search (before) ==")
r = call("omniroute_memory_search", {"query": "test"}, 14)
print(json.dumps(r, ensure_ascii=False)[:600])

print("\n== memory_add ==")
r = call("omniroute_memory_add", {"type": "factual", "key": "mcp-test", "content": "OmniRoute MCP live test entry"}, 15)
print(json.dumps(r, ensure_ascii=False)[:600])

print("\n== memory_search (after) ==")
r = call("omniroute_memory_search", {"query": "mcp-test"}, 16)
print(json.dumps(r, ensure_ascii=False)[:800])

print("\n== memory_clear ==")
r = call("omniroute_memory_clear", {}, 17)
print(json.dumps(r, ensure_ascii=False)[:400])

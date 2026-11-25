import asyncio, json, sys
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

URL = sys.argv[1]

def j(res):
    return json.loads(res.content[0].text)

async def main():
    async with streamablehttp_client(URL) as (r, w, _):
        async with ClientSession(r, w) as s:
            await s.initialize()
            lists = (await s.call_tool("list_lists", {}))
            names = [json.loads(c.text)["name"] for c in lists.content]
            print("lists:", names)
            target = next(n for n in names if n.lower() in ("tasks", "작업")) if any(n.lower() in ("tasks", "작업") for n in names) else names[0]
            add = j(await s.call_tool("add_task", {"title": "[MCP 연동 테스트] 삭제해도 됨", "list_name": target,
                                                  "due_date": "2026-11-26", "important": True, "subtasks": ["하위1"]}))
            print("add:", add)
            tid = add["task_id"]
            found = j(await s.call_tool("search_tasks", {"query": "MCP 연동 테스트"}))
            print("search:", found["count"], found["tasks"][0] if found["tasks"] else None)
            sub = found["tasks"][0]["subtasks"][0]["subtask_id"]
            print("sub done:", j(await s.call_tool("set_subtask_done", {"task_id": tid, "subtask_id": sub})))
            print("update:", j(await s.call_tool("update_task", {"task_id": tid, "clear_due_date": True, "important": False})))
            print("complete:", j(await s.call_tool("complete_task", {"task_id": tid})))

asyncio.run(main())

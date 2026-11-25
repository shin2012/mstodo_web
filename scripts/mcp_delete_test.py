"""삭제 도구 테스트: 테스트 할 일을 만들고 하위 작업 → 할 일 순서로 지운 뒤 사라졌는지 확인."""
import asyncio, json, sys
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

URL, TOKEN = sys.argv[1], sys.argv[2]

def j(res):
    if res.isError:
        raise SystemExit("ERROR: " + res.content[0].text)
    return json.loads(res.content[0].text)

async def main():
    async with streamablehttp_client(URL, headers={"Authorization": f"Bearer {TOKEN}"}) as (r, w, _):
        async with ClientSession(r, w) as s:
            await s.initialize()
            tools = {t.name: t for t in (await s.list_tools()).tools}
            print("delete tools:", [n for n in tools if n.startswith("delete")],
                  "destructive:", tools["delete_task"].annotations.destructiveHint)
            add = j(await s.call_tool("add_task", {"title": "[MCP 삭제 테스트]", "list_name": "작업",
                                                  "subtasks": ["지울 하위", "남길 하위"]}))
            tid = add["task_id"]
            t = j(await s.call_tool("search_tasks", {"query": "MCP 삭제 테스트"}))["tasks"][0]
            sub = next(x for x in t["subtasks"] if x["title"] == "지울 하위")["subtask_id"]
            print("delete_subtask:", j(await s.call_tool("delete_subtask", {"task_id": tid, "subtask_id": sub})))
            t = j(await s.call_tool("search_tasks", {"query": "MCP 삭제 테스트"}))["tasks"][0]
            print("remaining subtasks:", [x["title"] for x in t["subtasks"]])
            print("delete_task:", j(await s.call_tool("delete_task", {"task_id": tid})))
            j(await s.call_tool("sync_todo", {}))
            print("after sync search:", j(await s.call_tool("search_tasks", {"query": "MCP", "include_completed": True}))["count"])

asyncio.run(main())

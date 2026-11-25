"""삭제 도구 테스트: 테스트 할 일 3개를 만들고
1) 제목이 틀린 일괄 삭제 → 아무것도 안 지워지는지
2) 하위 작업 2개 일괄 삭제
3) 할 일 3개 한 번에 삭제 → 동기화 후에도 사라졌는지 확인."""
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
            print("delete tools:", [n for n in tools if n.startswith("delete")])
            print("schema:", json.dumps(tools["delete_tasks"].inputSchema, ensure_ascii=False)[:300])
            made = []
            for i in range(1, 4):
                a = j(await s.call_tool("add_task", {"title": f"[MCP 삭제 테스트 {i}]", "list_name": "작업",
                                                    "subtasks": ["하위 A", "하위 B", "하위 C"] if i == 1 else None}))
                made.append({"title": a["title"], "task_id": a["task_id"]})
            bad = [dict(made[0]), dict(made[1], title="틀린 제목")]
            r = await s.call_tool("delete_tasks", {"items": bad})
            print("wrong title → error:", r.isError, r.content[0].text[:120])
            print("still there:", j(await s.call_tool("search_tasks", {"query": "MCP 삭제 테스트"}))["count"])
            t = j(await s.call_tool("search_tasks", {"query": "MCP 삭제 테스트 1"}))["tasks"][0]
            subs = [{"title": x["title"], "subtask_id": x["subtask_id"]} for x in t["subtasks"] if x["title"] != "하위 C"]
            print("delete_subtasks:", j(await s.call_tool("delete_subtasks", {"task_title": t["title"], "task_id": t["task_id"], "subtasks": subs})))
            t = j(await s.call_tool("search_tasks", {"query": "MCP 삭제 테스트 1"}))["tasks"][0]
            print("remaining subtasks:", [x["title"] for x in t["subtasks"]])
            print("delete_tasks:", j(await s.call_tool("delete_tasks", {"items": made})))
            j(await s.call_tool("sync_todo", {}))
            print("after sync:", j(await s.call_tool("search_tasks", {"query": "MCP 삭제 테스트", "include_completed": True}))["count"])


asyncio.run(main())

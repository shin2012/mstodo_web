import asyncio, json, os, sys
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

URL = sys.argv[1]
HDR = {"Authorization": f"Bearer {sys.argv[2]}"} if len(sys.argv) > 2 else None

async def main():
    async with streamablehttp_client(URL, headers=HDR) as (r, w, _):
        async with ClientSession(r, w) as s:
            await s.initialize()
            tools = await s.list_tools()
            print("TOOLS:", [t.name for t in tools.tools])
            res = await s.call_tool("list_lists", {})
            print("LISTS:", res.content[0].text[:300] if res.content else res)
            res = await s.call_tool("list_tasks", {"due": "week"})
            d = json.loads(res.content[0].text)
            print("WEEK count:", d.get("count"), [t["title"] for t in d.get("tasks", [])][:5])

asyncio.run(main())

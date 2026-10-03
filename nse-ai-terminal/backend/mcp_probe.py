"""List MCP tools and optionally call one."""
import asyncio
import sys
import config

async def main():
    from mcp import ClientSession
    from mcp.client.streamable_http import streamablehttp_client
    headers={"Authorization":f"Bearer {config.MCP_AUTH_TOKEN}"} if config.MCP_AUTH_TOKEN else None
    async with streamablehttp_client(config.MCP_SERVER_URL,headers=headers) as (r,w,_):
        async with ClientSession(r,w) as s:
            await s.initialize()
            if len(sys.argv)>=4:
                res=await s.call_tool(sys.argv[1],{sys.argv[2]:sys.argv[3]})
                for p in res.content:print(getattr(p,"text",p))
                return
            for t in (await s.list_tools()).tools:
                props=list((t.inputSchema or {}).get("properties",{}))
                print(f"{t.name}  args={props}\n    {(t.description or '')[:110]}")
if __name__=="__main__":
    if not config.MCP_SERVER_URL:sys.exit("Set MCP_SERVER_URL first.")
    asyncio.run(main())
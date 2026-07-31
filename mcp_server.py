import asyncio
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent
from tools import search, search_memory as search_mem
from memory import save_to_memory

app = Server("autonomous-agent")

@app.list_tools()
async def list_tools():
    return [
        Tool(
            name="search_web",
            description="Search the internet for current information",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"}
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="search_memory",
            description="Search past memories and conversations",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "What to search for in memory"}
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="remember",
            description="Save important information to memory",
            inputSchema={
                "type": "object",
                "properties": {
                    "goal": {"type": "string", "description": "The original goal"},
                    "result": {"type": "string", "description": "What to remember"}
                },
                "required": ["goal", "result"]
            }
        )
    ]

@app.call_tool()
async def call_tool(name, arguments):
    if name == "search_web":
        result = search(arguments["query"])
        return [TextContent(type="text", text=result)]
    elif name == "search_memory":
        result = search_mem(arguments["query"])
        text, citations = result if isinstance(result, tuple) else (result, "")
        return [TextContent(type="text", text=str(text))]
    elif name == "remember":
        save_to_memory(arguments["goal"], arguments["result"])
        return [TextContent(type="text", text="Saved to memory successfully")]
    else:
        return [TextContent(type="text", text=f"Unknown tool: {name}")]

async def main():
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())

if __name__ == "__main__":
    asyncio.run(main())

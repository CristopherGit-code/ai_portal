from modules.main_graph.layout_graph import ChainManager
from mcp.server.fastmcp import FastMCP

mcp = FastMCP(
    "main_chain", 
    host="localhost",
    port=6100,
    stateless_http=True,
    mount_path="/mcp"
)

@mcp.tool()
async def plan_phase(query:str)->str:
    """ Returns the plan response for the query """
    chain = ChainManager()
    response = await chain.call_plan_phase(query)

    return response

@mcp.tool()
async def execute_phase(query:str)->str:
    """ Returns the final execution flow """
    chain = ChainManager()
    response = await chain.call_executor_phase(query)

    return response

@mcp.tool()
async def call_main_graph(query:str)->str:
    """ Calls complete graph """
    chain = ChainManager()
    response = await chain.call_main_graph(query)

    return response

if __name__ == "__main__":
    try:
        mcp.run(transport="streamable-http")
    except KeyboardInterrupt:
        print("Closing server")
    finally:
        print("Server closed")
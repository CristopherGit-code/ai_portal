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
async def main_chain(query:str)->str:
    """ Returns the response to the query """
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
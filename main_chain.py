import asyncio, logging
from modules.main_graph.layout_graph import ChainManager

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(name=f"MAIN_CHAIN.{__name__}")

async def main():
    chain = ChainManager()
    response = await chain.call_main_graph()
    print(response)

if __name__ == "__main__":
    asyncio.run(main())
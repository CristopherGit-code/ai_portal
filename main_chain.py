import asyncio, logging, httpx
from modules.graph.graph import SupervisorManager
from modules.util.lang_fuse import FuseConfig

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(name=f"Agent.{__name__}")

fuse_tracer = FuseConfig()
id = fuse_tracer.generate_id()
trace_handler = fuse_tracer.get_handler()

async def main():
    async with httpx.AsyncClient(timeout=10.0) as http_client:
        graph_agent = SupervisorManager(http_client)
        graph = graph_agent.build_graph()
        while True:
            try:
                user_input = input("USER: ")
                if user_input.lower() in ["quit", "exit", "q"]:
                    print("Goodbye!")
                    break
                final_response = []
                async for chunk in graph.astream( {"messages": [{"role": "user", "content": user_input}]},
                    {'configurable': {'thread_id': id},'callbacks':[trace_handler],'metadata':{'langfuse_session_id':id}},
                    stream_mode="values",
                    subgraphs=True
                ):
                    logger.debug("Chunk response ==========")
                    logger.debug(chunk[-1]['messages'][-1])
                    try:
                        final_response.append(chunk[-1]['messages'][-1].content)
                    except Exception as p:
                        final_response.append(f"Error in response: {p}")
                print("MODEL RESPONSE")
                print(final_response[-1])
            except Exception as e:
                logger.info(f'General error: {e}')

if __name__ == "__main__":
    asyncio.run(main())
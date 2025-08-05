import asyncio
import logging,httpx
from langgraph.graph import StateGraph, START, MessagesState, END
from modules.cluster.verification import VerificationAgent
from modules.chain_agents.orchestrator import OrchestratorAgent
from modules.cluster.executor import ExecutorAgent
from modules.util.lang_fuse import FuseConfig

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(name=f"GRAPH.{__name__}")

fuse_tracer = FuseConfig()
id = fuse_tracer.generate_id()
trace_handler = fuse_tracer.get_handler()

class LayoutState(MessagesState):
    """ change the status according to execution steps """
    status: str

class ChainManager:
    _instance = None
    _initialized = False

    def __new__(cls, http_client:httpx.AsyncClient):
        if cls._instance is None:
            cls._instance = super(ChainManager,cls).__new__(cls)
        return cls._instance
    
    def __init__(self,http_client:httpx.AsyncClient):
        if not self._initialized:
            self.http_client = http_client
            self.remote_addresses = [
                "http://localhost:9999/",
                "http://localhost:9998/",
                "http://localhost:9997/"
            ]
            # self.team_lead_host = TeamLeadAgent(self.remote_addresses,self.http_client)
            # self.team_lead_host.create_agent()
            # self.team_lead = self.team_lead_host.team_lead_agent
            self.orchestrator_hub = OrchestratorAgent()
            self.orchestrator = self.orchestrator_hub.build_main_cluster()
            self.verification_agent = VerificationAgent()
            self.executor = ExecutorAgent()
            ChainManager._initialized = True
    
    async def main_graph(self):
        main_graph_builder = StateGraph(LayoutState)
        main_graph_builder.add_node("verify",self.verification_agent.verify_query)
        main_graph_builder.add_node("team_lead",self.orchestrator_hub.call_main_cluster)
        main_graph_builder.add_node("executor",self.executor.executor_agent)
        main_graph_builder.add_edge(START,"verify")
        main_graph_builder.add_conditional_edges(
            "verify", self.verification_agent.verification_check, {"Fail": END, "Pass": "team_lead"}
        )
        main_graph_builder.add_edge("team_lead","executor")
        main_graph_builder.add_edge("executor",END)
        graph = main_graph_builder.compile()

        try:
            user_input = input("USER: ")
            final_response = []
            for chunk in graph.stream( {"messages": [{"role": "user", "content": user_input}],'status':'plan'},
                {'configurable': {'thread_id': "1"},'callbacks':[trace_handler],'metadata':{'langfuse_session_id':id}},
                stream_mode="values",
                subgraphs=True
            ):
                try:
                    logger.debug("============ Chunk response ==========")
                    logger.debug(chunk[-1]['messages'][-1])
                    final_response.append(chunk[-1]['messages'][-1].content)
                except Exception as p:
                    final_response.append(f"Error in response: {p}")
            print("\nMODEL RESPONSE")
            print(final_response[-1])
        except Exception as e:
            logger.info(f'General error: {e}')

async def main():
    async with httpx.AsyncClient(timeout=10.0) as http_client:
        chain = ChainManager(http_client)
        await chain.main_graph()

if __name__ == "__main__":
    asyncio.run(main())
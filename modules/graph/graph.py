import asyncio
import logging,httpx
from langgraph.graph import StateGraph, START, MessagesState, END
from modules.chain_agents.team_leader import TeamLeadAgent
from modules.chain_agents.verification import VerificationAgent
from modules.chain_agents.orchestrator import OrchestratorAgent

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(name=f"Agent.{__name__}")

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
            self.team_lead_host = TeamLeadAgent(self.remote_addresses,self.http_client)
            self.team_lead_host.create_agent()
            self.team_lead = self.team_lead_host.team_lead_agent
            self.orchestrator_hub = OrchestratorAgent()
            self.orchestrator = self.orchestrator_hub.build_main_cluster()
            self.verification_agent = VerificationAgent()
            ChainManager._initialized = True
    
    async def main_graph(self):
        main_graph_builder = StateGraph(MessagesState)
        main_graph_builder.add_node("verify",self.verification_agent.verify_query)
        main_graph_builder.add_node("cluster", self.verification_agent.cluster_agents)
        main_graph_builder.add_node("team_lead",self.orchestrator_hub.call_main_cluster)
        main_graph_builder.add_node("test",self.orchestrator_hub.test)
        main_graph_builder.add_edge(START,"verify")
        main_graph_builder.add_conditional_edges(
            "verify", self.verification_agent.verification_check, {"Fail": END, "Pass": "cluster"}
        )
        main_graph_builder.add_edge("cluster","team_lead")
        main_graph_builder.add_edge("team_lead",END)
        # main_graph_builder.add_edge("test",END)
        graph = main_graph_builder.compile()

        try:
            user_input = input("USER: ")
            final_response = []
            for chunk in graph.stream( {"messages": [{"role": "user", "content": user_input}]},
                {'configurable': {'thread_id': id}},
                stream_mode="values",
                subgraphs=True
            ):
                try:
                    logger.debug("============ Chunk response ==========")
                    logger.debug(chunk[-1]['messages'][-1])
                    final_response.append(chunk[-1]['messages'][-1].content)
                except Exception as p:
                    final_response.append(f"Error in response: {p}")
            print("MODEL RESPONSE")
            print(final_response[-1])
        except Exception as e:
            logger.info(f'General error: {e}')

async def main():
    async with httpx.AsyncClient(timeout=10.0) as http_client:
        chain = ChainManager(http_client)
        await chain.main_graph()

if __name__ == "__main__":
    asyncio.run(main())
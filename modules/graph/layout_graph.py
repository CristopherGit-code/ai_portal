import asyncio
import logging,httpx
from langgraph.graph import StateGraph, START, MessagesState, END
from modules.cluster.verification import VerificationAgent
from modules.cluster.layout import LayoutAgent
from modules.cluster.executor import ExecutorAgent
from modules.util.lang_fuse import FuseConfig
from modules.cluster.agents import WorkerManager
from typing import Annotated
from langchain_core.messages import AnyMessage
from langgraph.graph import add_messages

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(name=f"LAYOUT_GRAPH.{__name__}")

fuse_tracer = FuseConfig()
id = fuse_tracer.generate_id()
trace_handler = fuse_tracer.get_handler()

class LayoutState(MessagesState):
    """ change the status according to execution steps """
    status: str
    plans: Annotated[list[AnyMessage], add_messages]

class ChainManager:
    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ChainManager,cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            self.verification_agent = VerificationAgent()
            self.layout_hub = LayoutAgent()
            self.executor_hub = ExecutorAgent()
            self.workers_hub = WorkerManager()
            ChainManager._initialized = True
    
    def synthesizer(self,state:LayoutState):
        """Synthesize full agent plans form the list"""

        full_plan = []

        for plan in state["plans"]:
            details = plan.content
            full_plan.append(details)

        return {"messages": [{"role": "assistant", "content": full_plan}],'status':'execute','plans':full_plan}

    def build_main_graph(self):
        main_graph_builder = StateGraph(LayoutState)

        main_graph_builder.add_node("verify",self.verification_agent.verify_query)
        main_graph_builder.add_node("layout_plan",self.layout_hub.call_layout_agent)
        main_graph_builder.add_node("layout_select",self.layout_hub.call_layout_agent)
        main_graph_builder.add_node("executor",self.executor_hub.call_executor_agent)

        for agent in self.workers_hub.agent_list:
            main_graph_builder.add_node(agent[0],agent[1])

        main_graph_builder.add_node("synthesizer",self.synthesizer)

        main_graph_builder.add_edge(START,"verify")
        
        main_graph_builder.add_conditional_edges(
            "verify", self.verification_agent.verification_check, {"Fail": END, "Pass": "layout_plan"}
        )

        for agent in self.workers_hub.agent_list:
            main_graph_builder.add_edge("layout_plan",agent[0])
            main_graph_builder.add_edge(agent[0],"synthesizer")

        main_graph_builder.add_edge("synthesizer","layout_select")
        main_graph_builder.add_edge("layout_select","executor")

        graph = main_graph_builder.compile()

        return graph

    async def call_main_graph(self):
        graph = self.build_main_graph()
        try:
            user_input = input("USER: ")
            final_response = []
            async for chunk in graph.astream( {"messages": [{"role": "user", "content": user_input}],'status':'plan'},
                {'configurable': {'thread_id': "1"},'callbacks':[trace_handler],'metadata':{'langfuse_session_id':id}},
                stream_mode="values",
                subgraphs=True
            ):
                try:
                    logger.debug("============ Chunk response ==========\n")
                    logger.debug(chunk[-1])
                    final_response.append(chunk[-1]['messages'][-1].content)
                except Exception as p:
                    final_response.append(f"Error in response: {p}")
            final_text = f"MODEL RESPONSE:\n{final_response[-1]}"
            return final_text
        except Exception as e:
            logger.info(f'General error: {e}')
            return f'General error: {e}'

async def main():
    chain = ChainManager()
    response = await chain.call_main_graph()
    print(response)
        

if __name__ == "__main__":
    asyncio.run(main())
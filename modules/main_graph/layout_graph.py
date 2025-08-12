import asyncio
import logging
from langgraph.graph import StateGraph, START, MessagesState, END
from modules.cluster.verification import VerificationAgent
from modules.cluster.planner import PlannerAgent
from modules.cluster.executor import ExecutorAgent
from modules.util.lang_fuse import FuseConfig
from modules.cluster.agents import WorkerManager
from modules.cluster.layout_builder import LayoutAgent
from typing import Annotated
from langchain_core.messages import AnyMessage
from langgraph.graph import add_messages

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(name=f"LAYOUT_GRAPH.{__name__}")

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
            self.fuse_tracer = FuseConfig()
            self.trace_handler = self.fuse_tracer.get_handler()
            self.verification_agent = VerificationAgent()
            self.planner_hub = PlannerAgent()
            self.executor_hub = ExecutorAgent()
            self.workers_hub = WorkerManager()
            self.layout_hub = LayoutAgent()
            self.build_main_graph()
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
        main_graph_builder.add_node("planner",self.planner_hub.call_planner_agent)
        main_graph_builder.add_node("agent_select",self.planner_hub.call_planner_agent)
        main_graph_builder.add_node("executor",self.executor_hub.call_executor_agent)
        main_graph_builder.add_node("layout",self.layout_hub.call_layout_builder)

        for agent in self.workers_hub.agent_list:
            main_graph_builder.add_node(agent[0],agent[1])

        main_graph_builder.add_node("synthesizer",self.synthesizer)

        main_graph_builder.add_edge(START,"verify")
        
        main_graph_builder.add_conditional_edges(
            "verify", self.verification_agent.verification_check, {"Fail": END, "Pass": "planner"}
        )

        for agent in self.workers_hub.agent_list:
            main_graph_builder.add_edge("planner",agent[0])
            main_graph_builder.add_edge(agent[0],"synthesizer")

        main_graph_builder.add_edge("synthesizer","agent_select")
        main_graph_builder.add_edge("agent_select","executor")
        main_graph_builder.add_edge("executor","layout")

        self.graph = main_graph_builder.compile()

    async def call_main_graph(self, user_input:str)->str:
        try:
            final_response = []
            async for chunk in self.graph.astream( {"messages": [{"role": "user", "content": user_input}],'status':'plan'},
                {'configurable': {'thread_id': "1"},'callbacks':[self.trace_handler],'metadata':{'langfuse_session_id':self.fuse_tracer.generate_id()}},
                stream_mode="values",
                subgraphs=True
            ):
                try:
                    logger.debug("============ Chunk response ==========\n")
                    logger.debug(chunk[-1])
                    final_response.append(chunk[-1]['messages'][-1].content)
                except Exception as p:
                    final_response.append(f"Error in response: {p}")
            return final_response[-1]
        except Exception as e:
            logger.info(f'General error: {e}')
            return f'General error: {e}'

async def main():
    chain = ChainManager()
    response = await chain.call_main_graph()
    print(response)

if __name__ == "__main__":
    asyncio.run(main())
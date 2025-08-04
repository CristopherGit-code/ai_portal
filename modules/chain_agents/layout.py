import asyncio, operator
from typing import Annotated, Any, List, Literal
from typing_extensions import TypedDict
from pydantic import BaseModel, Field
from langgraph.graph import StateGraph, START, END, MessagesState
from langchain_core.messages import HumanMessage,SystemMessage,AIMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Send
from langgraph.prebuilt import create_react_agent
from modules.util.ociopen_ai import LLM_Open_Client
from modules.chain_agents.workers import (
    CinemaAgentPlanner,
    DecorationAgentPlanner,
    FlowerAgentPlanner
)
import asyncio
import logging,httpx
from langgraph.graph import StateGraph, START, MessagesState, END
from modules.chain_agents.verification import VerificationAgent
from modules.chain_agents.orchestrator import OrchestratorAgent
from modules.chain_agents.executor import ExecutorAgent
from modules.util.lang_fuse import FuseConfig
from modules.chain_agents.agents import WorkerManager

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(name=f"GRAPH.{__name__}")

fuse_tracer = FuseConfig()
id = fuse_tracer.generate_id()
trace_handler = fuse_tracer.get_handler()

class LayoutState(MessagesState):
    """ change the status according to execution steps """
    status: str
    current_agent: str

class LayoutAgent:
    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(LayoutAgent,cls).__new__(cls)
        return cls._instance
    
    SYSTEM_INSTRUCTION = (
        "You are a supervisor in charge of different expertise agents, you have two main tasks:\n"
        "1. Request for plans of the agents when the status is 'plan'.\n"
        "Given a user query, ask other agents to first, come up with a plan to solve the user query, add the necessary context.\n"
        "Do not make up any agents, create a GENERAL query with the enough context for any kind of agent to understand the task.\n"
        "DO NOT use any tool calls yet, just create the necessary plan message for the agents."
        "2. You will then receive the different agent plans to address the user query, the 'execute' state, when here, provide instructions to the agents to start working:\n"
        "Select the top agents that address better the user request, considering, relevance, importance of information the agent can provide to the user, agent plan relevance in the context.\n"
        "Once you have selected the agents, pass to the execute phase and create a message for the selected agents.\n"
        "Include all the context, details and information needed in order to proceeed, add as much as details as possible.\n"
        "Actively indicate the selected agents they have to complete the plan suggested. Use the agent tools available to make the calls and confirm the execution.\n"
        "Once the agents finish the tasks, evaluate if the responses fulfill the user request. If context information missing, decide the data in behalf of the user.\n"
        "If an agent is requesting for missing details, act in behalf of the user to reduce the human interaction and call the agent again with the new information.\n"
        "Reduce as much as possible the need of human interaction by taking decisions in behalf of the user. Acknowledge this decisions to the user in the final response.\n"
    )

    def __init__(self):
        if not self._initialized:
            self.workers_handler = WorkerManager()
            self.oci_client = LLM_Open_Client()
            self.model = self.oci_client.build_llm_client()
            self.memory = MemorySaver()
            self.tools = self.workers_handler.agent_tools
            self.layout_agent = create_react_agent(
                model=self.model,
                tools=self.tools,
                checkpointer=self.memory,
                prompt=self.SYSTEM_INSTRUCTION
            )
            LayoutAgent._initialized = True

    def call_layout_agent(self,state:LayoutState)->LayoutState:
        print("==============layout=================\n")
        if state['status'] == 'plan':
            query = state['messages'][0].content
            print(query)
        else:
            query = f"Current agent plans: {state['messages'][-1].content}, current state: {state['status']}. Generate the instructions to be executed by the agents. Select only the best agents to address the user query: {state['messages'][0].content}.Call the tools for each agent to execute the task."
            print(query)
        
        response = self.layout_agent.invoke({"messages": [{"role": "assistant", "content": query}]})
        ans = response['messages'][-1].content
        print(ans)
        
        return {"messages": [{"role": "assistant", "content": ans}],'status':'execute'}

    def test(self,state:LayoutState)->LayoutState:
        return {"messages": [{"role": "assistant", "content": "cinema agent can buy tickets, find movie functions and movies available, flower agent can create bunch of flowers and order flowers, decoration agent is able to make reservations for meetings and decorations for rooms, houses, salons."}],'status':'execute'}
    
async def main_graph():
    layout = LayoutAgent()
    main_graph_builder = StateGraph(LayoutState)

    main_graph_builder.add_node("layout_plan",layout.layout_agent)
    main_graph_builder.add_node("agents", layout.test)
    main_graph_builder.add_node("layout_execute",layout.layout_agent)

    main_graph_builder.add_edge(START,"layout_plan")
    main_graph_builder.add_edge("layout_plan","agents")
    main_graph_builder.add_edge("agents","layout_execute")

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
                logger.debug(chunk)
                final_response.append(chunk[-1]['messages'][-1].content)
            except Exception as p:
                final_response.append(f"Error in response: {p}")
        print("\nMODEL RESPONSE")
        print(final_response[-1])
    except Exception as e:
        logger.info(f'General error: {e}')

async def main():
    await main_graph()

if __name__ == "__main__":
    asyncio.run(main())
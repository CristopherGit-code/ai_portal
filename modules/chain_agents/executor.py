import asyncio
from pydantic import Field
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent
from modules.util.ociopen_ai import LLM_Open_Client
from langchain_core.tools import tool
import asyncio, operator
from typing import Annotated, Any, List
from typing_extensions import TypedDict
from pydantic import BaseModel, Field
from langgraph.graph import StateGraph, START, END, MessagesState
from langchain_core.messages import HumanMessage,SystemMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Send
from langgraph.prebuilt import create_react_agent
from modules.util.ociopen_ai import LLM_Open_Client
from modules.chain_agents.workers import (
    CinemaAgentPlanner,
    DecorationAgentPlanner,
    FlowerAgentPlanner
)

@tool
def cinema_expert(instructions:list[str])->str:
    """ Sends a task to a cinema agent with capabilities to: 
    find available cinema functions, purchase tickets and 
    return a list of available movies """
    return f"Finished the cinema planning request with the steps from {instructions}. All instructions done"

@tool
def decoration_expert(instructions:list[str])->str:
    """ Sends a task to a decoration_agent with capabilities to: 
    list in-place decorations available, confirm a decoration order for meetings, dates or parties"""
    return f"Finished the decoration planning request with the steps from {instructions}. All instructions done"

@tool
def flower_expert(instructions:list[str])->str:
    """ Sends a task to a flower_agent with capabilities to: 
    list available flowers, create a custom bunch of flowers, and
    confirm flower purchase orders"""
    return f"Finished the flower planning request with the steps from {instructions}. All instructions done"

class ExecutorAgent:
    """ Agent expert in planning cinema visits, offers movie information, functions, and ticket purchase """

    _instance = None
    _initialized = False

    def build_system_instruction(self):
        self.SYSTEM_INSTRUCTION = (
        """ 
        You are a supervisor agent orchestrating a team of specialized agents to fulfill complex user requests. 
        Your main objectives are to analyze user queries and agent plans, delegate tasks, complete missing context, and assemble the final response. 
        To interact with agents, you must use the available tools designed for calling each agent.
        Your Responsibilities:
        Analyze Queries and Plans:
        Review the users request and all submitted agent plans.
        Extract required objectives, detect missing information, and outline dependencies.
        Agent Selection & Task Delegation:
        Identify which agents will provide the most impact or value for the users request.
        For each agent you select, use the designated tool interface to issue instructions.
        In each instruction, clearly define the agents scope, required tools, proposed methods, and any relevant context.
        Context Completion:
        If information is incomplete or ambiguous, do not ask the user for clarification.
        Attempt to infer missing details from current context or agent responses.
        Where inference isnt possible, make sensible, user-centered decisions and mark each one clearly as your own choice.
        Workflow & Coordination:
        Manage task sequencing, resolve any dependencies, and order agent execution as needed.
        Coordinate information sharing between agents if helpful.
        Final Response Assembly:
        Collect responses from agents via the tools interfaces.
        Synthesize all results, decisions, and assumptions into a comprehensive, clear final response to the user.
        Guidelines:
        Always use the prescribed tools to interact with team agents—never interact outside these tool interfaces.
        Do not request extra information from the user unless explicitly prompted.
        Be transparent about assumptions or preferences chosen on behalf of the user.
        Provide a clear summary of your process, agent involvement, and any autonomous decisions.
        Strive for clarity, efficiency, and user-centered outcomes.
        Always offer at the end of the work, information to the user about what plans had been completed and a brief worflow details.\n
        Answer in less than 250 words.
        """
    )

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ExecutorAgent,cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            self.cinema_planner = CinemaAgentPlanner()
            self.flower_planner = FlowerAgentPlanner()
            self.deco_planner = DecorationAgentPlanner()
            self.remote_agent_connections:list[dict[str,str]] = [
                {'name': self.cinema_planner.name, 'description': self.cinema_planner.description},
                {'name': self.deco_planner.name, 'description': self.deco_planner.description},
                {'name': self.flower_planner.name, 'description': self.flower_planner.description},
            ]
            self.agent_list:dict[str,Any] = {
                self.cinema_planner.name: self.cinema_planner, 
                self.deco_planner.name: self.deco_planner,
                self.flower_planner.name: self.flower_planner
            }
            self.oci_client = LLM_Open_Client()
            self.model = self.oci_client.build_llm_client()
            self.memory = MemorySaver()
            self.tools = [cinema_expert,flower_expert,decoration_expert]
            self.build_system_instruction()
            self.executor_agent = create_react_agent(
                model=self.model,
                tools=self.tools,
                checkpointer=self.memory,
                prompt=self.SYSTEM_INSTRUCTION,
            )
            ExecutorAgent._initialized = True

async def main():
    main_orchestrator = ExecutorAgent()

    query = r""" {'agent_name': 'cinema_agent', 'agent_plan': 'I will provide tailored suggestions for film-themed entertainment specifically aligned with cinema experiences suitable for a pool party. I specialize in recommending movie screenings, interactive cinema ideas, and ways to incorporate film into your event. I do not handle general pool party organization beyond the cinema theme.', 'agent_tools': "[StructuredTool(name='send_task2_cinema_expert', description='Sends a task to a cinema agent with capabilities to: find available cinema functions, purchase tickets and return a list of available movies', args_schema=<class 'langchain_core.utils.pydantic.send_task2_cinema_expert'>, func=<function send_task2_cinema_expert at 0x0000018E694F0D60>)] Capabilities: Suggest, find movie screenings, recommend film-based interactive experiences, and assist with ticket purchases or scheduling for related cinema events.", 'agent_relevance': 4}

    ---

    For a vibrant pool party:
    Theme: Tropical Luau—think Hawaiian vibes.
    Color Palette: Teal, coral, yellow, and palm green.
    Lighting: String fairy lights, floating pool LEDs, lanterns.
    Props: Inflatable flamingos, pineapples, beach balls, tiki torches.
    Decor Arrangements: Palm-leaf table runners, bamboo centerpieces, and flower garlands on fences.
    Our Services: Themed decor setup, custom backdrops, outdoor-safe lighting, prop rentals, and onsite arrangement.

    If you want to confirm an order or check available decorations, I can send a request for you!

    ---

    {'agent_name': 'flower_agent', 'agent_plan': 'I will provide a range of floral arrangement and botanical theme ideas tailored for a summer pool party. The plan considers durability, vibrant color, and suitability for wet, outdoor environments, recommending both natural and artificial flower solutions for centerpieces, garlands, and floating pool decor. My capabilities include suggesting specific flowers and creative floral decor ideas, and I can assist with custom flower bunch orders or purchases. If users need to proceed with an order, I can utilize my tools to confirm availability and customization requests.', 'agent_tools': "[StructuredTool(name='send_task2_flower_expert', description='Sends a task to a flower_agent with capabilities to: list available flowers, create a custom bunch of flowers, and confirm flower purchase orders')]", 'agent_relevance': 5} """
    
    # Invoke
    state = main_orchestrator.executor_agent.invoke({"messages": [{"role": "user", "content": query}]},
                {'configurable': {'thread_id': "1"}})
    print("Final state ================================")
    print(state["messages"][-1].content)

if __name__ == "__main__":
    asyncio.run(main())
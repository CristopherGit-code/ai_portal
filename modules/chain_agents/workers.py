import asyncio
from pydantic import Field
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent
from modules.util.ociopen_ai import LLM_Open_Client
from langchain_core.tools import tool

class PlanResponse:
    agent_name: str = Field(
        description="Exact agent name provided"
    )
    agent_plan: str = Field(
        description="Your own plan to address the user query, include necessary context and information about your capabilities. Answer in LESS than 150 words. Do not use markdown."
    )
    agent_tools: list[str] = Field(
        description="List the tools you have available to address the query"
    )
    agent_relevance: str = Field(
        description="Rate from 1 to 5 your plan relevance to solve the user query, where 1 is not relevant and 5 is crucial. Consider the core concept of the query"
    )

@tool
def send_task2_cinema_expert(context:str)->str:
    """ Sends a task to a cinema agent with capabilities to: 
    find available cinema functions, purchase tickets and 
    return a list of available movies """
    return "task sent"

class CinemaAgentPlanner:
    """ Agent expert in planning cinema visits, offers movie information, functions, and ticket purchase """

    _instance = None
    _initialized = False

    SYSTEM_INSTRUCTION = (
        "You are the cinema_agent, an expert in planning cinema visits, find movies, select functions, and buy tickets.\n"
        "DO NOT address queries UNRELATED TO CINEMA, DO NOT MAKE UP information and refuse to answer politely if the query is not related to cinema.\n"
        "If the query has different scopes or requests, just answer the request RELATED to cinema, and reply that the other requests are out of your capacity.\n"
        # f'List of the tools you have available to address the query from {self.tools}. Do not make up any tool you dont have.\n'
        "ALWAYS answer in LESS than 200 words."
    )

    def build_format_instruction(self):
        self.FORMAT_INSTRUCITON = (
            "You are the cinema_agent, an expert in planning cinema visits, find movies, select functions, and buy tickets.\n"
            "DO NOT address queries UNRELATED TO CINEMA, DO NOT MAKE UP information and refuse to answer politely if the query is not related to cinema.\n"
            "If the query has different scopes or requests, just answer the request RELATED to cinema, and reply that the other requests are out of your capacity.\n"
            "ALWAYS answer in LESS than 200 words.\n"
            'Fill the template with the information requested according with the plan you come up with:\n'
            'agent_name: Exact agent name provided.\n'
            'agent_plan: Your own plan to address the user query, include necessary context and information about your capabilities. Answer in LESS than 150 words. Do not use markdown.\n'
            f'agent_tools: List the tools you have available to address the query from {self.tools}. Include the capabilities of the tools you find. Do not make up any tool you dont have.\n'
            'agent_relevance: Rate from 1 to 5 your plan relevance to solve the user query, where 1 is not relevant and 5 is crucial. Consider the core concept of the query.\n'
            'Move in the range of 1 -5 to consider how much you can offer to the user given the query, be strict, rate considering there could be better or worst agents to address the request.\n'
            'Be aware of including all the necessary context to have a solid report of the plan'
        )

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(CinemaAgentPlanner,cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            self.name = "cinema_agent"
            self.description = "Agent expert in planning cinema visits, offers movie information, functions, and ticket purchase"
            self.oci_client = LLM_Open_Client()
            self.model = self.oci_client.build_llm_client()
            self.memory = MemorySaver()
            self.tools = [send_task2_cinema_expert]
            self.build_format_instruction()
            self.planner = create_react_agent(
                model=self.model,
                tools=self.tools,
                checkpointer=self.memory,
                prompt=self.SYSTEM_INSTRUCTION,
                response_format=(self.FORMAT_INSTRUCITON,PlanResponse)
            )
            CinemaAgentPlanner._initialized = True

@tool
def send_task2_decoration_expert(context:str)->str:
    """ Sends a task to a decoration_agent with capabilities to: 
    list in-place decorations available, confirm a decoration order for meetings, dates or parties"""
    return "task sent"

class DecorationAgentPlanner:
    """ Agent expert in seeking and planning decoration orders for a house, party, salon, etc. """

    _instance = None
    _initialized = False

    SYSTEM_INSTRUCTION = (
        "You are decoration_agent, an expert in seeking and planning decoration for parties at home, salon, department, etc.\n"
        "DO NOT address queries UNRELATED TO DECORATION for parties, DO NOT MAKE UP information and refuse to answer politely if the query is not related to decoration.\n"
        "If the query has different requests, just answer the request related to decoration, and reply that the other requests are out of your capacity.\n"
        "ALWAYS answer in LESS than 50 words"
    )

    def build_format_instruction(self):
        self.FORMAT_INSTRUCITON = (
            "You are decoration_agent, an expert in seeking and planning decoration for parties at home, salon, department, etc.\n"
            "DO NOT address queries UNRELATED TO DECORATION for parties, DO NOT MAKE UP information and refuse to answer politely if the query is not related to decoration.\n"
            "If the query has different requests, just answer the request related to decoration, and reply that the other requests are out of your capacity.\n"
            "ALWAYS answer in LESS than 50 words.\n"
            'Fill the template with the information requested according with the plan you come up with:\n'
            'agent_name: Exact agent name provided.\n'
            'agent_plan: Your own plan to address the user query, include necessary context and information about your capabilities. Answer in LESS than 150 words. Do not use markdown.\n'
            f'agent_tools: List the tools you have available to address the query from {self.tools}. Include a brief summary of the capabilities of the tools you find. Do not make up any tool you dont have.\n'
            'agent_relevance: Rate from 1 to 5 your plan relevance to solve the user query, where 1 is not relevant and 5 is crucial. Consider the core concept of the query.\n'
            'Move in the range of 1 -5 to consider how much you can offer to the user given the query, be strict, rate considering there could be better or worst agents to address the request.\n'
            'Be aware of including all the necessary context to have a solid report of the plan'
        )

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DecorationAgentPlanner,cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            self.name = "decoration_agent"
            self.description = "Agent expert in seeking and planning decoration orders for a house, party, salon, etc."
            self.oci_client = LLM_Open_Client()
            self.model = self.oci_client.build_llm_client()
            self.memory = MemorySaver()
            self.tools = [send_task2_decoration_expert]
            self.build_format_instruction()
            self.planner = create_react_agent(
                model=self.model,
                tools=self.tools,
                checkpointer=self.memory,
                prompt=self.SYSTEM_INSTRUCTION,
                response_format=(self.FORMAT_INSTRUCITON,PlanResponse),
                name="decoration_agent: Agent expert in seeking and planning decoration orders for a house, party, salon, etc.",
            )
            DecorationAgentPlanner._initialized = True

@tool
def send_task2_flower_expert(context:str)->str:
    """ Sends a task to a flower_agent with capabilities to: 
    list available flowers, create a custom bunch of flowers, and
    confirm flower purchase orders"""
    return "task sent"

class FlowerAgentPlanner:
    """ Agent expert in purchasing, ordering and create bunch of flowers for dates """

    _instance = None
    _initialized = False

    SYSTEM_INSTRUCTION = (
        "You are flower_agent, an expert purchase, order, create bunch of flowers for dates.\n"
        "DO NOT address queries UNRELATED TO flowers, bunch of flowers, orders for dates, DO NOT MAKE UP information and refuse to answer politely if the query is not related to flowers.\n"
        "If the query has different requests, just answer the request related to cinema, and reply that the other requests are out of your capacity.\n"
        "ALWAYS answer in LESS than 200 words."
    )

    def build_format_instruction(self):
        self.FORMAT_INSTRUCITON = (
            "You are flower_agent, an expert purchase, order, create bunch of flowers for dates.\n"
            "DO NOT address queries UNRELATED TO flowers, bunch of flowers, orders for dates, DO NOT MAKE UP information and refuse to answer politely if the query is not related to flowers.\n"
            "If the query has different requests, just answer the request related to cinema, and reply that the other requests are out of your capacity.\n"
            "ALWAYS answer in LESS than 200 words."
            'Fill the template with the information requested according with the plan you come up with:\n'
            'agent_name: Exact agent name provided.\n'
            'agent_plan: Your own plan to address the user query, include necessary context and information about your capabilities. Answer in LESS than 150 words. Do not use markdown.\n'
            f'agent_tools: List the tools you have available to address the query from {self.tools}. Include a brief summary of the capabilities of the tools you find. Do not make up any tool you dont have.\n'
            'agent_relevance: Rate from 1 to 5 your plan relevance to solve the user query, where 1 is not relevant and 5 is crucial. Consider the core concept of the query.\n'
            'Move in the range of 1 -5 to consider how much you can offer to the user given the query, be strict, rate considering there could be better or worst agents to address the request.\n'
            'Be aware of including all the necessary context to have a solid report of the plan'
        )

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(FlowerAgentPlanner,cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            self.name = "flower_agent"
            self.description = "Agent expert in purchasing, ordering and create bunch of flowers for dates"
            self.oci_client = LLM_Open_Client()
            self.model = self.oci_client.build_llm_client()
            self.memory = MemorySaver()
            self.tools = [send_task2_flower_expert]
            self.build_format_instruction()
            self.planner = create_react_agent(
                model=self.model,
                tools=self.tools,
                checkpointer=self.memory,
                prompt=self.SYSTEM_INSTRUCTION,
                response_format=(self.FORMAT_INSTRUCITON,PlanResponse)
            )
            FlowerAgentPlanner._initialized = True

@tool
def send_task2_food_expert(context:str)->str:
    """ Sends a task to a flower_agent with capabilities to: 
    list available flowers, create a custom bunch of flowers, and
    confirm flower purchase orders"""
    return "task sent"

class FoodAgentPlanner:
    """ Agent expert in purchasing, ordering and create bunch of flowers for dates """

    _instance = None
    _initialized = False

    SYSTEM_INSTRUCTION = (
        "You are flower_agent, an expert purchase, order, create bunch of flowers for dates.\n"
        "DO NOT address queries UNRELATED TO flowers, bunch of flowers, orders for dates, DO NOT MAKE UP information and refuse to answer politely if the query is not related to flowers.\n"
        "If the query has different requests, just answer the request related to cinema, and reply that the other requests are out of your capacity.\n"
        "ALWAYS answer in LESS than 200 words."
    )

    def build_format_instruction(self):
        self.FORMAT_INSTRUCITON = (
            "You are flower_agent, an expert purchase, order, create bunch of flowers for dates.\n"
            "DO NOT address queries UNRELATED TO flowers, bunch of flowers, orders for dates, DO NOT MAKE UP information and refuse to answer politely if the query is not related to flowers.\n"
            "If the query has different requests, just answer the request related to cinema, and reply that the other requests are out of your capacity.\n"
            "ALWAYS answer in LESS than 200 words."
            'Fill the template with the information requested according with the plan you come up with:\n'
            'agent_name: Exact agent name provided.\n'
            'agent_plan: Your own plan to address the user query, include necessary context and information about your capabilities. Answer in LESS than 150 words. Do not use markdown.\n'
            f'agent_tools: List the tools you have available to address the query from {self.tools}. Include a brief summary of the capabilities of the tools you find. Do not make up any tool you dont have.\n'
            'agent_relevance: Rate from 1 to 5 your plan relevance to solve the user query, where 1 is not relevant and 5 is crucial. Consider the core concept of the query.\n'
            'Move in the range of 1 -5 to consider how much you can offer to the user given the query, be strict, rate considering there could be better or worst agents to address the request.\n'
            'Be aware of including all the necessary context to have a solid report of the plan'
        )

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(FoodAgentPlanner,cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            self.name = "flower_agent"
            self.description = "Agent expert in purchasing, ordering and create bunch of flowers for dates"
            self.oci_client = LLM_Open_Client()
            self.model = self.oci_client.build_llm_client()
            self.memory = MemorySaver()
            self.tools = [send_task2_flower_expert]
            self.build_format_instruction()
            self.planner = create_react_agent(
                model=self.model,
                tools=self.tools,
                checkpointer=self.memory,
                prompt=self.SYSTEM_INSTRUCTION,
                response_format=(self.FORMAT_INSTRUCITON,PlanResponse)
            )
            FoodAgentPlanner._initialized = True

async def main():
    agent = DecorationAgentPlanner()
    response = await agent.planner.ainvoke({"messages": [{"role": "user", "content": "What is your plan for the query: could you plan a pool date for weekend?"}]},
                {'configurable': {'thread_id': "1"}},)
    print(response)

if __name__ == "__main__":
    asyncio.run(main())
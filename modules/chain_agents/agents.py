from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent
from modules.util.ociopen_ai import LLM_Open_Client
from langchain_core.tools import tool, BaseTool
from langgraph.graph import MessagesState
from typing import Annotated
from langchain_core.messages import AnyMessage
from langgraph.graph import add_messages

class LayoutState(MessagesState):
    """ change the status according to execution steps """
    status: str
    plans: Annotated[list[AnyMessage], add_messages]

@tool
def send_task2_cinema_expert(context:str)->str:
    """ Sends a task to a cinema agent with capabilities to: 
    find available cinema functions, purchase tickets and 
    return a list of available movies """
    return "task sent"

class CinemaAgent:
    """ Agent expert in planning cinema visits, offers movie information, functions, and ticket purchase """

    _instance = None
    _initialized = False

    SYSTEM_INSTRUCTION = (
        "You are the cinema_agent, an expert in planning cinema visits, find movies, select functions, and buy tickets.\n"
        "DO NOT address queries UNRELATED TO CINEMA, DO NOT MAKE UP information and refuse to answer politely if the query is not related to cinema.\n"
        "If the query has different scopes or requests, just answer the request RELATED to cinema, and reply that the other requests are out of your capacity.\n"
        "ALWAYS answer in LESS than 200 words."
    )

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(CinemaAgent,cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            self.name = "cinema_agent"
            self.oci_client = LLM_Open_Client()
            self.model = self.oci_client.build_llm_client()
            self.memory = MemorySaver()
            self.tools = [send_task2_cinema_expert]
            self.agent = create_react_agent(
                model=self.model,
                tools=self.tools,
                checkpointer=self.memory,
                prompt=self.SYSTEM_INSTRUCTION
            )
            CinemaAgent._initialized = True

    def cinema_plan(self,state:LayoutState)->LayoutState:
        """ Verifies the user query to be aligned to the topic """

        query = state['messages'][-1].content
        response = self.agent.invoke({"messages": [{"role": "assistant", "content": query}]})
        ans = response['messages'][-1].content
        
        return {"messages": [{"role": "assistant", "content": ans}],'plans':ans}

@tool
def send_task2_cinema_expert(context:str)->str:
    """ Sends a task to a cinema agent with capabilities to: 
    find available cinema functions, purchase tickets and 
    return a list of available movies """
    return "task sent"

class FoodAgent:
    """ Agent expert in getting food options, snacks, canapes, can purchase food orders """

    _instance = None
    _initialized = False

    SYSTEM_INSTRUCTION = (
        "You are the food_agent, an expert in getting food options, snacks, canapes, can purchase food orders.\n"
        "DO NOT address queries UNRELATED TO FOOD, DO NOT MAKE UP information and refuse to answer politely if the query is not related to food.\n"
        "If the query has different scopes or requests, just answer the request RELATED to food, and reply that the other requests are out of your capacity.\n"
        "ALWAYS answer in LESS than 200 words."
    )

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(FoodAgent,cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            self.name = "food_agent"
            self.oci_client = LLM_Open_Client()
            self.model = self.oci_client.build_llm_client()
            self.memory = MemorySaver()
            self.tools = [send_task2_cinema_expert]
            self.agent = create_react_agent(
                model=self.model,
                tools=self.tools,
                checkpointer=self.memory,
                prompt=self.SYSTEM_INSTRUCTION
            )
            FoodAgent._initialized = True

    def food_plan(self,state:LayoutState)->LayoutState:
        """ Verifies the user query to be aligned to the topic """

        query = state['messages'][-1].content
        response = self.agent.invoke({"messages": [{"role": "assistant", "content": query}]})
        ans = response['messages'][-1].content
        
        return {"messages": [{"role": "assistant", "content": ans}],'plans':ans}
    
@tool
def call_cinema_agent(instruction:str,context:str)->str:
    """ Calls the cinema agent with the specific instructions and context given """

    cinema_agent = CinemaAgent()
    response = cinema_agent.agent.invoke({"messages": [{"role": "user", "content": f"Given the context: {context}, work to fulfill the request: {instruction}. Do not make up information and provide all the data that you hava available"}]})

    return response['messages'][-1].content

@tool
def call_food_agent(instruction:str,context:str)->str:
    """ Calls the Food agent with the specific instructions and context given """

    food_agent = FoodAgent()
    response = food_agent.agent.invoke({"messages": [{"role": "user", "content": f"Given the context: {context}, work to fulfill the request: {instruction}. Do not make up information and provide all the data that you hava available"}]})

    return response['messages'][-1].content
    
class WorkerManager:
    """ Module to manage worker agents and keep the connections """
    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(WorkerManager,cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            self.cinema_agent = CinemaAgent()
            self.food_agent = FoodAgent()
            self.agent_list = [
                (self.cinema_agent.name,self.cinema_agent.cinema_plan),
                (self.food_agent.name,self.food_agent.food_plan),
            ]
            self.agent_tools:list[BaseTool] = [call_cinema_agent,call_food_agent]
            WorkerManager._initialized = True
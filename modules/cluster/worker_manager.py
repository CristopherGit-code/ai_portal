from langchain_core.tools import tool, BaseTool
import logging
from modules.cluster.workers.cinema_agent import CinemaAgent
from modules.cluster.workers.decoration_agent import DecorationAgent
from modules.cluster.workers.file_agent import FileAgent
from modules.cluster.workers.food_agent import FoodAgent
from modules.cluster.workers.weather_agent import WeatherAgent

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(name=f"AGENTS_CLUSTER.{__name__}")

@tool
async def call_cinema_agent(instruction:str,context:str)->str:
    """ Calls the cinema agent with the specific instructions and context given """

    cinema_agent = CinemaAgent()
    response = await cinema_agent.agent.ainvoke({"messages": [{"role": "user", "content": f"Given the context: {context}, work to fulfill the request: {instruction}. Do not make up information and provide all the data that you hava available"}]})

    return response['messages'][-1].content

@tool
async def call_food_agent(instruction:str,context:str)->str:
    """ Calls the Food agent with the specific instructions and context given """

    food_agent = FoodAgent()
    response = await food_agent.agent.ainvoke({"messages": [{"role": "user", "content": f"Given the context: {context}, work to fulfill the request: {instruction}. Do not make up information and provide all the data that you hava available"}]})

    return response['messages'][-1].content

@tool
async def call_decoration_agent(instruction:str,context:str)->str:
    """ Calls the decoration agent with the specific instructions and context given """

    decoration_agent = DecorationAgent()
    response = await decoration_agent.agent.ainvoke({"messages": [{"role": "user", "content": f"Given the context: {context}, work to fulfill the request: {instruction}. Do not make up information and provide all the data that you hava available"}]})

    return response['messages'][-1].content

@tool
async def call_weather_agent(instruction:str,context:str)->str:
    """ Calls the weather agent with the specific instructions and context given """

    weather_agent = WeatherAgent()
    response = await weather_agent.agent.ainvoke({"messages": [{"role": "user", "content": f"Given the context: {context}, work to fulfill the request: {instruction}. Do not make up information and provide all the data that you hava available"}]})

    return response['messages'][-1].content
    
@tool
async def call_file_agent(instruction:str,context:str)->str:
    """ Calls the file agent with the specific instructions and context given """

    file_agent = FileAgent()
    response = await file_agent.agent.ainvoke({"messages": [{"role": "user", "content": f"Given the context: {context}, work to fulfill the request: {instruction}. Do not make up information and provide all the data that you hava available"}]})

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
            self.decoration_agent = DecorationAgent()
            self.weather_agent = WeatherAgent()
            self.file_agent = FileAgent()
            self.agent_list = [
                (self.cinema_agent.name,self.cinema_agent.cinema_plan),
                (self.food_agent.name,self.food_agent.food_plan),
                (self.decoration_agent.name,self.decoration_agent.decoration_plan),
                (self.weather_agent.name,self.weather_agent.weather_plan),
                (self.file_agent.name,self.file_agent.file_plan),
            ]
            self.agent_tools:list[BaseTool] = [
                call_cinema_agent,
                call_food_agent,
                call_decoration_agent,
                call_weather_agent,
                call_file_agent
            ]
            WorkerManager._initialized = True
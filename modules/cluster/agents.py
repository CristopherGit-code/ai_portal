from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent
from modules.util.ociopen_ai import LLM_Open_Client
from langchain_core.tools import tool, BaseTool
from langgraph.graph import MessagesState
from typing import Annotated, Any
from langchain_core.messages import AnyMessage
from langgraph.graph import add_messages
from uuid import uuid4
import httpx
from a2a.client import A2ACardResolver, A2AClient
from a2a.types import (
    AgentCard,
    MessageSendParams,
    SendMessageRequest,
)
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(name=f"AGENTS_CLUSTER.{__name__}")

class LayoutState(MessagesState):
    """ change the status according to execution steps """
    status: str
    plans: Annotated[list[AnyMessage], add_messages]

async def call_a2a_agent(agent_name:str,message:str)->str:
    PUBLIC_AGENT_CARD_PATH = '/.well-known/agent.json'
    EXTENDED_AGENT_CARD_PATH = '/agent/authenticatedExtendedCard'

    remote_addresses = {
        'cinema_agent':'http://localhost:9999/',
        'decoration_agent':'http://localhost:9998/',
        'food_agent':'http://localhost:9997/',
        'weather_agent':'http://localhost:9996/',
        'file_agent':'http://localhost:9995/'
    }
    logger.debug("\na2a call function ===================")
    logger.debug(remote_addresses.keys())

    try:
        if agent_name not in remote_addresses.keys():
            return f"Wrong agent name, agent names are: {remote_addresses.keys()}"
    except Exception as e:
        logger.debug(e)
    
    base_url = remote_addresses[agent_name]
    timeout = 30.0

    async with httpx.AsyncClient() as httpx_client:
        resolver = A2ACardResolver(
            httpx_client=httpx_client,
            base_url=base_url,
        )
        final_agent_card_to_use: AgentCard | None = None

        try:
            _public_card = (await resolver.get_agent_card())
            final_agent_card_to_use = _public_card
            logger.info('\nUsing PUBLIC agent card for client initialization (default).')

            if _public_card.supports_authenticated_extended_card:
                try:
                    auth_headers_dict = {
                        'Authorization': 'Bearer dummy-token-for-extended-card'
                    }
                    _extended_card = await resolver.get_agent_card(
                        relative_card_path=EXTENDED_AGENT_CARD_PATH,
                        http_kwargs={'headers': auth_headers_dict},
                    )
                    final_agent_card_to_use = (_extended_card)
                    logger.info('\nUsing AUTHENTICATED EXTENDED agent card for client')
                except Exception as e_extended:
                    logger.warning(
                        f'Failed to fetch extended agent card: {e_extended}. '
                        'Will proceed with public card.',
                        exc_info=True,
                    )
            elif (_public_card):
                logger.info('\nPublic card does not indicate support for an extended card. Using public card.')

        except Exception as e:
            logger.error(f'Critical error fetching public agent card: {e}', exc_info=True)
            raise RuntimeError('Failed to fetch the public agent card. Cannot continue.') from e

        client = A2AClient(httpx_client=httpx_client, agent_card=final_agent_card_to_use)
        logger.info('A2AClient initialized.')

        send_message_payload: dict[str, Any] = {
            'message': {
                'role': 'user',
                'parts': [
                    {'kind': 'text', 'text': message}
                ],
                'message_id': uuid4().hex,
            },
        }
        request = SendMessageRequest(
            id=str(uuid4()), params=MessageSendParams(**send_message_payload)
        )

        logger.debug("First response:\n")
        response = await client.send_message(request, http_kwargs={"timeout": timeout})
        ans = response.model_dump(mode='json', exclude_none=True)
        logger.debug(ans)

        return str(ans)
    
# A2A call -------------------------------------------------------------

@tool
async def send_task2_cinema_expert(agent_name:str,full_context:str)->str:
    """ Sends a task to a cinema_agent with capabilities to: 
    find available cinema functions, purchase tickets (including money usage) and 
    return a list of available movies. Agent is not capable to do tasks outside the cinema location.
    Agent name: cinema_agent
    """
    response = await call_a2a_agent(agent_name,full_context)
    return response

class CinemaAgent:
    """ Agent expert in planning cinema visits, offers movie information, functions, and ticket purchase """

    _instance = None
    _initialized = False

    SYSTEM_INSTRUCTION = (
        """
        You are a cinema agent agent with specific expertise in cinema and tool access for cinema related tasks. Follow these guidelines for every incoming request:

        1. Plan Request Handling:
        - If the message asks you to come up with a plan or propose a solution:
        - Do not make any tool calls or perform actions.
        - Clearly acknowledge your own main skills, capabilities, and area of expertise.
        - Generate a detailed plan for addressing the user query, focusing only on tasks within your actual expertise and using tools you can genuinely access.
        - If the user query includes topics outside your main expertise, only address the sections related to your scope—ignore unrelated subjects.

        2. Execute/Task Request Handling
        - If the message instructs you to execute a plan or follow a series of tasks:
        - Begin work immediately using ONLY your available tools and within your expertise.
        - For tasks involving multiple topics, address strictly the portions that align with your domain.
        - Ignore unrelated or out-of-scope subjects in the request.
        
        User Interaction Minimization:
        - Reduce unnecessary human interaction by acting on behalf of the user wherever appropriate.
        - Always clearly inform the user of any decisions or actions you have taken on their behalf.
        
        GENERAL RULES:
        - Always act only within your true capabilities and main area of expertise.
        - If the request is few related or not related to your scope, inform in main scope that your apportation to the plan or tasks is not relevant to the user query.
        - Never attempt to address topics or perform actions outside your practical scope or tool access.
        - Clearly communicate what portion of the query you are addressing and what is omitted due to scope limitations.
        - ALWAYS use the tools you have available to answer the execution process
        - If the tool results in an error, DO NOT make up information, just inform the agent can not respond
        """
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
async def send_task2_food_expert(agent_name:str,full_context:str)->str:
    """ Sends a task to a food_agent with capabilities to: 
    find available food restaurants, purchase snacks (including money usage) and 
    return a list of available canapes
    Agent name: food_agent
    """
    response = await call_a2a_agent(agent_name,full_context)
    return response

class FoodAgent:
    """ Agent expert in getting food options, snacks, canapes, can purchase food orders """

    _instance = None
    _initialized = False

    SYSTEM_INSTRUCTION = (
        """
        You are a food agent agent with specific expertise in food and tool access for food related tasks. Follow these guidelines for every incoming request:

        1. Plan Request Handling:
        - If the message asks you to come up with a plan or propose a solution:
        - Do not make any tool calls or perform actions.
        - Clearly acknowledge your own main skills, capabilities, and area of expertise.
        - Generate a detailed plan for addressing the user query, focusing only on tasks within your actual expertise and using tools you can genuinely access.
        - If the user query includes topics outside your main expertise, only address the sections related to your scope—ignore unrelated subjects.

        2. Execute/Task Request Handling
        - If the message instructs you to execute a plan or follow a series of tasks:
        - Begin work immediately using ONLY your available tools and within your expertise.
        - For tasks involving multiple topics, address strictly the portions that align with your domain.
        - Ignore unrelated or out-of-scope subjects in the request.
        
        User Interaction Minimization:
        - Reduce unnecessary human interaction by acting on behalf of the user wherever appropriate.
        - Always clearly inform the user of any decisions or actions you have taken on their behalf.
        
        GENERAL RULES:
        - Always act only within your true capabilities and main area of expertise.
        - If the request is few related or not related to your scope, inform in main scope that your apportation to the plan or tasks is not relevant to the user query.
        - Never attempt to address topics or perform actions outside your practical scope or tool access.
        - Clearly communicate what portion of the query you are addressing and what is omitted due to scope limitations.
        - ALWAYS use the tools you have available to answer the execution process
        - If the tool results in an error, DO NOT make up information, just inform the agent can not respond
        """
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
            self.tools = [send_task2_food_expert]
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
async def send_task2_decoration_expert(agent_name:str,full_context:str)->str:
    """ Sends a task to a decoration_agent with capabilities to: 
    list decorations possible to borrow and
    buy and confirm the order for decoration in a certan space (also including money usage)
    Agent name: decoration_agent
    """
    response = await call_a2a_agent(agent_name,full_context)
    return response

class DecorationAgent:
    """ Agent expert in seeking and planning decoration orders for a house, party, salon, etc. """

    _instance = None
    _initialized = False

    SYSTEM_INSTRUCTION = (
        """
        You are a decoration agent with specific expertise in decoration and tool access for decoration related tasks. Follow these guidelines for every incoming request:

        1. Plan Request Handling:
        - If the message asks you to come up with a plan or propose a solution:
        - Do not make any tool calls or perform actions.
        - Clearly acknowledge your own main skills, capabilities, and area of expertise.
        - Generate a detailed plan for addressing the user query, focusing only on tasks within your actual expertise and using tools you can genuinely access.
        - If the user query includes topics outside your main expertise, only address the sections related to your scope—ignore unrelated subjects.

        2. Execute/Task Request Handling
        - If the message instructs you to execute a plan or follow a series of tasks:
        - Begin work immediately using ONLY your available tools and within your expertise.
        - For tasks involving multiple topics, address strictly the portions that align with your domain.
        - Ignore unrelated or out-of-scope subjects in the request.
        
        User Interaction Minimization:
        - Reduce unnecessary human interaction by acting on behalf of the user wherever appropriate.
        - Always clearly inform the user of any decisions or actions you have taken on their behalf.
        
        GENERAL RULES:
        - Always act only within your true capabilities and main area of expertise.
        - If the request is few related or not related to your scope, inform in main scope that your apportation to the plan or tasks is not relevant to the user query.
        - Never attempt to address topics or perform actions outside your practical scope or tool access.
        - Clearly communicate what portion of the query you are addressing and what is omitted due to scope limitations.
        - ALWAYS use the tools you have available to answer the execution process
        - If the tool results in an error, DO NOT make up information, just inform the agent can not respond
        """
    )

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DecorationAgent,cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            self.name = "decoration_agent"
            self.oci_client = LLM_Open_Client()
            self.model = self.oci_client.build_llm_client()
            self.memory = MemorySaver()
            self.tools = [send_task2_decoration_expert]
            self.agent = create_react_agent(
                model=self.model,
                tools=self.tools,
                checkpointer=self.memory,
                prompt=self.SYSTEM_INSTRUCTION
            )
            DecorationAgent._initialized = True

    def decoration_plan(self,state:LayoutState)->LayoutState:
        """ Verifies the user query to be aligned to the topic """

        query = state['messages'][-1].content
        response = self.agent.invoke({"messages": [{"role": "assistant", "content": query}]})
        ans = response['messages'][-1].content
        
        return {"messages": [{"role": "assistant", "content": ans}],'plans':ans}
    
@tool
async def send_task2_weather_expert(agent_name:str,full_context:str)->str:
    """ Sends a task to a weather_agent with capabilities to: 
    get weather alerts from US states in real time,
    get forecast for US states in real time (two letter abreviation letter for state).
    Agent name: weather_agent
    """
    response = await call_a2a_agent(agent_name,full_context)
    return response

class WeatherAgent:
    """ Agent that is expert in getting weather data in real time like forecast, and weather alerts """

    _instance = None
    _initialized = False

    SYSTEM_INSTRUCTION = (
        """
        You are a weather agent with specific expertise in weather and tool access for weather related tasks. Follow these guidelines for every incoming request:

        1. Plan Request Handling:
        - If the message asks you to come up with a plan or propose a solution:
        - Do not make any tool calls or perform actions.
        - Clearly acknowledge your own main skills, capabilities, and area of expertise.
        - Generate a detailed plan for addressing the user query, focusing only on tasks within your actual expertise and using tools you can genuinely access.
        - If the user query includes topics outside your main expertise, only address the sections related to your scope—ignore unrelated subjects.

        2. Execute/Task Request Handling
        - If the message instructs you to execute a plan or follow a series of tasks:
        - Begin work immediately using ONLY your available tools and within your expertise.
        - For tasks involving multiple topics, address strictly the portions that align with your domain.
        - Ignore unrelated or out-of-scope subjects in the request.
        
        User Interaction Minimization:
        - Reduce unnecessary human interaction by acting on behalf of the user wherever appropriate.
        - Always clearly inform the user of any decisions or actions you have taken on their behalf.
        
        GENERAL RULES:
        - Always act only within your true capabilities and main area of expertise.
        - If the request is few related or not related to your scope, inform in main scope that your apportation to the plan or tasks is not relevant to the user query.
        - Never attempt to address topics or perform actions outside your practical scope or tool access.
        - Clearly communicate what portion of the query you are addressing and what is omitted due to scope limitations.
        - ALWAYS use the tools you have available to answer the execution process
        - If the tool results in an error, DO NOT make up information, just inform the agent can not respond
        """
    )

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(WeatherAgent,cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            self.name = "weather_agent"
            self.oci_client = LLM_Open_Client()
            self.model = self.oci_client.build_llm_client()
            self.memory = MemorySaver()
            self.tools = [send_task2_weather_expert]
            self.agent = create_react_agent(
                model=self.model,
                tools=self.tools,
                checkpointer=self.memory,
                prompt=self.SYSTEM_INSTRUCTION
            )
            WeatherAgent._initialized = True

    def weather_plan(self,state:LayoutState)->LayoutState:
        """ Generates a plan for the weather agent """

        query = state['messages'][-1].content
        response = self.agent.invoke({"messages": [{"role": "assistant", "content": query}]})
        ans = response['messages'][-1].content
        
        return {"messages": [{"role": "assistant", "content": ans}],'plans':ans}
    
@tool
async def send_task2_file_expert(agent_name:str,full_context:str)->str:
    """ Sends a task to a file_agent with capabilities to: 
    manage user files
    create new files, write content to new files, delete files, rename files, search for a file.
    Agent name: file_agent
    """
    response = await call_a2a_agent(agent_name,full_context)
    return response

class FileAgent:
    """ Agent that is expert in managing user files for example, create, write, delete, rename files """

    _instance = None
    _initialized = False

    SYSTEM_INSTRUCTION = (
        """
        You are a file agent with specific expertise in files and local file management, tool access for file related tasks. Follow these guidelines for every incoming request:

        1. Plan Request Handling:
        - If the message asks you to come up with a plan or propose a solution:
        - Do not make any tool calls or perform actions.
        - Clearly acknowledge your own main skills, capabilities, and area of expertise.
        - Generate a detailed plan for addressing the user query, focusing only on tasks within your actual expertise and using tools you can genuinely access.
        - If the user query includes topics outside your main expertise, only address the sections related to your scope—ignore unrelated subjects.

        2. Execute/Task Request Handling
        - If the message instructs you to execute a plan or follow a series of tasks:
        - Begin work immediately using ONLY your available tools and within your expertise.
        - For tasks involving multiple topics, address strictly the portions that align with your domain.
        - Ignore unrelated or out-of-scope subjects in the request.
        
        User Interaction Minimization:
        - Reduce unnecessary human interaction by acting on behalf of the user wherever appropriate.
        - Always clearly inform the user of any decisions or actions you have taken on their behalf.
        
        GENERAL RULES:
        - Always act only within your true capabilities and main area of expertise.
        - If the request is few related or not related to your scope, inform in main scope that your apportation to the plan or tasks is not relevant to the user query.
        - Never attempt to address topics or perform actions outside your practical scope or tool access.
        - Clearly communicate what portion of the query you are addressing and what is omitted due to scope limitations.
        - ALWAYS use the tools you have available to answer the execution process
        - If the tool results in an error, DO NOT make up information, just inform the agent can not respond
        """
    )

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(FileAgent,cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            self.name = "file_agent"
            self.oci_client = LLM_Open_Client()
            self.model = self.oci_client.build_llm_client()
            self.memory = MemorySaver()
            self.tools = [send_task2_file_expert]
            self.agent = create_react_agent(
                model=self.model,
                tools=self.tools,
                checkpointer=self.memory,
                prompt=self.SYSTEM_INSTRUCTION
            )
            FileAgent._initialized = True

    def file_plan(self,state:LayoutState)->LayoutState:
        """ Generates a plan for the file agent """

        query = state['messages'][-1].content
        response = self.agent.invoke({"messages": [{"role": "assistant", "content": query}]})
        ans = response['messages'][-1].content
        
        return {"messages": [{"role": "assistant", "content": ans}],'plans':ans}

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
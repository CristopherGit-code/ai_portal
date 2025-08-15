from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent
from modules.util.ociopen_ai import LLM_Open_Client
from langchain_core.tools import tool
from modules.util.states import LayoutState
from modules.util.a2a_calls import call_a2a_agent

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
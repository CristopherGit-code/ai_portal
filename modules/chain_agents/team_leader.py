import asyncio, json, httpx
from a2a.client import A2ACardResolver
from a2a.types import AgentCard
from modules.util.remote_agent_connection import RemoteAgentConnections
from langchain_core.tools import tool
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent
from modules.util.ociopen_ai import LLM_Open_Client
from pydantic import BaseModel
from typing import Literal, Annotated
from langgraph.graph import add_messages
from langchain_core.messages import AnyMessage

@tool
def lang_list_remote_agents():
    """List the available remote agents you can use to delegate the task."""
    agent_hub = TeamLeadAgent.get_instance()
    if not agent_hub.remote_agent_connections:
        return []

    remote_agent_info = []
    for card in agent_hub.cards.values():
        remote_agent_info.append(
            {'name': card.name, 'description': card.description, 'skills': card.skills}
        )
    return remote_agent_info

@tool
async def send_message_2_agent(query:str,agent_name:str):
    """ Sends a message request to an agent and receives the agent response """
    agent_hub = TeamLeadAgent.get_instance()
    try:
        response = await agent_hub.remote_agent_connections[agent_name].send_message_agent(query)
        return response
    except Exception as e:
        return f"Error in response: {e}"
    
class ResponseFormat(BaseModel):
    """Respond to the user in this format."""
    status: Literal['complete', 'error', 'requires_input'] = 'requires_input'
    messages: Annotated[list[AnyMessage], add_messages]


class TeamLeadAgent:
    _instance = None
    _initialized = False

    def __new__(cls,remote_agent_addesses:list[str], http_client:httpx.AsyncClient):
        if cls._instance is None:
            cls._instance = super(TeamLeadAgent,cls).__new__(cls)
        return cls._instance
    
    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            raise Exception("Host agent has not been started yet")
        return cls._instance
    
    FORMAT_INSTRUCTION = (
        'Set response status to complete if the query is fully addressed and finished, and will ensure user completion.'
        'Set response status to requires_input if the query is missing core information and the agent was not capable of addressing after different intents.'
        'Set response status to error if the response contains misplaced information, errors, or the model does not respond.'
    )
    
    def build_system_instruction(self):
        self.SYSTEM_INSTRUCTION = (
        "You are a team leader responsible for managing user requests by orchestating and delegating tasks to specialized agents.\n"
        f"Each agent has different expertise scopes and skills: {self.list_remote_agents()}.You can use lang_list_remote_agents tool to refresh the agents available and their capabilities\n"
        "Your primary objectives are:\n"
        "1. Decompose and analyse user request: when you receive a user prompt, analyse its intent and identify all the required information to fulfill the request.\n"
        "2. Agent coordination and delegation: Select and coordinate with suitable agents based on skills and capabilities to complete the task.\n"
        "If user information is incomplete or ambiguous, do NOT ask the user for clarification; instead, proactively consult appropiate agents or make reasonable decisions to fill gaps, always leveraging agent responses when possible.\n"
        "3. Decision-making for incomplete information: If essencial details missing, and cannot be obtained from agents, make informed, user-centered decisions.\n"
        "Cleary mark all cases where you have chosen values, preferences, or solutions on behalf the user.\n"
        "4. Workflow management: manage task sequencing, dependencies, and coordination among agents to ensure seamless execution.\n"
        "5. Final response construction: Compose a ocmplete, cohesive response to the user that addresses the original request using all gathered or inferred informaiton.\n"
        "Guidelines:"
        "Strive to minimize user involvement: never request extra information from the user unless explicitly instructed.\n"
        "Leverage your agents to their fullest potential; encourage collaboration between them when beneficial.\n"
        "For ambiguous or open-ended requests, use default best practices or reasonable assumptions, clearly informing the user of any choices made.\n"
        "Always provide a transparent summary of the process and rationale behind any autonomous decisions.\n"
        "You must operate autonomously and proactively to deliver complete, thoughtful, and user-centered outcomes.\n"
    )

    def __init__(self, remote_agent_addesses:list[str], http_client:httpx.AsyncClient):
        if not self._initialized:
            self.httpx_client = http_client
            self.remote_agent_connections:dict[str,RemoteAgentConnections] = {}
            self.cards:dict[str,AgentCard] = {}
            self.agents:str = ''
            self.oci_client = LLM_Open_Client()
            self.model = self.oci_client.build_llm_client()
            self.memory = MemorySaver()
            TeamLeadAgent._initialized = True
            loop = asyncio.get_running_loop()
            loop.create_task(self.init_remote_agent_addresses(remote_agent_addesses))

    async def init_remote_agent_addresses(self,remote_agent_addresses:list[str]):
        async with asyncio.TaskGroup() as task_group:
            for address in remote_agent_addresses:
                task_group.create_task(self.retrieve_card(address))

    async def retrieve_card(self, address:str):
        card_resolver = A2ACardResolver(self.httpx_client,address)
        card = await card_resolver.get_agent_card()
        self.register_agent_card(card)

    def register_agent_card(self,card:AgentCard):
        remote_connection = RemoteAgentConnections(self.httpx_client, card)
        self.remote_agent_connections[card.name] = remote_connection
        self.cards[card.name] = card
        agent_info = []
        for remote_agent in self.list_remote_agents():
            agent_info.append(json.dumps(remote_agent))
        self.agents = '\n'.join(agent_info)

    def list_remote_agents(self):
        """List the available remote agents you can use to delegate the task."""
        if not self.remote_agent_connections:
            return []

        remote_agent_info = []
        for card in self.cards.values():
            remote_agent_info.append(
                {'name': card.name, 'description': card.description}
            )
        return remote_agent_info

    def create_agent(self):
        self.build_system_instruction()
        self.tools = [lang_list_remote_agents, send_message_2_agent]
        self.team_lead_agent = create_react_agent(
            model=self.model,
            tools=self.tools,
            checkpointer=self.memory,
            prompt=self.SYSTEM_INSTRUCTION,
            response_format=(self.FORMAT_INSTRUCTION,ResponseFormat)
        )
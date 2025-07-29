import asyncio
import base64
import json
import os
import uuid
import httpx
from a2a.client import A2ACardResolver
from a2a.types import (
    AgentCard,
    DataPart,
    Message,
    MessageSendConfiguration,
    MessageSendParams,
    Part,
    Task,
    TaskState,
    TextPart,
)
from modules.util.remote_agent_connection import RemoteAgentConnections, TaskUpdateCallback
from modules.util.oci_client import LLM_Client
from collections.abc import AsyncIterable
from typing import Any
from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.tools import tool
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent

@tool
def lang_list_remote_agents():
    """List the available remote agents you can use to delegate the task."""
    agent_hub = HostAgentHub.get_instance()
    if not agent_hub.remote_agent_connections:
        return []

    remote_agent_info = []
    for card in agent_hub.cards.values():
        remote_agent_info.append(
            {'name': card.name, 'description': card.description}
        )
    return remote_agent_info

@tool
async def send_message_2_agent(query:str,agent_name:str):
    """ Sends a message request to an agent and receives the agent response """
    agent_hub = HostAgentHub.get_instance()
    try:
        response = await agent_hub.remote_agent_connections[agent_name].send_message_agent(query)
        return response
    except Exception as e:
        return f"Error in response: {e}"

class HostAgentHub:
    _instance = None
    _initialized = False

    def __new__(cls,remote_agent_addesses:list[str], http_client:httpx.AsyncClient):
        if cls._instance is None:
            cls._instance = super(HostAgentHub,cls).__new__(cls)
        return cls._instance
    
    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            raise Exception("Host agent has not been started yet")
        return cls._instance
    
    def build_system_instruction(self):
        self.SYSTEM_INSTRUCTION = (
        "You are a supervisor of different agents to plan dates, parties and meetings.\n"
        f"The current agents available are: {self.list_remote_agents()}.\n"
        "ALWAYS ask first all the agents to come up with a plan on how they could address the user query, JUST a plan, not the actual final answer, ask something like 'Tell me what is you plan to address the nex user query...'.\n"
        "Based on the plan offered by each agent, select the top 3 relevant agents (if available) and ask them to complete now the user query.\n"
        "You are in charge of answer the user's query, order the agent responses according to relevance for the user.\n"
        "BEFORE finish you execution, ALWAYS make sure the user query is fully completed and addressed. DO NOT make up any data, if missing, ask the user for it."
    )

    def __init__(self, remote_agent_addesses:list[str], http_client:httpx.AsyncClient):
        if not self._initialized:
            self.httpx_client = http_client
            self.remote_agent_connections:dict[str,RemoteAgentConnections] = {}
            self.cards:dict[str,AgentCard] = {}
            self.agents:str = ''
            self.oci_client = LLM_Client()
            self.model = self.oci_client.build_llm_client()
            self.memory = MemorySaver()
            HostAgentHub._initialized = True
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
        self.hub_agent = create_react_agent(
            model=self.model,
            tools=self.tools,
            checkpointer=self.memory,
            prompt=self.SYSTEM_INSTRUCTION
        )
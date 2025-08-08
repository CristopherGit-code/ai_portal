from dotenv import load_dotenv
load_dotenv()
from collections.abc import AsyncIterable
from typing import Any
from langchain_core.messages import AIMessage, ToolMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent
from remote.util.oci_client import LLM_Client
import logging
import asyncio

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(name=f'MCP_FILE.{__name__}')

# MCP connection section -----------------------------------------

from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.prebuilt import create_react_agent
import json

with open(r"C:\Users\Cristopher Hdz\Desktop\ai_portal\remote\util\config\files.json",'r') as config:
    data = config.read()
    metadata = json.loads(data)

client = MultiServerMCPClient(metadata)

# MCP connection section END -----------------------------------------

oci_client = LLM_Client()
memory = MemorySaver()

class FileAgent:
    """ Agent expert managing user files, open, delete, write, rename files, etc. """

    SYSTEM_INSTRUCTION = (
        "You are an expert in managing user files environment to use different habilities such as open, delete, rename, etc.\n"
        "You have different tools availabe to complete user requests.\n"
        "DO NOT address queries UNRELATED TO FILE MANAGEMENT, DO NOT MAKE UP information and refuse to answer politely if the query is not related to file management.\n"
        "If the query has different requests, just answer the request related to files, or file management, and reply that the other requests are out of your capacity.\n"
        "ALWAYS answer in LESS than 50 words."
    )

    def __init__(self):
        self.model = oci_client.build_llm_client()
        self.tools = asyncio.run(self._load_tools())
        self.file_agent = create_react_agent(
            model=self.model,
            tools=self.tools,
            checkpointer=memory,
            prompt=self.SYSTEM_INSTRUCTION
        )

    async def _load_tools(self):
        return await client.get_tools()

    async def stream(self,query,context_id)-> AsyncIterable[dict[str,Any]]:
        inputs = {'messages': [('user', query)]}
        config = {'configurable': {'thread_id': context_id}}
        final_response = []
        try:
            for chunk in self.file_agent.stream(inputs,config,stream_mode="values"):
                message = chunk['messages'][-1]
                final_response.append(message.content)
                if isinstance(message,AIMessage):
                    yield {
                        'is_task_complete': False,
                        'require_user_input': False,
                        'content': f'Calling agent: {message.content}',
                    }
                elif isinstance(message,ToolMessage):
                    yield {
                        'is_task_complete': False,
                        'require_user_input': False,
                        'content': f'Tool call: {message.content}',
                    }
        except Exception as e:
            final_response.append(e)
            final_response.append("error")
            yield {
                    'is_task_complete': False,
                    'require_user_input': False,
                    'content': 'error',
                }
            
        if final_response[-1] == "error":
            yield {
                'is_task_complete': False,
                'require_user_input': True,
                'content': final_response[-2],
            }
        else:
            yield {
                'is_task_complete': True,
                'require_user_input': False,
                'content': final_response[-1],
            }
    
    SUPPORTED_CONTENT_TYPES = ['text', 'text/plain']
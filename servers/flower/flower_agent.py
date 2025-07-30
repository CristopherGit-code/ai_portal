from collections.abc import AsyncIterable
from typing import Any
from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.tools import tool
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent
from servers.util.oci_client import LLM_Client
from modules.util.lang_fuse import FuseConfig

oci_client = LLM_Client()
memory = MemorySaver()

fuse_tracer = FuseConfig()
id = fuse_tracer.generate_id()
trace_handler = fuse_tracer.get_handler()

@tool
def list_flowers()->list[str]:
    """ Returns the available flowers to make orders to store """
    flowers = ["roses","daisy","tulip","sunflower"]
    return flowers

@tool
def create_bunch(flowers:str)->str:
    """ Given a list of flowers creates a great bunch of flowers to order """
    order = f"Created bunch of flowers using {flowers} as base"
    return order

@tool 
def confirm_order(day:str,flowers:str)->str:
    """ Given the day and the list of flowers confirms an order for a bunch of flowers """
    return f"Order for {day} using {flowers} as base, confirmed and ready to pick up"

class FlowerAgent:
    """ Agent expert in purchasing, ordering and create bunch of flowers for dates """

    SYSTEM_INSTRUCTION = (
        "You are an expert purchase, order, create bunch of flowers for dates.\n"
        "You have different tools availabe to complete user requests.\n"
        "DO NOT address queries UNRELATED TO flowers, bunch of flowers, orders for dates, DO NOT MAKE UP information and refuse to answer politely if the query is not related to flowers.\n"
        "If the query has different requests, just answer the request related to cinema, and reply that the other requests are out of your capacity.\n"
        "ALWAYS answer in LESS than 50 words."
    )

    def __init__(self):
        self.model = oci_client.build_llm_client()
        self.tools = [list_flowers,create_bunch,confirm_order]
        # self.tools = [list_flowers]
        self.flower_agent = create_react_agent(
            model=self.model,
            tools=self.tools,
            checkpointer=memory,
            prompt=self.SYSTEM_INSTRUCTION
        )

    async def stream(self,query,context_id)-> AsyncIterable[dict[str,Any]]:
        inputs = {'messages': [('user', query)]}
        config = {'configurable': {'thread_id': context_id},'callbacks':[trace_handler],'metadata':{'langfuse_session_id':id}}
        final_response = []
        try:
            for chunk in self.flower_agent.stream(inputs,config,stream_mode="values"):
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
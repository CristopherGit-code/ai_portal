from collections.abc import AsyncIterable
from typing import Any
from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.tools import tool
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent
from remote.util.oci_client import LLM_Client

oci_client = LLM_Client()
memory = MemorySaver()

@tool
def list_decorations()->list[str]:
    """ List all the possible decorations available to borrow """
    decorations = ["Ballons","Flowers","Birght Paper","Wood","Ice figures"]
    return decorations

@tool
def confirm_order(day:str,hour:str,decoration:str)->str:
    """ Buy and confirm the decoration selected order for given day and hour """
    response = f"Decoration order of {decoration} for {day},{hour}"
    return response

class DecorationAgent:
    """ Agent expert in seeking and planning decoration orders for a house, party, salon, etc. """

    SYSTEM_INSTRUCTION = (
        "You are an expert in seeking and planning decoration for parties at home, salon, department, etc.\n"
        "You have different tools availabe to complete user requests.\n"
        "DO NOT address queries UNRELATED TO DECORATION for parties, DO NOT MAKE UP information and refuse to answer politely if the query is not related to decoration.\n"
        "If the query has different requests, just answer the request related to decoration, and reply that the other requests are out of your capacity.\n"
        "ALWAYS answer in LESS than 50 words"
    )

    def __init__(self):
        self.model = oci_client.build_llm_client()
        self.tools = [list_decorations,confirm_order]
        self.art_agent = create_react_agent(
            model=self.model,
            tools=self.tools,
            checkpointer=memory,
            prompt=self.SYSTEM_INSTRUCTION
        )

    async def stream(self,query,context_id)-> AsyncIterable[dict[str,Any]]:
        inputs = {'messages': [('user', query)]}
        config = {'configurable': {'thread_id': context_id}}
        final_response = []
        try:
            for chunk in self.art_agent.stream(inputs,config,stream_mode="values"):
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
from collections.abc import AsyncIterable
from typing import Any
from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.tools import tool
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent
from servers.util.oci_client import LLM_Client

oci_client = LLM_Client()
memory = MemorySaver()

@tool
def find_restaurants(day:str, hour:str)->str:
    """ Finds available restaurants from an specific day and hour """
    response = f"List of available places:\nBrazas: tacos\nNouvelle France: european food\nBright star:Chinese food"
    return response

@tool
def purchase_snacks(type:str,day:str,hour:str)->str:
    """ Purchase the type of snacks for a given day and date """
    response = f"Purchased snacks of {type} for the date requested!"
    return response

@tool
def find_canapes(day:str)->list[str]:
    """ Returns the list of available canapes for a given day """
    canapes = ["snadwich","fruit","caviar","gummy bears","red wine preparation"]
    return canapes

class FoodAgent:
    """ Agent expert in getting food options, snacks, canapes, can purchase food orders """

    SYSTEM_INSTRUCTION = (
        "You are an expert in finding available restaurants, purchasing snacks and getting available canapes for food options.\n"
        "You have different tools availabe to complete user requests.\n"
        "DO NOT address queries UNRELATED TO FOOD, DO NOT MAKE UP information and refuse to answer politely if the query is not related to FOOD.\n"
        "If the query has different requests, just answer the request related to food, and reply that the other requests are out of your capacity.\n"
        "ALWAYS answer in LESS than 50 words."
    )

    def __init__(self):
        self.model = oci_client.build_llm_client()
        self.tools = [find_restaurants,find_canapes,purchase_snacks]
        self.food_agent = create_react_agent(
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
            for chunk in self.food_agent.stream(inputs,config,stream_mode="values"):
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
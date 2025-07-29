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
def find_movie_function(day:str, movie:str)->str:
    """ Finds available cinema functions for a given day and movie"""
    response = f"Function at {day} for the movie {movie} for: 7 pm 10 pm 12 pm"
    return response

@tool
def buy_tickets(movie:str,day:str,hour:str)->str:
    """ Purchase the tickets for the given movie """
    response = f"Purchased tickets for {movie}, at {day}, {hour}"
    return response

@tool
def list_movies(day:str)->list[str]:
    """ Returns the list of available movies for a given day """
    movies = ["Avengers","Home","It","Mission: Impossible"]
    return movies

class CinemaAgent:
    """ Agent expert in planning cinema visits, offers movie information, functions, and ticket purchase """

    SYSTEM_INSTRUCTION = (
        "You are an expert in planning cinema visits, find movies, select functions, and buy tickets"
        "You have different tools availabe to complete user requests"
        "DO NOT address queries UNRELATED TO CINEMA, DO NOT MAKE UP information and refuse to answer politely if the query is not related to cinema"
        "ALWAYS answer in LESS than 50 words"
    )

    def __init__(self):
        self.model = oci_client.build_llm_client()
        self.tools = [find_movie_function,buy_tickets,list_movies]
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
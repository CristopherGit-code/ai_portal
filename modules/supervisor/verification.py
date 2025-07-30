from modules.util.oci_client import LLM_Client
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent
from pydantic import BaseModel
from typing import Literal
import sys, logging
from modules.util.lang_fuse import FuseConfig

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(name=f"Agent.{__name__}")

fuse_tracer = FuseConfig()
id = fuse_tracer.generate_id()
trace_handler = fuse_tracer.get_handler()

class ResponseFormat(BaseModel):
    """Respond to the user in this format."""

    status: Literal['input_required', 'completed', 'error'] = 'input_required'
    message: str

class WeatherResponse(BaseModel):
    conditions: str

class VerificationAgent:
    _instance = None
    _initialized = False

    FORMAT_INSTRUCTION = (
        'Set response status to input_required if the user needs to provide more information to complete the request.'
        'Set response status to error if there is an error while processing the request.'
        'Set response status to completed if the request is complete.'
    )

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(VerificationAgent,cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if not self._initialized:
            self.oci_client = LLM_Client()
            self.model = self.oci_client.build_llm_client()
            self.memory = MemorySaver()
            self.create_agent()
            VerificationAgent._initialized = True

    def build_system_instruction(self):
        self.SYSTEM_INSTRUCTION = (
        "You are a verification agent in charge of filtering harsh, rude, innapropiate or not topic related topic queries.\n"
        "The topics related to the agent functions are planning dates, parties, decoration, movies, flowers and general planning for dates, parties and meetings.\n"
        "If the reques from the user is not related to the past topics or includes harsh, rude, innapropiate requests, politely refuse to answer the message.\n"
        "In case the query is able to be solved by the supervisor, continue with the execution to answer the user."
    )
        
    def create_agent(self):
        self.build_system_instruction()
        self.tools = []
        self.verify_agent = create_react_agent(
            model=self.model,
            tools=self.tools,
            checkpointer=self.memory,
            prompt=self.SYSTEM_INSTRUCTION,
            response_format=ResponseFormat
        )

async def main():
    agent = VerificationAgent()
    user_input = input("USER: ")
    response = agent.verify_agent.invoke(
            {"messages": [{"role": "user", "content": user_input}]},
            {'configurable': {'thread_id': "1"},'callbacks':[trace_handler],'metadata':{'langfuse_session_id':id}}
        )
    print("======== model response:")
    print(response['structured_response'])
    return

if __name__ == '__main__':
    import asyncio
    asyncio.run(main())  
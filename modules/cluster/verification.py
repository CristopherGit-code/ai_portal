from modules.util.ociopen_ai import LLM_Open_Client
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent
from pydantic import BaseModel
from typing import Literal
from langgraph.graph import MessagesState
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(name=f"VERIFY.{__name__}")

class VerificationFormat(BaseModel):
    """Respond to the user in this format."""
    status: Literal['complete', 'reject'] = 'reject'

class VerificationAgent:
    _instance = None
    _initialized = False

    FORMAT_INSTRUCTION = (
        'Set response status to complete if the query is related to party, date, meeting planning and also is not rude, harsh or with bad intention'
        'Set response status to reject if the query is not related to party, date, meeting planning, or if the request is rude, or intents to request a harmful action'
    )

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(VerificationAgent,cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if not self._initialized:
            self.oci_client = LLM_Open_Client()
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
            response_format=(self.FORMAT_INSTRUCTION,VerificationFormat)
        )

    def verify_query(self,state:MessagesState):
        """ Verifies the user query to be aligned to the topic """
        response = self.verify_agent.invoke({"messages": [{"role": "user", "content": state["messages"][-1].content}]})
        return {"messages": [{"role": "assistant", "content": response["structured_response"].status}]}
    
    def verification_check(self,state:MessagesState):
        """ decides if the query is able to pass to next node """
        if str(state["messages"][-1].content) == 'reject':
            return "Fail"
        return "Pass"

async def main_loop():
    agent = VerificationAgent()
    user_input = input("USER: ")
    response = agent.verify_agent.invoke(
            {"messages": [{"role": "user", "content": user_input}]},
            {'configurable': {'thread_id': "1"}}
        )
    print("======== model response:")
    print(response)
    return

if __name__ == '__main__':
    import asyncio
    asyncio.run(main_loop())
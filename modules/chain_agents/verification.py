from modules.util.ociopen_ai import LLM_Open_Client
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent
from pydantic import BaseModel
from typing import Literal
from modules.util.lang_fuse import FuseConfig
from langgraph.graph import MessagesState
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(name=f"VERIFY.{__name__}")

fuse_tracer = FuseConfig()
id = fuse_tracer.generate_id()
trace_handler = fuse_tracer.get_handler()

class ResponseFormat(BaseModel):
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
            response_format=(self.FORMAT_INSTRUCTION,ResponseFormat)
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
    """ {'messages': [HumanMessage(content='what is the capital of congo?', additional_kwargs={}, response_metadata={}, id='9debc275-cfad-4a83-ab11-74e85e5dc77b'), AIMessage(content='I’m here to assist with planning dates, parties, decorations, movies, flowers, and general event planning. If you need help organizing an event or any of the related topics, please let me know!', additional_kwargs={'refusal': None}, response_metadata={'token_usage': {'completion_tokens': 41, 'prompt_tokens': 126, 'total_tokens': 167, 'completion_tokens_details': {'accepted_prediction_tokens': 0, 'audio_tokens': 0, 'reasoning_tokens': 0, 'rejected_prediction_tokens': 0}, 'prompt_tokens_details': {'audio_tokens': 0, 'cached_tokens': 0}}, 'model_name': 'openai.gpt-4.1', 'system_fingerprint': 'fp_799e4ca3f1', 'id': 'chatcmpl-BzRSFiN1gpKhiLIWeIVO9ppW12fjv', 'service_tier': 'default', 'finish_reason': 'stop', 'logprobs': None}, id='run--6f14355a-f5d9-4f38-98cf-31310517935b-0', usage_metadata={'input_tokens': 126, 'output_tokens': 41, 'total_tokens': 167, 'input_token_details': {'audio': 0, 'cache_read': 0}, 'output_token_details': {'audio': 0, 'reasoning': 0}})], 'structured_response': ResponseFormat(status='reject', message='Your query is not related to party, date, or meeting planning. Please let me know if you need help organizing an event or planning a celebration!')} """
    return

if __name__ == '__main__':
    import asyncio
    asyncio.run(main_loop())
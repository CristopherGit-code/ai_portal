from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent
from modules.util.ociopen_ai import LLM_Open_Client
import logging
import asyncio
import json
from langgraph.graph import MessagesState
from pydantic import BaseModel
from langchain_core.tools import tool
from typing import List,Any
from modules.util.lang_fuse import FuseConfig

fuse_tracer = FuseConfig()
trace_handler = fuse_tracer.get_handler()

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(name=f"LAYOUT_BUILDER.{__name__}")

class HelperOpenAI:
    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(HelperOpenAI,cls).__new__(cls)
            cls._instance._init()
        return cls._instance
    
    def _init(self):
        if self._initialized:
            return
        self.openai_module = LLM_Open_Client()
        self._initialized = True

    def bind_output(self,schema):
        model = self.openai_module.build_llm_client()
        output_model = model.with_structured_output(schema)
        return output_model

with open(r"C:\Users\Cristopher Hdz\Desktop\ai_portal\modules\UI\json\card.json",'r',encoding='utf-8') as f:
    card_schema = json.load(f)

@tool
async def build_card_schema(context:str)->Any:
    """ Builds a JSON schema for a card text UI component based on the given context. """
    llm = HelperOpenAI().bind_output(card_schema)
    query = f"Based on the current context: {context}, use the schema to generate a text card UI component with a summary of the data given."
    response = await llm.ainvoke(query)
    return response

with open(r"C:\Users\Cristopher Hdz\Desktop\ai_portal\modules\UI\json\chart.json",'r',encoding='utf-8') as f:
    chart_schema = json.load(f)

@tool
async def build_chart_schema(context:str)->Any:
    """ Builds a JSON schema for a chart bar/pie UI component based on the given context. """
    llm = HelperOpenAI().bind_output(chart_schema)
    query = f"Based on the current context: {context}, use the schema to generate a chart UI component with a summary of the data given."
    response = await llm.ainvoke(query)
    return response


class ComponentState(BaseModel):
    components:List[str]

class LayoutAgent:
    """ Agent expert in building UI layout from the final workflow report """

    _instance = None
    _initialized = False

    SYSTEM_INSTRUCTION = (
        """
        You are an agent in charge of a layout build to show the final response to the user.

        For first task:
        - You will receive the ouput response from different agents, your task is to select one UI component for each agent response.
        - You are in charge of select which are the best UI components to show the response to the user.
        - Select a UI component for each agent response or context given and call a tool with that information to generate the component.

        You have different component tools to generate the UI components. Select at least two different for the user to have variety of visual elements.
        Your main task is to build a response that contains the modules based on the report from the previous agent.

        For the final response:
        - Do not change the tool output, just add the json responses in a list format like. 
        - Do not include any extra information of text, nor additional messages, just the list with the tool outputs.
        """
    )

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(LayoutAgent,cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            self.oci_client = LLM_Open_Client()
            self.model = self.oci_client.build_llm_client()
            self.memory = MemorySaver()
            self.tools = [build_card_schema,build_chart_schema]
            self.layout_builder_agent = create_react_agent(
                model=self.model,
                tools=self.tools,
                checkpointer=self.memory,
                prompt=self.SYSTEM_INSTRUCTION,
                # response_format=("Put the tool responses in list format",ComponentState)
            )
            LayoutAgent._initialized = True

    async def call_layout_builder(self, state:MessagesState):

        logger.debug("\nEntered layout builder ===============\n")

        query = f"Current workflow report\n: {state['messages'][-1].content}"
        response = await self.layout_builder_agent.ainvoke({"messages": [{"role": "assistant", "content": query}]})

        ans = response['messages'][-1].content
        logger.debug(str(ans))
        
        return {"messages": [{"role": "assistant", "content": ans}],'status':'execute'}

async def main():
    main_orchestrator = LayoutAgent()

    query = r"""A"""
    # Invoke
    state = await main_orchestrator.layout_builder_agent.ainvoke({"messages": [{"role": "user", "content": query}]},
                {'configurable': {'thread_id': "1"},'callbacks':[trace_handler],'metadata':{'langfuse_session_id':fuse_tracer.generate_id()}})
    print("Final state ================================")
    print(state["messages"][-1].content)

if __name__ == "__main__":
    asyncio.run(main())
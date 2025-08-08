from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent
from modules.util.ociopen_ai import LLM_Open_Client
import logging
import asyncio
from langgraph.graph import MessagesState
from pydantic import BaseModel
from typing import List

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(name=f"LAYOUT_BUILDER.{__name__}")

class Component(BaseModel):
    component: str

class ComponentState(BaseModel):
    components:List[Component]

class LayoutAgent:
    """ Agent expert in building UI layout from the final workflow report """

    _instance = None
    _initialized = False

    SYSTEM_INSTRUCTION = (
        """
        You are an agent in charge of a layout build to show the final response to the user.

        Your main task is to build a json response that contains the modules based on the report from the previous agent.

        You should order the components from the most relevant to the less relevant, and decide the way to show them in screen.
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
            self.tools = []
            self.layout_builder_agent = create_react_agent(
                model=self.model,
                tools=self.tools,
                checkpointer=self.memory,
                prompt=self.SYSTEM_INSTRUCTION,
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

    query = ""
    # Invoke
    state = main_orchestrator.layout_builder_agent.invoke({"messages": [{"role": "user", "content": query}]},
                {'configurable': {'thread_id': "1"}})
    print("Final state ================================")
    print(state["messages"][-1].content)

if __name__ == "__main__":
    asyncio.run(main())
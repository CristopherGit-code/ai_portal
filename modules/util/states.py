from langgraph.graph import MessagesState
from typing import Annotated
from langchain_core.messages import AnyMessage
from langgraph.graph import add_messages

class LayoutState(MessagesState):
    """ change the status according to execution steps for worker agents """
    status: str
    plans: Annotated[list[AnyMessage], add_messages]
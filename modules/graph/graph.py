import logging,httpx
from langgraph.graph import StateGraph, START, MessagesState, END
from modules.supervisor.supervisor import HostAgentHub

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(name=f"Agent.{__name__}")

class SupervisorManager:
    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SupervisorManager,cls).__new__(cls)
        return cls._instance
    
    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            raise Exception("Host agent has not been started yet")
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            self.http_client = httpx.AsyncClient(timeout=10.0)
            self.remote_addresses = [
                "http://localhost:9999/",
                "http://localhost:9998/"
            ]
            self.supervisor_host = HostAgentHub(self.remote_addresses,self.http_client)
            self.supervisor_host.create_agent()
            self.supervisor_agent = self.supervisor_host.hub_agent
            SupervisorManager._initialized = True

    def test(self,MessagesState):
        response = MessagesState['messages'][-1].content
        return {"messages": response}

    def build_graph(self):
        main_graph_builder = StateGraph(MessagesState)
        main_graph_builder.add_node("supervisor",self.supervisor_agent)
        main_graph_builder.add_node("test",self.test)
        main_graph_builder.add_edge(START,"supervisor")
        main_graph_builder.add_edge("supervisor","test")
        main_graph_builder.add_edge("test",END)
        graph = main_graph_builder.compile()
        return graph
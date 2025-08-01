import asyncio, operator
from typing import Annotated, Any, List
from typing_extensions import TypedDict
from pydantic import BaseModel, Field
from langgraph.graph import StateGraph, START, END, MessagesState
from langchain_core.messages import HumanMessage,SystemMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Send
from langgraph.prebuilt import create_react_agent
from modules.util.ociopen_ai import LLM_Open_Client
from modules.chain_agents.workers import (
    CinemaAgentPlanner,
    DecorationAgentPlanner,
    FlowerAgentPlanner
)

class Plan(BaseModel):
    agent_name: str = Field(
        description="Exact name of the agent to request the plan to complete the user request",
    )
    agent_description: str = Field(
        description= "Exact agent description that mathces the name of the agent and information about the agent capabilities"
    )
    request: str = Field(
        description="Query asking the particular agent to come up with a plan to address the user query, necessary context and query if required",
    )

class Plans(BaseModel):
    plan_request: List[Plan] = Field(
        description="Plan requests for each of the agents available",
    )

# Worker state
class WorkerState(TypedDict):
    plan: Plan
    completed_plans: Annotated[list, operator.add]

# Graph state
class State(TypedDict):
    query: str  # User query
    plans: list[Plan]  # List of agent plans
    completed_plans: Annotated[
        list, operator.add
    ]  # All workers write to this key in parallel
    final_selected_agents: str

class OrchestratorAgent:
    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(OrchestratorAgent,cls).__new__(cls)
        return cls._instance
    
    def build_system_instruction(self):
        self.SYSTEM_INSTRUCTION = (
        "You are a team leader responsible for managing user requests by orchestating and delegating tasks to specialized agents.\n"
        f"Each agent has different expertise scopes and skills: {self.remote_agent_connections}.Use only the agents inside the list and dont make up any new one\n"
        "Your primary objectives are:\n"
        "1. Ask EACH agent to come up with a plan to complete the user query.\n"
        "2. Make emphasis to the agents to answer what they have to offer, their capabilities on that topic, similar to a bid offering their services to complete the user query.\n"
        "3. The main aim is to know the capabilities and limitations of each agent.\n"
        "Main key: create a plan request for each of the agents in the list."
    )

    def __init__(self):
        if not self._initialized:
            self.cinema_planner = CinemaAgentPlanner()
            self.flower_planner = FlowerAgentPlanner()
            self.deco_planner = DecorationAgentPlanner()
            self.remote_agent_connections:list[dict[str,str]] = [
                {'name': self.cinema_planner.name, 'description': self.cinema_planner.description},
                {'name': self.deco_planner.name, 'description': self.deco_planner.description},
                {'name': self.flower_planner.name, 'description': self.flower_planner.description},
            ]
            self.agent_list:dict[str,Any] = {
                self.cinema_planner.name: self.cinema_planner, 
                self.deco_planner.name: self.deco_planner,
                self.flower_planner.name: self.flower_planner
            }
            self.oci_client = LLM_Open_Client()
            self.lead_model = self.oci_client.build_llm_client()
            self.worker_model = self.oci_client.build_llm_client()
            self.memory = MemorySaver()
            self.create_main_leader()
            OrchestratorAgent._initialized = True    

    def create_main_leader(self):
        self.build_system_instruction()
        self.tools = []
        self.team_lead_agent = create_react_agent(
            model=self.lead_model,
            tools=self.tools,
            checkpointer=self.memory,
            prompt=self.SYSTEM_INSTRUCTION,
            response_format=Plans
        )
    
    # Nodes
    def lead_call(self, state: State):
        """ team leader call """
        response = self.team_lead_agent.invoke({"messages": [{"role": "user", "content": state['query']['content']}]})

        return {"plans": response['structured_response'].plan_request}
    
    def agent_call(self, state: WorkerState):
        """Worker generates a plan to solve the query"""

        try:
            agent = self.agent_list[state['plan'].agent_name]
            tools = agent.tools
            response = agent.planner.invoke({"messages": [{"role": "user", "content": state['plan'].request}]},
                    {'configurable': {'thread_id': "1"}},)
            
            print("Expert response ------------------------------------->>>")
            print(response["structured_response"])
            return {"completed_plans": [str(response["structured_response"])]}
        except Exception as e:
            print("Expert ERROR ------------------------------------->>>")
            print(e)

        if not tools: 
            tools = []

        plan = self.worker_model.invoke(
            [
                SystemMessage(
                    content=f"You are an agent called {state['plan'].agent_name}, expert in the tasks that match the following description: {state['plan'].agent_description}. Come up with a plan to address the user request, considering you only have this tools {tools} available. Include agent name in response, refuse politely to answer any other queries not related to that. Answer in LESS than 100 words."
                ),
                HumanMessage(
                    content=f"Here is the user request: {state['plan'].request}"
                ),
            ]
        )

        return {"completed_plans": [plan.content]}
    
    def synthesizer(self,state: State):
        """Synthesize full agent plans form the list"""

        # List of completed plans
        completed_plans = state["completed_plans"]

        # Format completed section to str to use as context for final plans
        completed_report_plans = "\n\n---\n\n".join(completed_plans)

        return {"final_selected_agents": completed_report_plans}

    # Conditional edge function to create agent_call workers that each write a section of the report
    def assign_workers(self,state: State):
        """Assign a worker to each section in the plan"""
        
        # Kick off section writing in parallel via Send() API
        return [Send("agent_call", {"plan": p}) for p in state["plans"]]
    
    def build_main_cluster(self):
        workflow_builder = StateGraph(State)
        workflow_builder.add_node("orchestrator", self.lead_call)
        workflow_builder.add_node("agent_call", self.agent_call)
        workflow_builder.add_node("synthesizer", self.synthesizer)
        # Add edges to connect nodes
        workflow_builder.add_edge(START, "orchestrator")
        workflow_builder.add_conditional_edges(
            "orchestrator", self.assign_workers, ["agent_call"]
        )
        workflow_builder.add_edge("agent_call", "synthesizer")
        workflow_builder.add_edge("synthesizer", END)

        # Compile the workflow
        orchestrator_worker = workflow_builder.compile()

        return orchestrator_worker
    
    def call_main_cluster(self,state:MessagesState)-> MessagesState:
        graph = self.build_main_cluster()

        query = state["messages"][0].content
        response = graph.invoke({'query': {'content': query}})
        agent_plans = response['final_selected_agents']
        final_response = f"Original user query:\n{query}.\n Agent plans to fulfill the query:\n{agent_plans}"

        return {"messages": [{"role": "assistant", "content": final_response}]}

async def main():
    main_orchestrator = OrchestratorAgent()

    orchestrator_worker = main_orchestrator.build_main_cluster()
    
    # Invoke
    state = orchestrator_worker.invoke({'query': {'content':'what are the movies during the weekend?'}})
    print("Final state ================================")
    print(state)
    print("Final response =================")
    print(state['final_selected_agents'])

if __name__ == "__main__":
    asyncio.run(main())
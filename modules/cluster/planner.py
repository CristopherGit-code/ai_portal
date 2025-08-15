import asyncio
from langgraph.graph import StateGraph, START, END, MessagesState
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent
from modules.util.ociopen_ai import LLM_Open_Client
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(name=f"PLANNER_AGENT.{__name__}")

class PlannerState(MessagesState):
    """ change the status according to execution steps """
    status: str

class PlannerAgent:
    """ Agent in charge of give the plan order, recevie the responses and decide which agents to use """

    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(PlannerAgent,cls).__new__(cls)
        return cls._instance
    
    SYSTEM_INSTRUCTION = (
        """ 
        You are a supervisor agent responsible for managing a group of agents with varying expertise and unknown number. When presented with a user query:

        Step 1: Request Planning from Agents WHEN IN PLAN PHASE
        - Broadcast the user query to all available agents.
        - Instruct each agent:
            * To independently propose a plan for solving the user query.
            * To strictly base their plan only on tools and resources they genuinely have access to.
            * To focus the plan on their main area of expertise; agents should only suggest actions within their actual capabilities.
        
        Step 2: Evaluate and Compile Agents' Plans. Select Best Agents for the Task. Assign Detailed Tasks and Context. WHEN IN EXECUTE MODE
        - Collect and review all agents' proposed plans.
        - For each plan, determine:
            * The relevance and suitability of the agents expertise to the query.
            * How effectively the plan leverages the agents specific skills and available tools.
        - Choose the most suitable agents (one or several) whose skills, plans, and available tools align best with the user query.
        - For each selected agent, compile and output a structured list including:
            * Agent name.
            * Relevant skills or expertise the agent should employ for this request.
            * The exact tasks the agent should perform, derived from the agents own plan.
        - For assign the tasks and context:
            * add as much contextual background as possible, specifically tailored to the agents expertise and directly related to the user query.
            * Ensure the instructions and context are practical and actionable for the agents, enabling them to execute their assigned tasks effectively.
        - Final response MUST include a list of the agents selected and the information assigned to each agent.
        
        Rules:
        - Do not assume knowledge about the agents' identities, expertise, or the total number of agents; always act based only on the information obtained directly from agents responses.
        - All guidance and assignments must be rooted in the actual capabilities expressed by the agents in their submitted plans.
        - Reduce as much as possible the need of human interaction by taking decisions in behalf of the user. Acknowledge this decisions to the user in the final response.
        """
    )

    def __init__(self):
        if not self._initialized:
            self._oci_client = LLM_Open_Client()
            self._model = self._oci_client.build_llm_client()
            self._memory = MemorySaver()
            self._tools = []
            self._planner_agent = create_react_agent(
                model=self._model,
                tools=self._tools,
                checkpointer=self._memory,
                prompt=self.SYSTEM_INSTRUCTION
            )
            PlannerAgent._initialized = True

    def call_planner_agent(self,state:PlannerState)->PlannerState:
        logger.debug("=========== Entered planner calling")
        if state['status'] == 'plan':
            query = state['messages'][0].content
        else:
            query = f"Current agent plans: {state['messages'][-1].content}, current state: {state['status']}. Generate the instructions to be executed by the agents. Select only the best agents to address the user query: {state['messages'][0].content}.Generate the list of selected agents along with the context and tasks."
        
        response = self._planner_agent.invoke({"messages": [{"role": "assistant", "content": query}]})
        ans = response['messages'][-1].content
        logger.debug(str(ans))
        
        return {"messages": [{"role": "assistant", "content": ans}],'status':'execute'}
    
async def main_graph():
    planner = PlannerAgent()
    main_graph_builder = StateGraph(PlannerState)

    main_graph_builder.add_node("planner_plan",planner.planner_agent)
    main_graph_builder.add_node("agents", planner.test)
    main_graph_builder.add_node("planner_execute",planner.planner_agent)

    main_graph_builder.add_edge(START,"planner_plan")
    main_graph_builder.add_edge("planner_plan","agents")
    main_graph_builder.add_edge("agents","planner_execute")

    graph = main_graph_builder.compile()

    try:
        user_input = input("USER: ")
        final_response = []
        for chunk in graph.stream( {"messages": [{"role": "user", "content": user_input}],'status':'plan'},
            {'configurable': {'thread_id': "1"}},
            stream_mode="values",
            subgraphs=True
        ):
            try:
                logger.debug("============ Chunk response ==========")
                logger.debug(chunk)
                final_response.append(chunk[-1]['messages'][-1].content)
            except Exception as p:
                final_response.append(f"Error in response: {p}")
        print("\nMODEL RESPONSE")
        print(final_response[-1])
    except Exception as e:
        logger.info(f'General error: {e}')

async def main():
    await main_graph()

if __name__ == "__main__":
    asyncio.run(main())
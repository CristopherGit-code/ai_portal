from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent
from modules.util.ociopen_ai import LLM_Open_Client
import logging
import asyncio
from langgraph.graph import MessagesState
from modules.cluster.agents import WorkerManager
from modules.util.lang_fuse import FuseConfig

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(name=f"EXECUTOR_AGENT.{__name__}")

fuse_tracer = FuseConfig()
id = fuse_tracer.generate_id()
trace_handler = fuse_tracer.get_handler()

class ExecutorAgent:
    """ Agent expert in planning cinema visits, offers movie information, functions, and ticket purchase """

    _instance = None
    _initialized = False

    SYSTEM_INSTRUCTION = (
        """
        You are an executor agent responsible for orchestrating the execution of tasks by specialized team agents.
        Your main objectives are to manage task execution using instructions and context provided by previous steps, coordinate agent activity, ensure completion, minimize unnecessary user interaction, and assemble the final result.
        
        Your Responsibilities:

        Orchestrate Execution:
        - Receive a set of tasks, assigned agents, and relevant context prepared by upstream processes.
        - For each task, use the appropriate tool interface to call and instruct the designated agent.
        - Ensure each agent receives the correct scope, context, and action required as provided.
        
        Monitor and Coordinate Agent Activity:
        - Continuously monitor agent responses and progress for each task.
        - If an agent does not respond or completes a task incompletely, retry, re-issue instructions, or make practical user-centered decisions on the users behalf (clearly mark such decisions).
        - Sequence tasks and coordinate the order of execution as needed, especially where dependencies exist.
        - If agents must share outputs, facilitate needed information transfer via available tools (never via direct agent-to-agent interface).
        
        Reduce Human Interaction:
        - Never prompt the user for extra information unless explicitly instructed.
        - Make decisions and act for the user as necessary, always informing them of such autonomous actions.
        
        Context Completion:
        - If information is incomplete or ambiguous, do not ask the user for clarification.
        - Attempt to infer missing details from current context or agent responses.
        - Where inference isnt possible, make sensible, user-centered decisions and mark each one clearly as your own choice.

        Final Result Compilation:
        - Deliver a highly detailed and structured report containing all relevant outputs, agent contributions, workflow steps, and any autonomous choices made, while omitting discussion of agent selection or planning processes.
        - For the final response consider the sections:
            * Agents & Work Results:
                For each agent involved, present a dedicated section.
                Include the agents name, assigned tasks, the explicit context provided, and a detailed description of the work result, outputs, and any issues encountered or resolved.
                Preserve as much detail as possible from each agents output to ensure minimal information loss.
            * Workflow Summary
                Provide a clear, step-by-step account of the overall workflow executed by the agents.
        I       Include the sequence of task execution, handoffs, dependencies managed, outputs integrated, and any coordination steps undertaken.
            * Autonomous Supervisor Choices
                Clearly document all autonomous decisions made by you during execution (e.g., inference of missing context, resolution of agent failures, retries, or user-centered judgment calls).
                For each, state the context, the rationale, and its impact on the outcome.
        - Do not include or reference the process of agent planning or selection; focus only on post-selection execution results and workflow.
        - Retain all essential details and informative elements—avoid summarizing to the point of information loss.
        - Structure and label your report sections for maximum clarity and utility to the user.
        - Respond without a word or length constraint; focus on completeness and accuracy.
        
        Guidelines:
        - Interact with agents strictly through the official tool interfaces.
        - Explicity inform the agents they have to execute the plan, not create a new one, EXECUTE.
        - Ensure agents execute the plan, if they respond with a plan, ask the agents to execute.
        - Prioritize clarity, user-centric outcomes, and efficient task fulfillment.
        - Use the guidelines from final response according to the final result compilation
        """
    )

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ExecutorAgent,cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            self.oci_client = LLM_Open_Client()
            self.model = self.oci_client.build_llm_client()
            self.memory = MemorySaver()
            self.worker_hub = WorkerManager()
            self.tools = self.worker_hub.agent_tools
            self.executor_agent = create_react_agent(
                model=self.model,
                tools=self.tools,
                checkpointer=self.memory,
                prompt=self.SYSTEM_INSTRUCTION,
            )
            ExecutorAgent._initialized = True

    async def call_executor_agent(self, state:MessagesState):

        logger.debug("\nEntered executor ===============\n")

        query = f"Current agent plan selection and tasks\n: {state['messages'][-1].content}"
        response = await self.executor_agent.ainvoke(
            {"messages": [{"role": "assistant", "content": query}]},
            {'configurable': {'thread_id': id},'callbacks':[trace_handler],'metadata':{'langfuse_session_id':id}}
        )

        ans = response['messages'][-1].content
        logger.debug(str(ans))
        
        return {"messages": [{"role": "assistant", "content": ans}],'status':'execute'}


async def main():
    main_orchestrator = ExecutorAgent()

    query = ""
    # Invoke
    state = main_orchestrator.executor_agent.invoke({"messages": [{"role": "user", "content": query}]},
                {'configurable': {'thread_id': "1"}})
    print("Final state ================================")
    print(state["messages"][-1].content)

if __name__ == "__main__":
    asyncio.run(main())
# from root uv run python -m servers.decorations.deco_server
import click, httpx,uvicorn,logging,sys
from a2a.types import (
    AgentCapabilities,
    AgentCard,
    AgentSkill,
)
from a2a.server.tasks import (
    BasePushNotificationSender,
    InMemoryPushNotificationConfigStore,
    InMemoryTaskStore,
)
from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from remote.decorations.deco_agent import DecorationAgent
from remote.decorations.deco_executor import DecorationAgentExecutor


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@click.command()
@click.option("--host","host",default="localhost")
@click.option("--port","port",default=9998)
def main(host,port):
    try:
        capabilities = AgentCapabilities(streaming=True,push_notifications=True)
        
        list_decorations = AgentSkill(
            id="list_decorations",
            name="List available decorations",
            description="Helps the agent to list the available decorations for parties in different spaces",
            tags=["date","day","decoration"],
            examples=["What are the decorations available?"]
        )
        confirm_order = AgentSkill(
            id="confirm_order",
            name="Confirm the decoration order",
            description="Helps the agent to confirm the decoration order depending on decoration and day selected",
            tags=["date","day","decoration","buy"],
            examples=["Could you confirm the ice figures for Sunday?"]
        )
        
        agent_card = AgentCard(
            name="Decoration agent",
            description="Helps user select, decide and purchase decoration for parties",
            url=f"http://{host}:{port}/",
            version="1.0.0",
            default_input_modes=DecorationAgent.SUPPORTED_CONTENT_TYPES,
            default_output_modes=DecorationAgent.SUPPORTED_CONTENT_TYPES,
            capabilities=capabilities,
            skills=[list_decorations,confirm_order]
        )

        httpx_client = httpx.AsyncClient()
        push_config_store = InMemoryPushNotificationConfigStore()
        push_sender = BasePushNotificationSender(httpx_client=httpx_client,config_store=push_config_store)
        request_handler = DefaultRequestHandler(
            agent_executor=DecorationAgentExecutor(),
            task_store=InMemoryTaskStore(),
            push_config_store=push_config_store,
            push_sender= push_sender
        )
        server = A2AStarletteApplication(
            agent_card=agent_card, http_handler=request_handler
        )

        uvicorn.run(server.build(), host=host, port=port)

    except Exception as e:
        logger.error(f'An error occurred during server startup: {e}')
        sys.exit(1)

if __name__ == '__main__':
    main()
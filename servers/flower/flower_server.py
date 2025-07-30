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
from servers.flower.flower_agent import FlowerAgent
from servers.flower.flower_executor import FlowerAgentExecutor


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@click.command()
@click.option("--host","host",default="localhost")
@click.option("--port","port",default=9997)
def main(host,port):
    try:
        capabilities = AgentCapabilities(streaming=True,push_notifications=True)
        
        list_flowers = AgentSkill(
            id="list_flowers",
            name="List available flowers to create bunch of flowers",
            description="Helps the agent to know all the available flowers to create a bunch of flowers",
            tags=["date","day","decoration","flowers","list"],
            examples=["Which are the flower options?"]
        )
        confirm_order = AgentSkill(
            id="confirm_flower_order",
            name="Confirm the flower order",
            description="Helps the agent to confirm the flower order depending on flower and day selected",
            tags=["date","day","flower","buy"],
            examples=["Could you confirm the flowers for Sunday?"]
        )

        create_bunch = AgentSkill(
            id="create_bunch",
            name="Creates a custom bunch with the flowers that are available",
            description="Helps the agent create a new bunch of flowers depending on the selected ones.",
            tags=["date","day","flower","buy"],
            examples=["Could you create a flower decoration with [roses,daisis, tulips]?"]
        )
        
        agent_card = AgentCard(
            name="Flower agent",
            description="Helps user buy, send and receive flower orders for dates",
            url=f"http://{host}:{port}/",
            version="1.0.0",
            default_input_modes=FlowerAgent.SUPPORTED_CONTENT_TYPES,
            default_output_modes=FlowerAgent.SUPPORTED_CONTENT_TYPES,
            capabilities=capabilities,
            skills=[list_flowers,confirm_order,create_bunch]
        )

        httpx_client = httpx.AsyncClient()
        push_config_store = InMemoryPushNotificationConfigStore()
        push_sender = BasePushNotificationSender(httpx_client=httpx_client,config_store=push_config_store)
        request_handler = DefaultRequestHandler(
            agent_executor=FlowerAgentExecutor(),
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
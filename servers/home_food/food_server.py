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
from servers.home_food.food_agent import FoodAgent
from servers.home_food.food_executor import FoodAgentExecutor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@click.command()
@click.option("--host","host",default="localhost")
@click.option("--port","port",default=9997)
def main(host,port):
    try:
        capabilities = AgentCapabilities(streaming=True,push_notifications=True)
        
        find_restaurants = AgentSkill(
            id="find_restaurants",
            name="Find available restaurants",
            description="Finds available restaurants from an specific day and hour",
            tags=["date","day","food","restaurants","list"],
            examples=["Which are the restaurants for Sunday 3 pm?"]
        )
        purchase_snacks = AgentSkill(
            id="purchase_snacks",
            name="Purchase specific snacks",
            description="Purchase the type of snacks for a given day and date",
            tags=["date","day","buy","snacks"],
            examples=["could you buy fancy snacks for Sunday at 3 pm?"]
        )

        find_canapes = AgentSkill(
            id="find_canapes",
            name="Find canapes for a day",
            description="Returns the list of available canapes for a given day",
            tags=["date","day","list","food","canapes"],
            examples=["Could you find some canapes for Saturday?"]
        )
        
        agent_card = AgentCard(
            name="Food agent",
            description="Agent expert in getting food options, snacks, canapes, can purchase food orders",
            url=f"http://{host}:{port}/",
            version="1.0.0",
            default_input_modes=FoodAgent.SUPPORTED_CONTENT_TYPES,
            default_output_modes=FoodAgent.SUPPORTED_CONTENT_TYPES,
            capabilities=capabilities,
            skills=[find_restaurants,purchase_snacks,find_canapes]
        )

        httpx_client = httpx.AsyncClient()
        push_config_store = InMemoryPushNotificationConfigStore()
        push_sender = BasePushNotificationSender(httpx_client=httpx_client,config_store=push_config_store)
        request_handler = DefaultRequestHandler(
            agent_executor=FoodAgentExecutor(),
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
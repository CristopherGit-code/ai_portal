# from root uv run python -m servers.cinema.cinema_server
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
from remote.cinema.cinema_agent import CinemaAgent
from remote.cinema.cinema_executor import CinemaAgentExecutor


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@click.command()
@click.option("--host","host",default="localhost")
@click.option("--port","port",default=9999)
def main(host,port):
    try:
        capabilities = AgentCapabilities(streaming=True,push_notifications=True)
        
        find_movie_function = AgentSkill(
            id="find_movie_function",
            name="Find movie function",
            description="Helps the agent to find the different movie functions for a day and a movie requested",
            tags=["movies","date","day","movie function"],
            examples=["What are the available functions for Superman at Sunday?"]
        )
        buy_tickets = AgentSkill(
            id="buy_tickets",
            name="Buy tickets for a given function",
            description="Helps the agent to buy tickets given a movie, day and hour, confirms the order",
            tags=["movies","date","day","buy","tickets"],
            examples=["Could you buy tickets for Aliens, 8:00 pm, Sunday?"]
        )
        list_movies = AgentSkill(
            id="list_movies",
            name="List available movies",
            description="Helps the agent to know the available movies given a specific day",
            tags=["movies","date","day","movie function"],
            examples=["What movies do you have today?","What is the movies for Sunday?"]
        )
        
        agent_card = AgentCard(
            name="Cinema agent",
            description="Helps user look for movies, plan cinema visit and buy tickets for cinema",
            url=f"http://{host}:{port}/",
            version="1.0.0",
            default_input_modes=CinemaAgent.SUPPORTED_CONTENT_TYPES,
            default_output_modes=CinemaAgent.SUPPORTED_CONTENT_TYPES,
            capabilities=capabilities,
            skills=[find_movie_function,buy_tickets,list_movies]
        )

        httpx_client = httpx.AsyncClient()
        push_config_store = InMemoryPushNotificationConfigStore()
        push_sender = BasePushNotificationSender(httpx_client=httpx_client,config_store=push_config_store)
        request_handler = DefaultRequestHandler(
            agent_executor=CinemaAgentExecutor(),
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
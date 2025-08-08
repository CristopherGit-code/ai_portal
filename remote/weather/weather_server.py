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
from remote.weather.weather_agent import WeatherAgent
from remote.weather.weather_executor import WeatherAgentExecutor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@click.command()
@click.option("--host","host",default="localhost")
@click.option("--port","port",default=9996)
def main(host,port):
    try:
        capabilities = AgentCapabilities(streaming=True,push_notifications=True)
        
        get_alerts = AgentSkill(
            id="get_alerts",
            name="Get weather alerts",
            description="Helps the agent to get weather alerts for a US state.",
            tags=["day","weather","states","alerts"],
            examples=["What are the weather alerts for California?"]
        )
        get_forecast = AgentSkill(
            id="get_forecast",
            name="Weather forecast alerts",
            description="Helps the agent to get weather alerts for a US state",
            tags=["day","weather","states","forecast"],
            examples=["Give me the forecast for Ney York"]
        )
        
        agent_card = AgentCard(
            name="Weather agent",
            description="Helps user look for movies, plan cinema visit and buy tickets for cinema",
            url=f"http://{host}:{port}/",
            version="1.0.0",
            default_input_modes=WeatherAgent.SUPPORTED_CONTENT_TYPES,
            default_output_modes=WeatherAgent.SUPPORTED_CONTENT_TYPES,
            capabilities=capabilities,
            skills=[get_alerts,get_forecast]
        )

        httpx_client = httpx.AsyncClient()
        push_config_store = InMemoryPushNotificationConfigStore()
        push_sender = BasePushNotificationSender(httpx_client=httpx_client,config_store=push_config_store)
        request_handler = DefaultRequestHandler(
            agent_executor=WeatherAgentExecutor(),
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
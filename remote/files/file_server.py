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
from remote.files.file_agent import FileAgent
from remote.files.file_executor import FileAgentExecutor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@click.command()
@click.option("--host","host",default="localhost")
@click.option("--port","port",default=9995)
def main(host,port):
    try:
        capabilities = AgentCapabilities(streaming=True,push_notifications=True)
        
        write_file = AgentSkill(
            id="write_file",
            name="Write a file",
            description="Helps the agent to write a file into the user machine with content and provided path",
            tags=["file","content","path","user machine"],
            examples=["Wirte a file with some jokes in it in the current directory"]
        )
        delete_file = AgentSkill(
            id="delete_file",
            name="Delete a file",
            description="Helps the agent to delete a file given a path.",
            tags=["file","path","user machine"],
            examples=["Could you delete the file example.txt from my current directory?"]
        )
        
        agent_card = AgentCard(
            name="File agent",
            description="Helps user manage the files inside the user machine",
            url=f"http://{host}:{port}/",
            version="1.0.0",
            default_input_modes=FileAgent.SUPPORTED_CONTENT_TYPES,
            default_output_modes=FileAgent.SUPPORTED_CONTENT_TYPES,
            capabilities=capabilities,
            skills=[write_file,delete_file]
        )

        httpx_client = httpx.AsyncClient()
        push_config_store = InMemoryPushNotificationConfigStore()
        push_sender = BasePushNotificationSender(httpx_client=httpx_client,config_store=push_config_store)
        request_handler = DefaultRequestHandler(
            agent_executor=FileAgentExecutor(),
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
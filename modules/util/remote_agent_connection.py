from collections.abc import Callable
from uuid import uuid4

import httpx
from typing import Any

from a2a.client import A2AClient
from a2a.types import (
    AgentCard,
    JSONRPCErrorResponse,
    Message,
    MessageSendParams,
    SendMessageRequest,
    SendStreamingMessageRequest,
    Task,
    TaskArtifactUpdateEvent,
    TaskStatusUpdateEvent,
)

from a2a.client import A2ACardResolver, A2AClient

TaskCallbackArg = Task | TaskStatusUpdateEvent | TaskArtifactUpdateEvent
TaskUpdateCallback = Callable[[TaskCallbackArg, AgentCard], Task]

class RemoteAgentConnections:
    """A class to hold the connections to the remote agents."""

    def __init__(self, client: httpx.AsyncClient, agent_card: AgentCard):
        self.agent_client = A2AClient(client, agent_card)
        self.card = agent_card
        self.pending_tasks = set()
        self.timeout = 30.0

    def get_agent(self) -> AgentCard:
        return self.card

    async def send_message_task(
        self,
        request: MessageSendParams,
        task_callback: TaskUpdateCallback | None,
    ) -> Task | Message | None:
        if self.card.capabilities.streaming:
            task = None
            async for response in self.agent_client.send_message_streaming(
                SendStreamingMessageRequest(id=str(uuid4()), params=request)
            ):
                if not response.root.result:
                    return response.root.error
                # In the case a message is returned, that is the end of the interaction.
                event = response.root.result
                if isinstance(event, Message):
                    return event

                # Otherwise we are in the Task + TaskUpdate cycle.
                if task_callback and event:
                    task = task_callback(event, self.card)
                if hasattr(event, 'final') and event.final:
                    break
            return task
        # Non-streaming
        response = await self.agent_client.send_message(
            SendMessageRequest(id=str(uuid4()), params=request)
        )
        if isinstance(response.root, JSONRPCErrorResponse):
            return response.root.error
        if isinstance(response.root.result, Message):
            return response.root.result

        if task_callback:
            task_callback(response.root.result, self.card)
        return response.root.result
    
    async def send_message_agent(self, user_input:str)-> Any:
        send_message_payload: dict[str, Any] = {
                'message': {
                    'role': 'user',
                    'parts': [
                        {'kind': 'text', 'text': user_input}
                    ],
                    'message_id': uuid4().hex,
                },
            }
        request = SendMessageRequest(
            id=str(uuid4()), params=MessageSendParams(**send_message_payload)
        )
        response = await self.agent_client.send_message(request, http_kwargs={"timeout": self.timeout})
        final_text = response.model_dump(mode='json', exclude_none=True)
        try:
            answer = final_text.get("result").get("artifacts")[0].get('parts')[0].get('text')
            return answer
        except:
            return final_text
    
async def main():
    ports = [9999,8888]
    host = 'localhost'
    servers:dict[str,RemoteAgentConnections] = {}
    async with httpx.AsyncClient() as httpx_client:
        for port in ports:
            url=f"http://{host}:{port}/"
        
            resolver = A2ACardResolver(httpx_client,url)
            final_agent_card_use: AgentCard | None = None

            try:
                _public_card = await resolver.get_agent_card()
                final_agent_card_use = _public_card
            except Exception as e:
                raise RuntimeError('Failed to fetch the public agent card. Cannot continue.') from e
            name = str(final_agent_card_use.name)
            agent = RemoteAgentConnections(httpx_client,final_agent_card_use)
            servers[name] = agent
        response = await servers["Art agent"].send_message_agent("Who was nikola tesla?")
        print(response)
        response = await servers["Science agent"].send_message_agent("Who was nikola tesla?")
        print(response)

if __name__ == '__main__':
    import asyncio
    asyncio.run(main())       
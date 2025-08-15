from typing import Any
from uuid import uuid4
import httpx
from a2a.client import A2ACardResolver, A2AClient
from a2a.types import (
    AgentCard,
    MessageSendParams,
    SendMessageRequest,
)
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(name=f"A2A_CALLS.{__name__}")

async def call_a2a_agent(agent_name:str,message:str)->str:
    PUBLIC_AGENT_CARD_PATH = '/.well-known/agent.json'
    EXTENDED_AGENT_CARD_PATH = '/agent/authenticatedExtendedCard'

    remote_addresses = {
        'cinema_agent':'http://localhost:9999/',
        'decoration_agent':'http://localhost:9998/',
        'food_agent':'http://localhost:9997/',
        'weather_agent':'http://localhost:9996/',
        'file_agent':'http://localhost:9995/'
    }
    logger.debug("\na2a call function ===================")
    logger.debug(remote_addresses.keys())

    try:
        if agent_name not in remote_addresses.keys():
            return f"Wrong agent name, agent names are: {remote_addresses.keys()}"
    except Exception as e:
        logger.debug(e)
    
    base_url = remote_addresses[agent_name]
    timeout = 30.0

    async with httpx.AsyncClient() as httpx_client:
        resolver = A2ACardResolver(
            httpx_client=httpx_client,
            base_url=base_url,
        )
        final_agent_card_to_use: AgentCard | None = None

        try:
            _public_card = (await resolver.get_agent_card())
            final_agent_card_to_use = _public_card
            logger.info('\nUsing PUBLIC agent card for client initialization (default).')

            if _public_card.supports_authenticated_extended_card:
                try:
                    auth_headers_dict = {
                        'Authorization': 'Bearer dummy-token-for-extended-card'
                    }
                    _extended_card = await resolver.get_agent_card(
                        relative_card_path=EXTENDED_AGENT_CARD_PATH,
                        http_kwargs={'headers': auth_headers_dict},
                    )
                    final_agent_card_to_use = (_extended_card)
                    logger.info('\nUsing AUTHENTICATED EXTENDED agent card for client')
                except Exception as e_extended:
                    logger.warning(
                        f'Failed to fetch extended agent card: {e_extended}. '
                        'Will proceed with public card.',
                        exc_info=True,
                    )
            elif (_public_card):
                logger.info('\nPublic card does not indicate support for an extended card. Using public card.')

        except Exception as e:
            logger.error(f'Critical error fetching public agent card: {e}', exc_info=True)
            raise RuntimeError('Failed to fetch the public agent card. Cannot continue.') from e

        client = A2AClient(httpx_client=httpx_client, agent_card=final_agent_card_to_use)
        logger.info('A2AClient initialized.')

        send_message_payload: dict[str, Any] = {
            'message': {
                'role': 'user',
                'parts': [
                    {'kind': 'text', 'text': message}
                ],
                'message_id': uuid4().hex,
            },
        }
        request = SendMessageRequest(
            id=str(uuid4()), params=MessageSendParams(**send_message_payload)
        )

        logger.debug("First response:\n")
        response = await client.send_message(request, http_kwargs={"timeout": timeout})
        ans = response.model_dump(mode='json', exclude_none=True)
        logger.debug(ans)

        return str(ans)
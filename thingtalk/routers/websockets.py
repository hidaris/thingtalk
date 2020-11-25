from functools import partial

from fastapi import APIRouter
from fastapi.websockets import WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState
from websockets import ConnectionClosedOK, ConnectionClosedError
from loguru import logger
from pydantic import ValidationError

from ..toolkits.event_bus import ee
from ..schema import InputMsg, OutMsg


async def perform_action(action):
    """Perform an Action in a coroutine."""
    await action.start()


router = APIRouter()


async def send_data(websocket: WebSocket, data: OutMsg):
    if websocket.application_state == WebSocketState.CONNECTED:
        try:
            await websocket.send_json(data.dict(), mode='binary')
        except (WebSocketDisconnect, ConnectionClosedOK, ConnectionClosedError) as e:
            logger.debug(e)
    else:
        logger.info(f"can't send data {data} because websocket was closed")


subscribe_table = {}


@router.websocket("/channel")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()

    send = partial(send_data, websocket)
    subscribe_topics = []

    try:
        while True:
            receive_message = await websocket.receive_json()
            logger.info(f"websocket {id(websocket)} receive message {receive_message}")

            try:
                message = InputMsg(**receive_message)
            except ValidationError as e:
                logger.error(e.json())
                await websocket.send_json(e.json(), mode="binary")
                continue
            msg_type = message.messageType

            if msg_type == "subscribe":
                for thing_id in message.data.get("thing_ids", []):
                    logger.info(f"subscribe topic things/{thing_id}/state things/{thing_id}/event things/{thing_id}/error")
                    for topic_type in ["state", "event", "error"]:
                        subscribe_topic = f"things/{thing_id}/{topic_type}"
                        ee.on(subscribe_topic, send)
                        subscribe_topics.append(subscribe_topic)
                    subscribe_table.update({id(websocket): subscribe_topics})
            else:
                ee.emit(message.topic, message)

    except (WebSocketDisconnect, ConnectionClosedOK) as e:
        logger.info(f"websocket {id(websocket)} was closed with code {e}")
        topics = subscribe_table.get(id(websocket))
        if topics:
            for topic in topics:
                if send in ee.listeners(topic):
                    ee.remove_listener(topic, send)
            del subscribe_table[id(websocket)]
            logger.info(f"remove listener send of websocket {id(websocket)}")

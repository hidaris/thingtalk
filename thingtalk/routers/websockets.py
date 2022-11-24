from functools import partial

from fastapi import APIRouter
from fastapi.websockets import WebSocket, WebSocketDisconnect, WebSocketState
from websockets import ConnectionClosedOK, ConnectionClosedError
from loguru import logger
from pydantic import ValidationError

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
                thing_ids = message.data.get("thing_ids", [])
                subscribe_table.update({id(websocket): thing_ids})
                for thing_id in thing_ids:
                    logger.info(f"subscribe topic things/{thing_id}/*")
                    thing = websocket.app.state.things.get_thing(thing_id)
                    for topic_type in ["state", "event", "error"]:
                        thing.on(topic_type, send)
            else:
                thing_id = message.topic.replace('things/', '')
                thing = websocket.app.state.things.get_thing(thing_id)
                if thing:
                    thing.emit(message.messageType, message)

    except (WebSocketDisconnect, ConnectionClosedOK) as e:
        logger.info(f"websocket {id(websocket)} was closed with code {e}")
        thing_ids = subscribe_table.get(id(websocket))
        if thing_ids:
            for thing_id in thing_ids:
                thing = websocket.app.state.things.get_thing(thing_id)
                if thing:
                    for topic_type in ["state", "event", "error"]:
                        thing.remove_listener(topic_type, send)
            del subscribe_table[id(websocket)]
            logger.info(f"remove listener send of websocket {id(websocket)}")

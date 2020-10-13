import asyncio

from enum import Enum
from typing import Tuple, Optional, Dict, Any
from functools import partial

from fastapi import APIRouter
from fastapi import Depends
from fastapi.websockets import WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState
from websockets import ConnectionClosedOK, ConnectionClosedError
from loguru import logger
from pydantic import BaseModel, Field, ValidationError


async def perform_action(action):
    """Perform an Action in a coroutine."""
    await action.start()


router = APIRouter()


from ..dependencies import ee


class MsgType(str, Enum):
    subscribe = 'subscribe'
    set_property = 'setProperty'
    request_action = 'requestAction'
    add_event_subscription = 'addEventSubscription'


class Msg(BaseModel):
    type: MsgType = Field(alias="messageType")
    data: Dict[str, Any]


class TopicMsg(BaseModel):
    topic: Optional[str] = Field(None, alias="thing_id")
    type: MsgType = Field(alias="messageType")
    data: Dict[str, Any]


async def send_data(websocket: WebSocket, data):
    logger.info(data)
    if websocket.application_state == WebSocketState.CONNECTED:
        try:
            await websocket.send_json(data, mode='binary')
        except (WebSocketDisconnect, ConnectionClosedOK, ConnectionClosedError) as e:
            logger.debug(e)


subscribe_table = {}


@router.websocket("/channel")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()

    send = partial(send_data, websocket)
    subscribe_topics = []

    try:
        while True:
            receive_message = await websocket.receive_json()
            logger.info(f"ws receive message {receive_message}")

            try:
                message = TopicMsg(**receive_message)
            except ValidationError as e:
                logger.error(e.json())
                await websocket.send_json(e.json(), mode="binary")
                continue
            msg_type = message.type

            if msg_type == "subscribe":
                for thing_id in message.data.get("thing_ids", []):
                    logger.info(f"subscribe topic {thing_id}/state {thing_id}/event {thing_id}/error")
                    for topic_type in ["state", "event", "error"]:
                        subscribe_topic = f"{thing_id}/{topic_type}"
                        ee.on(subscribe_topic, send)
                        subscribe_topics.append(subscribe_topic)
                    subscribe_table.update({id(websocket): subscribe_topics})
            else:
                ee.emit(message.topic, receive_message)

    except (WebSocketDisconnect, ConnectionClosedOK) as e:
        logger.info(f"websocket was closed with code {e}")
        topics = subscribe_table.get(id(websocket))
        if topics:
            for topic in topics:
                logger.info(f"remove topic {topic}'s listener send")
                ee.remove_listener(topic, send)

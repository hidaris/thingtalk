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


# from ..dependencies import on_connect


# from ..models.thing import Thing


async def perform_action(action):
    """Perform an Action in a coroutine."""
    await action.start()


router = APIRouter()


# @router.websocket("/things/{thing_id}")
# async def websocket_endpoint(
#         websocket: WebSocket,
#         thing_id: str,
#         thing_and_subscriber=Depends(on_connect)):
#     thing, subscriber = thing_and_subscriber
#     if not thing:
#         logger.info(f"thing {thing_id} not found, close websocket")
#         await websocket.close(1000)
#         return
#     try:
#         while True:
#             message = await websocket.receive_json()
#             logger.info(f"/things/{thing.id} receive message {message}")
#             msg_type = message.get("messageType", None)
#             if not msg_type or "data" not in message:
#                 await websocket.send_json(
#                     {
#                         "messageType": "error",
#                         "data": {
#                             "status": "400 Bad Request",
#                             "message": "Invalid message",
#                         },
#                     },
#                     mode="binary",
#                 )
#
#             elif msg_type == "setProperty":
#                 for property_name, property_value in message["data"].items():
#                     await thing.set_property(property_name, property_value)
#
#             elif msg_type == "syncProperty":
#                 for property_name, property_value in message["data"].items():
#                     await thing.sync_property(property_name, property_value)
#
#             elif msg_type == "requestAction":
#                 for action_name, action_params in message["data"].items():
#                     input_ = None
#                     if "input" in action_params:
#                         input_ = action_params["input"]
#
#                     action = await thing.perform_action(action_name, input_)
#                     if action:
#                         asyncio.create_task(perform_action(action))
#                     else:
#                         await websocket.send_json(
#                             {
#                                 "messageType": "error",
#                                 "data": {
#                                     "status": "400 Bad Request",
#                                     "message": "Invalid action request",
#                                     "request": message,
#                                 },
#                             },
#                             mode="binary",
#                         )
#
#             elif msg_type == "addEventSubscription":
#                 for event_name in message["data"].keys():
#                     await thing.add_event_subscriber(event_name, subscriber)
#             else:
#                 await websocket.send_json(
#                     {
#                         "messageType": "error",
#                         "data": {
#                             "status": "400 Bad Request",
#                             "message": "Unknown messageType: " + msg_type,
#                             "request": message,
#                         },
#                     },
#                     mode="binary",
#                 )
#
#     except (WebSocketDisconnect, ConnectionClosedOK) as e:
#         logger.info(f"websocket was closed with code {e}")
#         await thing.remove_subscriber(subscriber)


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
    if websocket.application_state != WebSocketState.DISCONNECTED:
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
                logger.debug(message.json())
            except ValidationError as e:
                logger.error(e.json())
                await websocket.send_json(e.json(), mode="binary")
                continue
            msg_type = message.type

            if msg_type == "subscribe":
                for thing_id in message.data.get("thing_ids", []):
                    logger.info(f"subscribe topic {thing_id}/state {thing_id}/event")
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

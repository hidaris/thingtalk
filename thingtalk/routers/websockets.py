import asyncio

from fastapi import APIRouter
from fastapi import Depends
from fastapi.websockets import WebSocket, WebSocketDisconnect
from websockets import ConnectionClosedOK
from loguru import logger

from ..dependencies import on_connect


# from ..models.thing import Thing


async def perform_action(action):
    """Perform an Action in a coroutine."""
    await action.start()


router = APIRouter()


@router.websocket("/things/{thing_id}")
async def websocket_endpoint(
        websocket: WebSocket,
        thing_and_subscriber=Depends(on_connect)):
    thing, subscriber = thing_and_subscriber
    if not thing:
        return
    try:
        while True:
            logger.info("wait for message")
            message = await websocket.receive_json()
            logger.info(f"/things/{thing.id} receive message {message}")
            if "messageType" not in message or "data" not in message:
                await websocket.send_json(
                    {
                        "messageType": "error",
                        "data": {
                            "status": "400 Bad Request",
                            "message": "Invalid message",
                        },
                    },
                    mode="binary",
                )
                logger.info("close websocket")
                await websocket.close(1000)
                return

            msg_type = message["messageType"]
            if msg_type == "setProperty":
                for property_name, property_value in message["data"].items():
                    await thing.set_property(property_name, property_value)

            elif msg_type == "syncProperty":
                for property_name, property_value in message["data"].items():
                    await thing.sync_property(property_name, property_value)

            elif msg_type == "requestAction":
                for action_name, action_params in message["data"].items():
                    input_ = None
                    if "input" in action_params:
                        input_ = action_params["input"]

                    action = await thing.perform_action(action_name, input_)
                    if action:
                        asyncio.create_task(perform_action(action))
                    else:
                        await websocket.send_json(
                            {
                                "messageType": "error",
                                "data": {
                                    "status": "400 Bad Request",
                                    "message": "Invalid action request",
                                    "request": message,
                                },
                            },
                            mode="binary",
                        )

            elif msg_type == "addEventSubscription":
                for event_name in message["data"].keys():
                    await thing.add_event_subscriber(event_name, websocket)
            else:
                await websocket.send_json(
                    {
                        "messageType": "error",
                        "data": {
                            "status": "400 Bad Request",
                            "message": "Unknown messageType: " + msg_type,
                            "request": message,
                        },
                    },
                    mode="binary",
                )

    except (WebSocketDisconnect, ConnectionClosedOK) as e:
        logger.info(f"websocket was closed with code {e}")
        await thing.remove_subscriber(subscriber)

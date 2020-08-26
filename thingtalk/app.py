import asyncio
import typing
import socket

from zeroconf import ServiceInfo, Zeroconf

from websockets import ConnectionClosedOK
from fastapi import FastAPI
from fastapi import status, Depends
from fastapi.requests import Request
from fastapi.websockets import WebSocket, WebSocketDisconnect
from fastapi.exceptions import HTTPException
from fastapi.responses import UJSONResponse
# from tortoise.contrib.fastapi import HTTPNotFoundError, register_tortoise


from loguru import logger

from .dependencies import get_thing, check_property_and_get_thing, on_connect
from .thing import Thing, Server
# from .auth import requires
from .errors import PropertyError
from .utils import get_http_href, get_ws_href, get_ip
from .containers import MultipleThings

logger.info("initial thingtalk instance")

app = FastAPI(
    title="ThingTalk",
    version="0.2.0",
    description="Web of Things framework, high performance, easy to learn, fast to code, ready for production"
)
server = Server()
app.state.things = MultipleThings({server.id: server}, "things")


# @app.on_event("startup")
# async def init_zmq():
#     bus = MessageBus(app)
#     app.state.bus = bus
#     asyncio.create_task(bus.receive())
#     bus.subscriber.subscribe("things/urn:thingtalk:server")
#
#
# @app.on_event("shutdown")
# async def close_zmq():
#     bus = app.state.bus
#     await bus.clean_up()

# @app.on_event("startup")
# async def start_mdns():
#     """Start listening for incoming connections."""
#     name = await app.state.things.get_name()
#     args = [
#         '_webthing._tcp.local.',
#         f"{name}._webthing._tcp.local.",
#     ]
#     kwargs = {
#         'port': '8000',# port,
#         'properties': {
#             'path': '/',
#         },
#         'server': f"{socket.gethostname()}.local.",
#         'addresses': [socket.inet_aton(get_ip())]
#     }
#     app.state.service_info = ServiceInfo(*args, **kwargs)
#     app.state.zeroconf = Zeroconf()
#     app.state.zeroconf.register_service(app.state.service_info)
#
#
# @app.on_event("shutdown")
# async def stop_mdns():
#     """Stop listening."""
#     app.state.zeroconf.unregister_service(app.state.service_info)
#     app.state.zeroconf.close()


async def perform_action(action):
    """Perform an Action in a coroutine."""
    await action.start()


@app.get("/things", tags=["thing"])
async def get_things(request: Request) -> UJSONResponse:
    """
    Handle a request to / when the server manages multiple things.
    Handle a GET request.
    :param request -- the request
    :return UJSONResponse
    """
    things = request.app.state.things

    async def get_description(thing):
        description = await thing.as_thing_description()
        description["href"] = await thing.get_href()
        description["links"].append({
            "rel": "alternate",
            "href": f"{get_ws_href(request)}{await thing.get_href()}",
        })
        description["base"] = f"{get_http_href(request)}{await thing.get_href()}"

        description["securityDefinitions"] = {
            "nosec_sc": {"scheme": "nosec", },
        }
        description["security"] = "nosec_sc"
        return description

    descriptions = [await get_description(thing) for _, thing in await things.get_things()]

    return UJSONResponse(descriptions)


@app.get("/things/{thing_id}", tags=["thing"])
async def get_thing_by_id(request: Request, thing: Thing = Depends(get_thing)) -> UJSONResponse:
    """
    Handle a GET request, including websocket requests.
    :param request: the request
    :param thing -- the thing this request is for
    :return UJSONResponse
    """
    description = await thing.as_thing_description()
    description["links"].append(
        {
            "rel": "alternate",
            "href": f"{get_ws_href(request)}{await thing.get_href()}",
        }
    )
    description["base"] = f"{get_http_href(request)}{await thing.get_href()}"
    description["securityDefinitions"] = {
        "nosec_sc": {"scheme": "nosec", },
    }
    description["security"] = "nosec_sc"

    return UJSONResponse(description)


@app.get("/things/{thing_id}/properties", tags=["property"])
async def get_properties(thing: Thing = Depends(get_thing)) -> UJSONResponse:
    """
    Handle a request to /properties.
    :param thing -- the thing this request is for"
    :return: UJSONResponse
    """
    return UJSONResponse(await thing.get_properties())


@app.get("/things/{thing_id}/properties/{property_name}", tags=["property"])
async def get_property(
        property_name: str,
        thing: Thing = Depends(check_property_and_get_thing)
) -> UJSONResponse:
    """
    Handle a request to /properties/<property>.
    :param: thing-- the thing this request is for"
    :param: property_name -- name of the thing property this request is for
    :return: UJSONResponse
    """
    return UJSONResponse(
        {property_name: await thing.get_property(property_name), }
    )


@app.put("/things/{thing_id}/properties/{property_name}", tags=["property"])
async def put_property(
        property_name: str,
        data: typing.Dict[str, typing.Any],
        thing: Thing = Depends(get_thing),
) -> UJSONResponse:
    """
    Handle a PUT request to /properties/<property>.
    :param property_name -- the name of the property from the URL path
    :param data -- data of this request put
    :param thing -- the thing this request is for
    :return: UJSONResponse
    """
    try:
        await thing.set_property(property_name, data[property_name])
    except PropertyError:
        raise HTTPException(status_code=400)

    return UJSONResponse(
        {property_name: await thing.get_property(property_name), }
    )


@app.get("/things/{thing_id}/actions", tags=["action"])
async def get_actions(thing: Thing = Depends(get_thing)) -> UJSONResponse:
    """
    Handle a request to /actions.
    :param thing-- the thing this request is for
    :return UJSONResponse
    """
    return UJSONResponse(await thing.get_action_descriptions())


@app.post("/things/{thing_id}/actions", tags=["action"])
async def revoke_actions(
        message: typing.Dict[str, typing.Any],
        thing: Thing = Depends(get_thing)
) -> UJSONResponse:
    """
    Handle a POST request.
    :param thing -- the thing this request is for
    :param message -- the request body
    :return UJSONResponse
    """
    response = {}
    for action_name, action_params in message.items():
        input_ = None
        if "input" in action_params:
            input_ = action_params["input"]
        print(f"input_ {input_}")
        action = await thing.perform_action(action_name, input_)
        if action:
            response.update(await action.as_action_description())

            # Start the action
            asyncio.create_task(perform_action(action))

    return UJSONResponse(response, status_code=201)


@app.get("/things/{thing_id}/actions/{action_name}", tags=["action"])
async def get_action(action_name: str, thing: Thing = Depends(get_thing)) -> UJSONResponse:
    """
    Handle a request to /actions/<action_name>.
    :param thing -- the thing this request is for
    :param action_name -- name of the action from the URL path
    :return UJSONResponse
    """
    return UJSONResponse(
        await thing.get_action_descriptions(action_name=action_name)
    )


@app.post("/things/{thing_id}/actions/{action_name}", tags=["action"])
async def invoke_action(
        action_name: str,
        message: typing.Dict[str, typing.Any],
        thing: Thing = Depends(get_thing)
) -> UJSONResponse:
    """
    Handle a POST request.
    :param thing -- the thing this request is for
    :param action_name -- name of the action from the URL path
    :param message -- the request body
    :return UJSONResponse
    """
    response = {}
    for name, action_params in message.items():
        if name != action_name:
            continue

        input_ = None
        if "input" in action_params:
            input_ = action_params["input"]

        action = await thing.perform_action(name, input_)
        if action:
            response.update(await action.as_action_description())

            # Start the action
            asyncio.create_task(perform_action(action))

    return UJSONResponse(response, status_code=201)


@app.get("/things/{thing_id}/actions/{action_name}/{action_id}", tags=["action"])
async def get_action_by_id(action_name: str, action_id: str, thing: Thing = Depends(get_thing)):
    """
    Handle a request to /actions/<action_name>/<action_id>.
    :param thing -- the thing this request is for
    :param action_name -- name of the action from the URL path
    :param action_id -- the action ID from the URL path
    :return UJSONResponse
    """
    action = await thing.get_action(action_name, action_id)
    if action is None:
        raise HTTPException(status_code=404)

    return UJSONResponse(await action.as_action_description())


@app.put("/things/{thing_id}/actions/{action_name}/{action_id}", tags=["action"])
async def update_action_by_id(action_name: str, action_id: str, thing: Thing = Depends(get_thing)):
    """
    Handle a PUT request.
    TODO: this is not yet defined in the spec
    :param thing -- the thing this request is for
    :param action_name -- name of the action from the URL path
    :param action_id -- the action ID from the URL path
    :return UJSONResponse
    """
    return UJSONResponse({"msg": "success"}, status_code=200)


@app.delete("/things/{thing_id}/actions/{action_name}/{action_id}", tags=["action"])
async def cancel_action_by_id(action_name: str,
                              action_id: str,
                              thing: Thing = Depends(get_thing)) -> UJSONResponse:
    """
    Handle a DELETE request.
    :param thing -- the thing this request is for
    :param action_name -- name of the action from the URL path
    :param action_id -- the action ID from the URL path
    :return UJSONResponse
    """
    if await thing.remove_action(action_name, action_id):
        return UJSONResponse({"msg": "success"}, status_code=204)
    else:
        raise HTTPException(status_code=404)


@app.get("/things/{thing_id}/events", tags=["event"])
async def get_events(thing: Thing = Depends(get_thing)) -> UJSONResponse:
    """
    Handle a request to /events.
    :param thing -- the thing this request is for
    :return UJSONResponse
    """
    return UJSONResponse(await thing.get_event_descriptions())


@app.get("/things/{thing_id}/events/{event_name}", tags=["event"])
async def get_event(event_name: str, thing: Thing = Depends(get_thing)) -> UJSONResponse:
    """
    Handle a request to /events/<event_name>.
    :param thing -- the thing this request is for
    :param event_name -- name of the event from the URL path
    :return UJSONResponse
    """
    return UJSONResponse(await thing.get_event_descriptions(event_name=event_name))


@app.websocket("/things/{thing_id}")
async def websocket_endpoint(websocket: WebSocket, thing: Thing = Depends(on_connect)):
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

    except WebSocketDisconnect as e:
        logger.info(f"websocket was closed with code {e}")
        if thing:
            await thing.remove_subscriber(websocket)

# register_tortoise(
#     app,
#     db_url="sqlite://:memory:",
#     modules={'models': ['thingtalk.model']},
#     generate_schemas=True,
#     add_exception_handlers=True,
# )

# class WsThingHandler(WebSocketEndpoint):
#     """Handle a request to /."""
#
#     encoding = "json"
#
#     async def dispatch(self) -> None:
#         websocket = WebSocket(self.scope, receive=self.receive, send=self.send)
#         try:
#             await self.on_connect(websocket)
#         except WebSocketDisconnect:
#             return
#
#         close_code = status.WS_1000_NORMAL_CLOSURE
#
#         try:
#             while True:
#                 message = await websocket.receive()
#                 if message["type"] == "websocket.receive":
#                     data = await self.decode(websocket, message)
#                     await self.on_receive(websocket, data)
#                 elif message["type"] == "websocket.disconnect":
#                     close_code = int(message.get("code", status.WS_1000_NORMAL_CLOSURE))
#                     break
#         except Exception as exc:
#             close_code = status.WS_1011_INTERNAL_ERROR
#             raise exc from None
#         finally:
#             await self.on_disconnect(websocket, close_code)
#

#             try:
#                 await websocket.send_json(description, mode="binary")
#             except (WebSocketDisconnect, ConnectionClosedOK):
#                 pass
#
#

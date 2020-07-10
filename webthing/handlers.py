import asyncio

from websockets import ConnectionClosedOK
from starlette import status
from starlette.types import Scope, Receive, Send
from starlette.requests import Request
from starlette.websockets import WebSocket, WebSocketDisconnect
from starlette.responses import UJSONResponse
from starlette.exceptions import HTTPException
from starlette.endpoints import HTTPEndpoint, WebSocketEndpoint

from .middlewares import requires
from .errors import PropertyError


async def perform_action(action):
    """Perform an Action in a coroutine."""
    await action.start()


class BaseHandler(HTTPEndpoint):
    """Base handler that is initialized with a thing."""

    def __init__(self, scope: Scope, receive: Receive, send: Send) -> None:
        super().__init__(scope, receive, send)
        request = Request(self.scope, receive=self.receive)
        self.things = request.app.state.things

    async def get_thing(self, thing_id):
        """
        Get the thing this request is for.
        things -- list of Things managed by this server
        thing_id -- ID of the thing to get, in string form
        Returns the thing, or None if not found.
        """
        return await self.things.get_thing(thing_id)


class ThingsHandler(BaseHandler):
    """Handle a request to / when the server manages multiple things."""

    @requires('authenticated')
    async def get(self, request):
        """
        Handle a GET request.
        property_name -- the name of the property from the URL path
        """
        ws_href = f"{'wss' if request.url.scheme == 'https' else 'ws'}://{request.headers.get('Host', '')}"

        descriptions = []
        for idx, thing in await self.things.get_things():
            description = await thing.as_thing_description()
            description["href"] = await thing.get_href()
            description["links"].append({
                "rel": "alternate",
                "href": f"{ws_href}{await thing.get_href()}",
            })
            description[
                "base"
            ] = f"{request.url.scheme}://{request.headers.get('Host', '')}{await thing.get_href()}"
            if request.app.state.require_auth:
                description["securityDefinitions"] = {
                    "bearer_sc": {"scheme": "bearer", },
                }
                description["security"] = "bearer_sc"
            else:
                description["securityDefinitions"] = {
                    "nosec_sc": {"scheme": "nosec", },
                }
                description["security"] = "nosec_sc"
            descriptions.append(description)

        return UJSONResponse(descriptions)


class ThingHandler(BaseHandler):
    """Handle a request to /."""

    @requires('authenticated')
    async def get(self, request):
        """
        Handle a GET request, including websocket requests.
        thing_id -- ID of the thing this request is for
        """
        thing_id = request.path_params.get("thing_id", "0")
        thing = await self.get_thing(thing_id)
        if thing is None:
            raise HTTPException(status_code=404)

        ws_href = f"{'wss' if request.url.scheme == 'https' else 'ws'}://{request.headers.get('Host', '')}"

        description = await thing.as_thing_description()
        description["links"].append(
            {"rel": "alternate", "href": f"{ws_href}{await thing.get_href()}", }
        )
        description["base"] = f"{request.url.scheme}://{request.headers.get('Host', '')}{await thing.get_href()}"
        if request.app.state.require_auth:
            description["securityDefinitions"] = {
                "bearer_sc": {"scheme": "bearer", },
            }
            description["security"] = "bearer_sc"
        else:
            description["securityDefinitions"] = {
                "nosec_sc": {"scheme": "nosec", },
            }
            description["security"] = "nosec_sc"

        return UJSONResponse(description)


class WsThingHandler(WebSocketEndpoint):
    """Handle a request to /."""

    encoding = "json"

    async def get_thing(self, thing_id):
        """
        Get the thing this request is for.
        things -- list of Things managed by this server
        thing_id -- ID of the thing to get, in string form
        Returns the thing, or None if not found.
        """
        websocket = WebSocket(self.scope, receive=self.receive, send=self.send)
        things = websocket.app.state.things
        return await things.get_thing(thing_id)

    async def dispatch(self) -> None:
        websocket = WebSocket(self.scope, receive=self.receive, send=self.send)
        try:
            await self.on_connect(websocket)
        except WebSocketDisconnect:
            return

        close_code = status.WS_1000_NORMAL_CLOSURE

        try:
            while True:
                message = await websocket.receive()
                if message["type"] == "websocket.receive":
                    data = await self.decode(websocket, message)
                    await self.on_receive(websocket, data)
                elif message["type"] == "websocket.disconnect":
                    close_code = int(message.get("code", status.WS_1000_NORMAL_CLOSURE))
                    break
        except Exception as exc:
            close_code = status.WS_1011_INTERNAL_ERROR
            raise exc from None
        finally:
            await self.on_disconnect(websocket, close_code)

    @requires('authenticated')
    async def on_connect(self, websocket):
        """
        Handle a GET request, including websocket requests.
        thing_id -- ID of the thing this request is for
        """
        await websocket.accept()

        thing_id = websocket.path_params.get("thing_id", "0")
        self.thing = await self.get_thing(thing_id)

        if self.thing is None:
            try:
                await websocket.send_json(
                    {
                        "messageType": "error",
                        "data": {
                            "status": "404 Not Found",
                            "message": "Invalid thing_id",
                        },
                    },
                    mode="binary",
                )
            except (WebSocketDisconnect, ConnectionClosedOK):
                pass

        else:
            await self.thing.add_subscriber(websocket)
            ws_href = f"{websocket.url.scheme}://{websocket.headers.get('Host', '')}"

            description = await self.thing.as_thing_description()
            description["links"].append(
                {"rel": "alternate", "href": f"{ws_href}{await self.thing.get_href()}", }
            )
            description[
                "base"] = f"{websocket.url.scheme}://{websocket.headers.get('Host', '')}{await self.thing.get_href()}"
            if websocket.app.state.require_auth:
                description["securityDefinitions"] = {
                    "bearer_sc": {"scheme": "bearer", },
                }
                description["security"] = "bearer_sc"
            else:
                description["securityDefinitions"] = {
                    "nosec_sc": {"scheme": "nosec", },
                }
                description["security"] = "nosec_sc"

            try:
                await websocket.send_json(description, mode="binary")
            except (WebSocketDisconnect, ConnectionClosedOK):
                pass

    async def on_receive(self, websocket, message):
        """
        Handle an incoming message.
        message -- message to handle
        """
        if "messageType" not in message or "data" not in message:
            try:
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
            except (WebSocketDisconnect, ConnectionClosedOK):
                pass

        if self.thing is None:
            try:
                await websocket.send_json(
                    {
                        "messageType": "error",
                        "data": {
                            "status": "404 Not Found",
                            "message": "Invalid thing_id",
                        },
                    },
                    mode="binary",
                )
            except (WebSocketDisconnect, ConnectionClosedOK):
                pass
            return

        msg_type = message["messageType"]
        if msg_type == "setProperty":
            for property_name, property_value in message["data"].items():
                try:
                    await self.thing.set_property(property_name, property_value)
                except PropertyError as e:
                    try:
                        await websocket.send_json(
                            {
                                "messageType": "error",
                                "data": {"status": "400 Bad Request", "message": str(e), },
                            },
                            mode="binary",
                        )
                    except (WebSocketDisconnect, ConnectionClosedOK):
                        pass

        elif msg_type == "syncProperty":
            for property_name, property_value in message["data"].items():
                try:
                    await self.thing.sync_property(property_name, property_value)
                except PropertyError as e:
                    try:
                        await websocket.send_json(
                            {
                                "messageType": "error",
                                "data": {"status": "400 Bad Request", "message": str(e), },
                            },
                            mode="binary",
                        )
                    except (WebSocketDisconnect, ConnectionClosedOK):
                        pass

        elif msg_type == "requestAction":
            for action_name, action_params in message["data"].items():
                input_ = None
                if "input" in action_params:
                    input_ = action_params["input"]

                action = await self.thing.perform_action(action_name, input_)
                if action:
                    asyncio.create_task(perform_action(action))
                else:
                    try:
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
                    except (WebSocketDisconnect, ConnectionClosedOK):
                        pass

        elif msg_type == "addEventSubscription":
            for event_name in message["data"].keys():
                await self.thing.add_event_subscriber(event_name, websocket)
        else:
            try:
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
            except (WebSocketDisconnect, ConnectionClosedOK):
                pass

    async def on_disconnect(self, websocket, close_code):
        """Handle a close event on the socket."""

        if hasattr(self, "thing") and self.thing:
            await self.thing.remove_subscriber(websocket)


class PropertiesHandler(BaseHandler):
    """Handle a request to /properties."""

    @requires('authenticated')
    async def get(self, request):
        """
        Handle a GET request.
        thing_id -- ID of the thing this request is for
        """
        thing_id = request.path_params.get("thing_id", "0")
        thing = await self.get_thing(thing_id)
        if thing is None:
            raise HTTPException(status_code=404)

        return UJSONResponse(await thing.get_properties())


class PropertyHandler(BaseHandler):
    """Handle a request to /properties/<property>."""

    @requires('authenticated')
    async def get(self, request):
        """
        Handle a GET request.
        thing_id -- ID of the thing this request is for
        property_name -- the name of the property from the URL path
        """
        thing_id = request.path_params.get("thing_id", "0")
        property_name = request.path_params.get("property_name", None)

        thing = await self.get_thing(thing_id)
        if thing is None:
            raise HTTPException(status_code=404)

        if await thing.has_property(property_name):
            return UJSONResponse(
                {property_name: await thing.get_property(property_name), }
            )
        else:
            raise HTTPException(status_code=404)

    @requires('authenticated')
    async def put(self, request):
        """
        Handle a PUT request.
        thing_id -- ID of the thing this request is for
        property_name -- the name of the property from the URL path
        """
        thing_id = request.path_params.get("thing_id", "0")
        property_name = request.path_params.get("property_name", None)

        thing = await self.get_thing(thing_id)
        if thing is None:
            raise HTTPException(status_code=404)

        try:
            args = await request.json()
        except ValueError:
            raise HTTPException(status_code=400)

        if property_name not in args:
            raise HTTPException(status_code=400)

        if await thing.has_property(property_name):
            try:
                await thing.set_property(property_name, args[property_name])
            except PropertyError:
                raise HTTPException(status_code=400)

            return UJSONResponse(
                {property_name: await thing.get_property(property_name), }
            )
        else:
            raise HTTPException(status_code=404)


class ActionsHandler(BaseHandler):
    """Handle a request to /actions."""

    @requires('authenticated')
    async def get(self, request):
        """
        Handle a GET request.
        thing_id -- ID of the thing this request is for
        """
        thing_id = request.path_params.get("thing_id", "0")

        thing = await self.get_thing(thing_id)
        if thing is None:
            raise HTTPException(status_code=404)

        return UJSONResponse(await thing.get_action_descriptions())

    @requires('authenticated')
    async def post(self, request):
        """
        Handle a POST request.
        thing_id -- ID of the thing this request is for
        """
        thing_id = request.path_params.get("thing_id", "0")

        thing = await self.get_thing(thing_id)
        if thing is None:
            raise HTTPException(status_code=404)

        try:
            message = await request.json()
        except ValueError:
            raise HTTPException(status_code=404)

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


class ActionHandler(BaseHandler):
    """Handle a request to /actions/<action_name>."""

    @requires('authenticated')
    async def get(self, request):
        """
        Handle a GET request.
        thing_id -- ID of the thing this request is for
        action_name -- name of the action from the URL path
        """
        thing_id = request.path_params.get("thing_id", "0")
        action_name = request.path_params.get("action_name", None)

        thing = await self.get_thing(thing_id)
        if thing is None:
            raise HTTPException(status_code=404)

        return UJSONResponse(
            await thing.get_action_descriptions(action_name=action_name)
        )

    @requires('authenticated')
    async def post(self, request):
        """
        Handle a POST request.
        thing_id -- ID of the thing this request is for
        action_name -- name of the action from the URL path
        """
        thing_id = request.path_params.get("thing_id", "0")
        action_name = request.path_params.get("action_name", None)

        thing = await self.get_thing(thing_id)
        if thing is None:
            raise HTTPException(status_code=404)

        try:
            message = await request.json()
        except ValueError:
            raise HTTPException(status_code=404)

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


class ActionIDHandler(BaseHandler):
    """Handle a request to /actions/<action_name>/<action_id>."""

    @requires('authenticated')
    async def get(self, request):
        """
        Handle a GET request.
        thing_id -- ID of the thing this request is for
        action_name -- name of the action from the URL path
        action_id -- the action ID from the URL path
        """
        thing_id = request.path_params.get("thing_id", "0")
        action_name = request.path_params.get("action_name", None)
        action_id = request.path_params.get("action_id", None)

        thing = await self.get_thing(thing_id)
        if thing is None:
            raise HTTPException(status_code=404)

        action = await thing.get_action(action_name, action_id)
        if action is None:
            raise HTTPException(status_code=404)

        return UJSONResponse(await action.as_action_description())

    @requires('authenticated')
    async def put(self, request):
        """
        Handle a PUT request.
        TODO: this is not yet defined in the spec
        thing_id -- ID of the thing this request is for
        action_name -- name of the action from the URL path
        action_id -- the action ID from the URL path
        """
        thing_id = request.path_params.get("thing_id", "0")
        action_name = request.path_params.get("action_name", None)
        action_id = request.path_params.get("action_id", None)

        thing = await self.get_thing(thing_id)
        if thing is None:
            raise HTTPException(status_code=404)

        return UJSONResponse({"msg": "success"}, status_code=200)

    @requires('authenticated')
    async def delete(self, request):
        """
        Handle a DELETE request.
        thing_id -- ID of the thing this request is for
        action_name -- name of the action from the URL path
        action_id -- the action ID from the URL path
        """
        thing_id = request.path_params.get("thing_id", "0")
        action_name = request.path_params.get("action_name", None)
        action_id = request.path_params.get("action_id", None)

        thing = await self.get_thing(thing_id)
        if thing is None:
            raise HTTPException(status_code=404)

        if await thing.remove_action(action_name, action_id):
            return UJSONResponse({"msg": "success"}, status_code=204)
        else:
            raise HTTPException(status_code=404)


class EventsHandler(BaseHandler):
    """Handle a request to /events."""

    @requires('authenticated')
    async def get(self, request):
        """
        Handle a GET request.
        thing_id -- ID of the thing this request is for
        """
        thing_id = request.path_params.get("thing_id", "0")

        thing = await self.get_thing(thing_id)
        if thing is None:
            raise HTTPException(status_code=404)

        return UJSONResponse(await thing.get_event_descriptions())


class EventHandler(BaseHandler):
    """Handle a request to /events/<event_name>."""

    @requires('authenticated')
    async def get(self, request):
        """
        Handle a GET request.
        thing_id -- ID of the thing this request is for
        event_name -- name of the event from the URL path
        """
        thing_id = request.path_params.get("thing_id", "0")
        event_name = request.path_params.get("event_name", None)

        thing = await self.get_thing(thing_id)
        if thing is None:
            raise HTTPException(status_code=404)

        return UJSONResponse(await thing.get_event_descriptions(event_name=event_name))

import asyncio
import ujson as json

from starlette.requests import Request
from starlette.websockets import WebSocket, WebSocketDisconnect
from starlette.responses import UJSONResponse
from starlette.exceptions import HTTPException
from starlette.endpoints import HTTPEndpoint, WebSocketEndpoint

from errors import PropertyError


async def perform_action(action):
    """Perform an Action in a coroutine."""
    await action.start()


class BaseHandler(HTTPEndpoint):
    """Base handler that is initialized with a thing."""

    async def get_thing(self, thing_id):
        """
        Get the thing this request is for.
        things -- list of Things managed by this server
        thing_id -- ID of the thing to get, in string form
        Returns the thing, or None if not found.
        """
        request = Request(self.scope, receive=self.receive)
        things = request.app.state.things
        return await things.get_thing(thing_id)


class ThingsHandler(BaseHandler):
    """Handle a request to / when the server manages multiple things."""

    async def get(self, request):
        """
        Handle a GET request.
        property_name -- the name of the property from the URL path
        """
        ws_href = "{}://{}".format(
            "wss" if self.request.protocol == "https" else "ws",
            self.request.headers.get("Host", ""),
        )

        descriptions = []
        async for thing in self.things.get_things():
            description = thing.as_thing_description()
            description["href"] = thing.get_href()
            description["links"].append(
                {"rel": "alternate", "href": f"{ws_href}{thing.get_href()}",}
            )
            description[
                "base"
            ] = f"{self.request.protocol}://{self.request.headers.get('Host', '')}{await thing.get_href()}"
            description["securityDefinitions"] = {
                "nosec_sc": {"scheme": "nosec",},
            }
            description["security"] = "nosec_sc"
            descriptions.append(description)

        return UJSONResponse(descriptions)


class ThingHandler(WebSocketEndpoint):
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
        print(things)
        return await things.get_thing(thing_id)

    async def on_connect(self, websocket):
        """
        Handle a GET request, including websocket requests.
        thing_id -- ID of the thing this request is for
        """
        await websocket.accept()
        thing_id = websocket.path_params.get("thing_id", "0")
        self.thing = await self.get_thing(thing_id)
        if self.thing is None:
            raise HTTPException(status_code=404)

        # self.set_header('Content-Type', 'application/json')
        ws_href = "{}://{}".format(
            websocket.url.scheme, websocket.headers.get("Host", "")
        )

        description = await self.thing.as_thing_description()
        description["links"].append(
            {"rel": "alternate", "href": f"{ws_href}{await self.thing.get_href()}",}
        )
        description["base"] = "{}://{}{}".format(
            websocket.url.scheme,
            websocket.headers.get("Host", ""),
            await self.thing.get_href(),
        )
        description["securityDefinitions"] = {
            "nosec_sc": {"scheme": "nosec",},
        }
        description["security"] = "nosec_sc"

        await websocket.send_json(description, mode="binary")

    def open(self):
        """Handle a new connection."""
        self.thing.add_subscriber(self)

    async def on_receive(self, websocket, data):
        """
        Handle an incoming message.
        message -- message to handle
        """
        try:
            message = json.loads(data)
        except ValueError:
            try:
                websocket.send_json(
                    {
                        "messageType": "error",
                        "data": {
                            "status": "400 Bad Request",
                            "message": "Parsing request failed",
                        },
                    },
                    mode="binary",
                )
            except WebSocketDisconnect:
                pass

            return

        if "messageType" not in message or "data" not in message:
            try:
                websocket.send_json(
                    {
                        "messageType": "error",
                        "data": {
                            "status": "400 Bad Request",
                            "message": "Invalid message",
                        },
                    },
                    mode="binary",
                )
            except WebSocketDisconnect:
                pass

            return

        msg_type = message["messageType"]
        if msg_type == "setProperty":
            for property_name, property_value in message["data"].items():
                try:
                    await self.thing.set_property(property_name, property_value)
                except PropertyError as e:
                    websocket.send_json(
                        {
                            "messageType": "error",
                            "data": {"status": "400 Bad Request", "message": str(e),},
                        },
                        mode="binary",
                    )
        elif msg_type == "requestAction":
            for action_name, action_params in message["data"].items():
                input_ = None
                if "input" in action_params:
                    input_ = action_params["input"]

                action = await self.thing.perform_action(action_name, input_)
                if action:
                    asyncio.create_task(perform_action(action))
                else:
                    websocket.send_json(
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
                await self.thing.add_event_subscriber(event_name, self)
        else:
            try:
                websocket.send_json(
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
            except WebSocketDisconnect:
                pass

    async def on_disconnect(self, websocket):
        """Handle a close event on the socket."""
        await self.thing.remove_subscriber(self)

    def check_origin(self, origin):
        """Allow connections from all origins."""
        return True

    def update_property(self, property_):
        """
        Send an update about a Property.
        :param property_: Property
        """
        message = json.dumps(
            {
                "messageType": "propertyStatus",
                "data": {property_.name: property_.get_value(),},
            }
        )

        self.write_message(message)

    def update_action(self, action):
        """
        Send an update about an Action.
        :param action: Action
        """
        message = json.dumps(
            {"messageType": "actionStatus", "data": action.as_action_description(),}
        )

        self.write_message(message)

    def update_event(self, event):
        """
        Send an update about an Event.
        :param event: Event
        """
        message = json.dumps(
            {"messageType": "event", "data": event.as_event_description(),}
        )

        self.write_message(message)


class PropertiesHandler(BaseHandler):
    """Handle a request to /properties."""

    async def get(self, request):
        """
        Handle a GET request.
        thing_id -- ID of the thing this request is for
        """
        thing_id = request.path_params.get("thing_id", "0")
        thing = await self.get_thing(thing_id)
        if thing is None:
            raise HTTPException(status_code=404)

        return UJSONResponse(thing.get_properties())


class PropertyHandler(BaseHandler):
    """Handle a request to /properties/<property>."""

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

        if thing.has_property(property_name):
            return UJSONResponse({property_name: thing.get_property(property_name),})
        else:
            raise HTTPException(status_code=404)

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
            args = json.loads(self.request.body.decode())
        except ValueError:
            raise HTTPException(status_code=400)

        if property_name not in args:
            raise HTTPException(status_code=400)

        if thing.has_property(property_name):
            try:
                thing.set_property(property_name, args[property_name])
            except PropertyError:
                raise HTTPException(status_code=400)

            return UJSONResponse({property_name: thing.get_property(property_name),})
        else:
            raise HTTPException(status_code=404)


class ActionsHandler(BaseHandler):
    """Handle a request to /actions."""

    async def get(self, request):
        """
        Handle a GET request.
        thing_id -- ID of the thing this request is for
        """
        thing_id = request.path_params.get("thing_id", "0")

        thing = await self.get_thing(thing_id)
        if thing is None:
            raise HTTPException(status_code=404)

        return UJSONResponse(thing.get_action_descriptions())

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
            message = json.loads(self.request.body.decode())
        except ValueError:
            raise HTTPException(status_code=404)

        response = {}
        for action_name, action_params in message.items():
            input_ = None
            if "input" in action_params:
                input_ = action_params["input"]

            action = thing.perform_action(action_name, input_)
            if action:
                response.update(action.as_action_description())

                # Start the action
                asyncio.create_task(perform_action(action))

        return UJSONResponse(response, status_code=201)


class ActionHandler(BaseHandler):
    """Handle a request to /actions/<action_name>."""

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

        return UJSONResponse(thing.get_action_descriptions(action_name=action_name))

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
            message = json.loads(self.request.body.decode())
        except ValueError:
            raise HTTPException(status_code=404)

        response = {}
        for name, action_params in message.items():
            if name != action_name:
                continue

            input_ = None
            if "input" in action_params:
                input_ = action_params["input"]

            action = thing.perform_action(name, input_)
            if action:
                response.update(action.as_action_description())

                # Start the action
                asyncio.create_task(perform_action(action))

        return UJSONResponse(response, status_code=201)


class ActionIDHandler(BaseHandler):
    """Handle a request to /actions/<action_name>/<action_id>."""

    async def get(self, request):
        """
        Handle a GET request.
        thing_id -- ID of the thing this request is for
        action_name -- name of the action from the URL path
        action_id -- the action ID from the URL path
        """
        thing_id = request.path_params.get("thing_id", "0")
        action_name = request.path_params.get("action_name", None)
        action_id = request.path_params.get("action_name", None)

        thing = await self.get_thing(thing_id)
        if thing is None:
            raise HTTPException(status_code=404)

        action = thing.get_action(action_name, action_id)
        if action is None:
            raise HTTPException(status_code=404)

        return UJSONResponse(action.as_action_description())

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
        action_id = request.path_params.get("action_name", None)

        thing = await self.get_thing(thing_id)
        if thing is None:
            raise HTTPException(status_code=404)

        self.set_status(200)

    async def delete(self, request):
        """
        Handle a DELETE request.
        thing_id -- ID of the thing this request is for
        action_name -- name of the action from the URL path
        action_id -- the action ID from the URL path
        """
        thing_id = request.path_params.get("thing_id", "0")
        action_name = request.path_params.get("action_name", None)
        action_id = request.path_params.get("action_name", None)

        thing = await self.get_thing(thing_id)
        if thing is None:
            raise HTTPException(status_code=404)

        if thing.remove_action(action_name, action_id):
            self.set_status(204)
        else:
            raise HTTPException(status_code=404)


class EventsHandler(BaseHandler):
    """Handle a request to /events."""

    async def get(self, request):
        """
        Handle a GET request.
        thing_id -- ID of the thing this request is for
        """
        thing_id = request.path_params.get("thing_id", "0")

        thing = await self.get_thing(thing_id)
        if thing is None:
            raise HTTPException(status_code=404)

        return UJSONResponse(thing.get_event_descriptions())


class EventHandler(BaseHandler):
    """Handle a request to /events/<event_name>."""

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

        return UJSONResponse(thing.get_event_descriptions(event_name=event_name))

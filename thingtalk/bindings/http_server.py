from __future__ import annotations

import copy
import asyncio

from typing import TYPE_CHECKING, Optional, Any

from fastapi import FastAPI
from fastapi.exceptions import HTTPException
from fastapi.params import Depends
from fastapi.requests import Request
from fastapi.responses import UJSONResponse, Response
from fastapi.routing import APIRouter
import uvicorn

from thingtalk.models.errors import PropertyError
from thingtalk.utils import get_http_host, get_ws_host

if TYPE_CHECKING:
    from thingtalk.servient import Servient
from thingtalk.models.thing import ExposedThing
from ..protocol_interfaces import ProtocolServer


class HttpServer(ProtocolServer):
    """
    A HTTP server that can be used to serve ThingTalk code.
    """

    def __init__(self, host='localhost', port='8000', path="", prefix="", **kwargs):
        """
        Initialize the HTTP server.

        :param host: The hostname to bind to.
        :param port: The port to bind to.
        :param path: The path to serve ThingTalk code from.
        """
        super().__init__(**kwargs)
        self.host = host
        self.port = port
        self.path = path
        self.prefix = prefix
        self.app = FastAPI()
        self.expose()
        # self.thing_router = APIRouter()
        # self.add_thing_handler()
        # self.app.include_router(self.thing_router, tags=["things"])
        # self.property_router = APIRouter()
        # self.action_router = APIRouter()
        # self.event_router = APIRouter()

    def start(self, servient: Servient):
        """
        Start the HTTP server.
        """
        self.servient = servient
        # config = Config(app=self.app, loop="none", host=self.host, port=self.port)
        # server = Server(config=config)
        # await server.serve(sockets=None)
        uvicorn.run(self.app, loop="none", host=self.host, port=self.port, log_level="info")

    def expose(self) -> None:
        """
        Expose a ThingTalk thing to the HTTP server.
        """
        # self.app.include_router(self.router, prefix=self.prefix)
        self.app.include_router(self.add_thing_handler(), prefix=self.prefix, tags=["things"])
        self.app.include_router(self.add_action_handler(), prefix=self.prefix, tags=["actions"])
        self.app.include_router(self.add_property_handler(), prefix=self.prefix, tags=["properties"])
        self.app.include_router(self.add_event_handler(), prefix=self.prefix, tags=["events"])

    def get_thing(self, thing_id: str) -> ExposedThing:
        """
        Get a thing by its ID.
        """
        thing = self.servient.getThing(thing_id)
        if not thing:
            raise HTTPException(status_code=404, detail=f"Thing {thing_id} not found")
        return thing

    def add_thing_handler(self) -> APIRouter:
        thing_router = APIRouter()
        
        @thing_router.get("/things")
        async def get_things(request: Request) -> UJSONResponse:
            """
            Handle a request to / when the server manages multiple things.
            Handle a GET request.
            :param request -- the request
            :return UJSONResponse
            """
            things = self.servient.things

            descriptions = []
            for idx, thing in tuple(things.items()):
                description = thing.get_thing_description()

                description["links"].append(
                    {
                        "rel": "alternate",
                        "href": f"{get_ws_host(request)}{thing.href}",
                    }
                )
                description["base"] = f"{get_http_host(request)}{thing.href}"

                description["securityDefinitions"] = {
                    "nosec_sc": {
                        "scheme": "nosec",
                    },
                }
                description["security"] = "nosec_sc"

                bak = copy.deepcopy(description)
                descriptions.append(bak)

            return UJSONResponse(descriptions)


        @thing_router.get("/things/{thing_id}")
        async def get_thing_by_id(
            request: Request, thing: ExposedThing = Depends(self.get_thing)
        ) -> UJSONResponse:
            """
            Handle a GET request, including websocket requests.
            :param request: the request
            :param thing -- the thing this request is for
            :return UJSONResponse
            """
            description = thing.get_thing_description()
            description["href"] = thing.href
            description["links"].append(
                {
                    "rel": "alternate",
                    "href": f"{get_ws_host(request)}{thing.href}",
                }
            )
            description["base"] = f"{get_http_host(request)}{thing.href}"
            description["securityDefinitions"] = {
                "nosec_sc": {
                "scheme": "nosec",
                },
            }
            description["security"] = "nosec_sc"

            return UJSONResponse(description)

        return thing_router


    def add_property_handler(self) -> APIRouter:
        property_router = APIRouter()
        
        @property_router.get("/properties")
        async def get_properties(thing: ExposedThing = Depends(self.get_thing)) -> UJSONResponse:
            """
            Handle a request to /properties.
            :param thing -- the thing this request is for"
            :return: UJSONResponse
            """
            return UJSONResponse(await thing.get_properties())

        @property_router.get("/properties/{property_name}")
        async def get_property(
            property_name: str,
            thing: ExposedThing = Depends(self.get_thing)) -> UJSONResponse:
            """
            Handle a request to /properties/<property>.
            :param: thing-- the thing this request is for"
            :param: property_name -- name of the thing property this request is for
            :return: UJSONResponse
            """
            if not thing.has_property(property_name):
                raise HTTPException(status_code=404, detail=f"Property {property_name} not found")
            return UJSONResponse(
                {property_name: thing.get_property(property_name), }
            )


        @property_router.put("/properties/{property_name}")
        async def put_property(
            property_name: str,
            data: dict[str, Any],
            thing: ExposedThing = Depends(self.get_thing)) -> UJSONResponse:
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
                {property_name: thing.get_property(property_name), }
            )

        return property_router
    
    def add_action_handler(self) -> APIRouter:
        action_router = APIRouter()
        
        async def perform_action(action):
            """Perform an Action in a coroutine."""
            await action.start()

        @action_router.get("/actions")
        async def get_actions(thing: ExposedThing = Depends(self.get_thing)) -> UJSONResponse:
            """
            Handle a request to /actions.
            :param thing-- the thing this request is for
            :return UJSONResponse
            """
            return UJSONResponse(thing.get_action_descriptions())


        @action_router.post("/actions")
        async def revoke_actions(
            message: dict[str, Any],
            thing: ExposedThing = Depends(self.get_thing)) -> UJSONResponse:
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
                action = await thing.perform_action(action_name, input_)
                if action:
                    response.update(action.description)

                    # Start the action
                    asyncio.create_task(perform_action(action))

            return UJSONResponse(response, status_code=201)


        @action_router.get("/actions/{action_name}")
        async def get_action(
            action_name: str,
            thing: ExposedThing = Depends(self.get_thing)) -> UJSONResponse:
            """
            Handle a request to /actions/<action_name>.
            :param thing -- the thing this request is for
            :param action_name -- name of the action from the URL path
            :return UJSONResponse
            """
            return UJSONResponse(
                thing.get_action_descriptions(action_name=action_name)
            )


        @action_router.post("/actions/{action_name}")
        async def invoke_action(
            action_name: str,
            message: dict[str, Any],
            thing: ExposedThing = Depends(self.get_thing)) -> UJSONResponse:
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
                    response.update(action.description)

                    # Start the action
                    asyncio.create_task(perform_action(action))

            return UJSONResponse(response, status_code=201)


        @action_router.get("/actions/{action_name}/{action_id}")
        async def get_action_by_id(
            action_name: str,
            action_id: str,
            thing: ExposedThing = Depends(self.get_thing)) -> UJSONResponse:
            """
            Handle a request to /actions/<action_name>/<action_id>.
            :param thing -- the thing this request is for
            :param action_name -- name of the action from the URL path
            :param action_id -- the action ID from the URL path
            :return UJSONResponse
            """
            action = thing.get_action(action_name, action_id)
            if action is None:
                raise HTTPException(status_code=404)

            return UJSONResponse(action.description)


        @action_router.put("/actions/{action_name}/{action_id}")
        async def update_action_by_id(
            action_name: str,
            action_id: str,
            thing: ExposedThing = Depends(self.get_thing)) -> UJSONResponse:
            """
            Handle a PUT request.
            TODO: this is not yet defined in the spec
            :param thing -- the thing this request is for
            :param action_name -- name of the action from the URL path
            :param action_id -- the action ID from the URL path
            :return UJSONResponse
            """
            return UJSONResponse({"msg": "success"}, status_code=200)


        @action_router.delete("/actions/{action_name}/{action_id}")
        async def cancel_action_by_id(
            action_name: str,
            action_id: str,
            thing: ExposedThing = Depends(self.get_thing)) -> Response:
            """
            Handle a DELETE request.
            :param thing -- the thing this request is for
            :param action_name -- name of the action from the URL path
            :param action_id -- the action ID from the URL path
            :return UJSONResponse
            """
            if await thing.remove_action(action_name, action_id):
                return Response(status_code=204)
            else:
                raise HTTPException(status_code=404)

        return action_router

    def add_event_handler(self) -> APIRouter:
        event_router = APIRouter()
        
        @event_router.get("/events")
        async def get_events(thing: ExposedThing = Depends(self.get_thing)) -> UJSONResponse:
            """
            Handle a request to /events.
            :param thing -- the thing this request is for
            :return UJSONResponse
            """
            return UJSONResponse(thing.get_event_descriptions())


        @event_router.get("/events/{event_name}")
        async def get_event(event_name: str, thing: ExposedThing = Depends(self.get_thing)) -> UJSONResponse:
            """
            Handle a request to /events/<event_name>.
            :param thing -- the thing this request is for
            :param event_name -- name of the event from the URL path
            :return UJSONResponse
            """
            return UJSONResponse(thing.get_event_descriptions(event_name=event_name))

        return event_router
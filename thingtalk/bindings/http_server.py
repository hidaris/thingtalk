from __future__ import annotations

import copy
import asyncio

from typing import TYPE_CHECKING, Optional, Any

from fastapi import FastAPI
from fastapi.exceptions import HTTPException
from fastapi.requests import Request
from fastapi.responses import UJSONResponse, Response
from fastapi.routing import APIRouter
import uvicorn

from thingtalk.models.errors import PropertyError

if TYPE_CHECKING:
    from thingtalk.servient import Servient
    from thingtalk.models.thing import ExposedThing
from ..protocol_interfaces import ProtocolServer
from routers import things, actions, events, properties


class HttpServer(ProtocolServer):
    """
    A HTTP server that can be used to serve ThingTalk code.
    """

    def __init__(self, host, port, path, prefix, **kwargs):
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
        self.router = APIRouter()

    async def start(self, servient: Servient):
        """
        Start the HTTP server.
        """
        self.servient = servient
        uvicorn.run(self.app, host=self.host, port=self.port, log_level="info")

    async def expose(self, thing: ExposedThing, tdTemplate) -> None:
        """
        Expose a ThingTalk thing to the HTTP server.
        """
        self.app.include_router(self.router, prefix=self.prefix)
        self.app.include_router(things.router, prefix=self.prefix, tags=["things"])
        self.app.include_router(actions.router, prefix=self.prefix, tags=["actions"])
        self.app.include_router(properties.router, prefix=self.prefix, tags=["properties"])
        self.app.include_router(events.router, prefix=self.prefix, tags=["properties"])

    def directory(self):
        @self.router.get("/things")
        async def get_things(request: Request) -> UJSONResponse:
            """
            Handle a request to / when the server manages multiple things.
            Handle a GET request.
            :param request -- the request
            :return UJSONResponse
            """
            things = self.servient.things

            descriptions = []
            for idx, thing in tuple(things.get_things()):
                description = thing.as_thing_description()

                description["links"].append(
                    {
                        "rel": "alternate",
                        "href": f"{get_ws_href(request)}{thing.href}",
                    }
                )
                description["base"] = f"{get_http_href(request)}{thing.href}"

                description["securityDefinitions"] = {
                    "nosec_sc": {
                        "scheme": "nosec",
                    },
                }
                description["security"] = "nosec_sc"

                bak = copy.deepcopy(description)
                descriptions.append(bak)

            return UJSONResponse(descriptions)


        @self.router.get("/things/{thing_id}")
        async def get_thing_by_id(
            request: Request, thing: ExposedThing = Depends(get_thing)
        ) -> UJSONResponse:
            """
            Handle a GET request, including websocket requests.
            :param request: the request
            :param thing -- the thing this request is for
            :return UJSONResponse
            """
            thing = self.servient.getThing(thing.id)
            if not thing:
                raise HTTPException(status_code=404, detail="Thing not found")
            description = thing.as_thing_description()
            description["href"] = thing.href
            description["links"].append(
                {
                    "rel": "alternate",
                    "href": f"{get_ws_href(request)}{thing.href}",
                }
            )
            description["base"] = f"{get_http_href(request)}{thing.href}"
            description["securityDefinitions"] = {
                "nosec_sc": {
                "scheme": "nosec",
                },
            }
            description["security"] = "nosec_sc"

            return UJSONResponse(description)


    def add_property_handler(self):
        @self.router.get("/properties")
        async def get_properties(thing: ExposedThing = Depends(get_thing)) -> UJSONResponse:
            """
            Handle a request to /properties.
            :param thing -- the thing this request is for"
            :return: UJSONResponse
            """
            thing = self.servient.getThing(thing.id)
            if not thing:
                raise HTTPException(status_code=404, detail="Thing not found")
            return UJSONResponse(await thing.get_properties())

        @self.router.get("/properties/{property_name}")
        async def get_property(
            property_name: str,
            thing: ExposedThing = Depends(check_property_and_get_thing)) -> UJSONResponse:
            """
            Handle a request to /properties/<property>.
            :param: thing-- the thing this request is for"
            :param: property_name -- name of the thing property this request is for
            :return: UJSONResponse
            """
            thing = self.servient.getThing(thing.id)
            if not thing:
                raise HTTPException(status_code=404, detail="Thing not found")
            return UJSONResponse(
                {property_name: thing.get_property(property_name), }
            )


        @self.router.put("/properties/{property_name}")
        async def put_property(
            property_name: str,
            data: dict[str, Any],
            thing: ExposedThing = Depends(get_thing)) -> UJSONResponse:
            """
            Handle a PUT request to /properties/<property>.
            :param property_name -- the name of the property from the URL path
            :param data -- data of this request put
            :param thing -- the thing this request is for
            :return: UJSONResponse
            """
            thing = self.servient.getThing(thing.id)
            if not thing:
                raise HTTPException(status_code=404, detail="Thing not found")
            try:
                await thing.set_property(property_name, data[property_name])
            except PropertyError:
                raise HTTPException(status_code=400)

            return UJSONResponse(
                {property_name: thing.get_property(property_name), }
            )
    
    def add_action_handler(self):
        async def perform_action(action):
            """Perform an Action in a coroutine."""
            await action.start()

        @self.router.get("/actions")
        async def get_actions(thing: ExposedThing = Depends(get_thing)) -> UJSONResponse:
            """
            Handle a request to /actions.
            :param thing-- the thing this request is for
            :return UJSONResponse
            """
            return UJSONResponse(thing.get_action_descriptions())


        @self.router.post("/actions")
        async def revoke_actions(
            message: dict[str, Any],
            thing: ExposedThing = Depends(get_thing)) -> UJSONResponse:
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


        @self.router.get("/actions/{action_name}")
        async def get_action(
            action_name: str,
            thing: ExposedThing = Depends(get_thing)) -> UJSONResponse:
            """
            Handle a request to /actions/<action_name>.
            :param thing -- the thing this request is for
            :param action_name -- name of the action from the URL path
            :return UJSONResponse
            """
            return UJSONResponse(
                thing.get_action_descriptions(action_name=action_name)
            )


        @self.router.post("/actions/{action_name}")
        async def invoke_action(
            action_name: str,
            message: dict[str, Any],
            thing: ExposedThing = Depends(get_thing)) -> UJSONResponse:
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


        @self.router.get("/actions/{action_name}/{action_id}")
        async def get_action_by_id(
            action_name: str,
            action_id: str,
            thing: ExposedThing = Depends(get_thing)) -> UJSONResponse:
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


        @self.router.put("/actions/{action_name}/{action_id}")
        async def update_action_by_id(
            action_name: str,
            action_id: str,
            thing: ExposedThing = Depends(get_thing)) -> UJSONResponse:
            """
            Handle a PUT request.
            TODO: this is not yet defined in the spec
            :param thing -- the thing this request is for
            :param action_name -- name of the action from the URL path
            :param action_id -- the action ID from the URL path
            :return UJSONResponse
            """
            return UJSONResponse({"msg": "success"}, status_code=200)


        @self.router.delete("/actions/{action_name}/{action_id}")
        async def cancel_action_by_id(
            action_name: str,
            action_id: str,
            thing: ExposedThing = Depends(get_thing)) -> Response:
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

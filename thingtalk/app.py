import socket

from typing import Any, Callable, Coroutine, Dict, List, Optional, Sequence, Type, Union

from starlette.routing import BaseRoute
from starlette.requests import Request
from starlette.middleware import Middleware
from starlette.responses import Response, JSONResponse

from fastapi import FastAPI, APIRouter
from fastapi.params import Depends
from fastapi.datastructures import Default

from loguru import logger
from zeroconf.asyncio import AsyncZeroconf, ServiceInfo

from .routers.mqtt import ThingMqtt
from .utils import get_ip
from .models.thing import Server, ExposedThing
from .models.containers import MultipleThings, SingleThing
from .toolkits import mb


class ThingTalk(FastAPI):

    def __init__(
            self,
            *,
            debug: bool = False,
            routes: Optional[List[BaseRoute]] = None,
            title: str = "FastAPI",
            description: str = "",
            version: str = "0.1.0",
            openapi_url: Optional[str] = "/openapi.json",
            openapi_tags: Optional[List[Dict[str, Any]]] = None,
            servers: Optional[List[Dict[str, Union[str, Any]]]] = None,
            dependencies: Optional[Sequence[Depends]] = None,
            default_response_class: Type[Response] = Default(JSONResponse),
            docs_url: Optional[str] = "/docs",
            redoc_url: Optional[str] = "/redoc",
            swagger_ui_oauth2_redirect_url: Optional[str] = "/docs/oauth2-redirect",
            swagger_ui_init_oauth: Optional[Dict[str, Any]] = None,
            middleware: Optional[Sequence[Middleware]] = None,
            exception_handlers: Optional[
                Dict[
                    Union[int, Type[Exception]],
                    Callable[[Request, Any], Coroutine[Any, Any, Response]],
                ]
            ] = None,
            on_startup: Optional[Sequence[Callable[[], Any]]] = None,
            on_shutdown: Optional[Sequence[Callable[[], Any]]] = None,
            openapi_prefix: str = "",
            root_path: str = "",
            root_path_in_servers: bool = True,
            responses: Optional[Dict[Union[int, str], Dict[str, Any]]] = None,
            callbacks: Optional[List[BaseRoute]] = None,
            deprecated: Optional[bool] = None,
            include_in_schema: bool = True,
            mode: str = "single",
            mqtt: Optional[ThingMqtt] = None,
            thing: Optional[ExposedThing] = None,
            **extra: Any) -> None:
        super().__init__(debug=debug, routes=routes, title=title, description=description, version=version,
                         openapi_url=openapi_url, openapi_tags=openapi_tags, servers=servers, dependencies=dependencies,
                         default_response_class=default_response_class, docs_url=docs_url, redoc_url=redoc_url,
                         swagger_ui_oauth2_redirect_url=swagger_ui_oauth2_redirect_url,
                         swagger_ui_init_oauth=swagger_ui_init_oauth, middleware=middleware,
                         exception_handlers=exception_handlers, on_startup=on_startup, on_shutdown=on_shutdown,
                         openapi_prefix=openapi_prefix, root_path=root_path, root_path_in_servers=root_path_in_servers,
                         responses=responses, callbacks=callbacks, deprecated=deprecated,
                         include_in_schema=include_in_schema, **extra)
        self.state.mode = mode
        self.state.mqtt = mqtt

        if mode in ["gateway", "multiple"]:
            assert mqtt is not None, "if running mode is gateway, mqtt shouldn't be none"
            self.state.things = MultipleThings({}, self.state.mode)
        else:
            assert thing is not None, "if running mode is single, parameter thing shouldn't be none"
            self.state.things = SingleThing(thing)

        self.post_init()

    def post_init(self):
        zeroconf = AsyncZeroconf()

        @self.on_event("startup")
        async def start_mdns():
            """Start listening for incoming connections."""
            name = self.state.things.get_name()
            args = [
                "_webthing._tcp.local.",
                f"{name}._webthing._tcp.local.",
            ]
            kwargs = {
                "port": 8000,
                "properties": {
                    "path": "/",
                },
                "server": f"{socket.gethostname()}.local.",
                "addresses": [socket.inet_aton(get_ip())],
            }
            self.state.service_info = ServiceInfo(*args, **kwargs)
            await zeroconf.async_register_service(self.state.service_info)

        @self.on_event("shutdown")
        async def stop_mdns():
            """Stop listening."""
            await zeroconf.async_unregister_service(self.state.service_info)
            await zeroconf.async_close()

        @self.on_event("shutdown")
        async def stop_mb():
            """Stop inner message bus"""
            mb.remove_all_listeners()

        if self.state.mode in ["gateway", "multiple"]:
            @self.on_event("startup")
            async def on_startup():
                await self.state.mqtt.set_app(self)
                await self.state.mqtt.connect()

            @self.on_event("shutdown")
            async def on_shutdown():
                await self.state.mqtt.disconnect()


# server = Server()
# server.href_prefix = f"/things/{server.id}"
# app.state.things = MultipleThings({server.id: server}, "things")


# await app.state.things.add_thing(server)


# restapi = APIRouter()
#
# restapi.include_router(things.router, tags=["thing"])
# restapi.include_router(
#     properties.router,
#     prefix="/things/{thing_id}",
#     tags=["property"],
#     responses={404: {"description": "Not found"}},
# )
# restapi.include_router(
#     actions.router,
#     prefix="/things/{thing_id}",
#     tags=["action"],
#     responses={404: {"description": "Not found"}},
# )
# restapi.include_router(
#     events.router,
#     prefix="/things/{thing_id}",
#     tags=["event"],
#     responses={404: {"description": "Not found"}},
# )
#
# app.include_router(restapi)
# app.include_router(websockets.router)

"""Python Web Thing server implementation."""

import socket
import asyncio

from zeroconf import ServiceInfo, Zeroconf
from contextlib import contextmanager
from threading import Thread

from starlette.routing import Route, WebSocketRoute
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from handlers import (
    ThingHandler,
    WsThingHandler,
    ThingsHandler,
    PropertyHandler,
    EventHandler,
    PropertiesHandler,
    ActionHandler,
    ActionsHandler,
    ActionIDHandler,
    EventsHandler,
)
from containers import SingleThing, MultipleThings
from utils import get_addresses, get_ip
from test import make_thing

# from file_thing import FileThing
from mixins import AsyncMixin


class DefaultHeaderMiddleware(BaseHTTPMiddleware):
    """Set the default headers for all requests."""

    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers[
            "Access-Control-Allow-Headers"
        ] = "Origin, X-Requested-With, Content-Type, Accept"
        response.headers[
            "Access-Control-Allow-Methods"
        ] = "GET, HEAD, PUT, POST, DELETE"

        return response


middlewares = [
    Middleware(DefaultHeaderMiddleware),
    Middleware(TrustedHostMiddleware, allowed_hosts=["localhost"]),
]


class WebThingServer(AsyncMixin):
    """Server to represent a Web Thing over HTTP."""

    def __init__(
        self,
        loop,
        things_maker,
        port=8000,
        hostname=None,
        additional_routes=None,
        base_path="",
    ):
        """
        Initialize the WebThingServer.
        For documentation on the additional route format, see:
        https://www.starlette.io/applications/
        loop -- event loop
        things_maker -- make things managed by this server -- should be of type
                  SingleThing or MultipleThings
        port -- port to listen on (defaults to 80)
        hostname -- Optional host name, i.e. mything.com
        additional_routes -- list of additional routes to add to the server
        base_path -- base URL path to use, rather than '/'
        """
        self._loop = loop
        self.things = self._run_async(things_maker())
        self.port = port
        self.hostname = hostname
        self.additional_routes = additional_routes
        self.base_path = base_path.rstrip("/")
        system_hostname = socket.gethostname().lower()
        self.hosts = [
            "localhost",
            f"localhost:{self.port}",
            f"{system_hostname}.local",
            f"{system_hostname}.local:{self.port}",
        ]

        for address in get_addresses():
            self.hosts.extend(
                [address, f"{address}:{self.port}",]
            )

        if self.hostname is not None:
            self.hostname = self.hostname.lower()
            self.hosts.extend(
                [self.hostname, f"{self.hostname}:{self.port}",]
            )

    def build_routes(self):
        return self._run_async(self._build_routes())

    async def _build_routes(self):
        if isinstance(self.things, MultipleThings):
            # for idx, thing in enumerate(await self.things.get_things()):
            for idx, thing in await self.things.get_things():
                await thing.set_href_prefix(f"/things{self.base_path}/{idx}")

            routes = [
                Route("/", ThingsHandler),
                Route("/{thing_id:str}", ThingHandler),
                Route("/{thing_id:str}/properties", PropertiesHandler),
                Route(
                    "/{thing_id:str}/properties/{property_name:str}", PropertyHandler
                ),
                Route("/{thing_id:str}/actions", ActionsHandler),
                Route("/{thing_id:str}/actions/{action_name:str}", ActionHandler),
                Route(
                    "/{thing_id:str}/actions/{action_name:str}/{action_id}",
                    ActionHandler,
                ),
                Route("/{thing_id:str}/events", EventHandler),
                Route("/{thing_id:str}/events/{event_name:str}", EventHandler),
            ]
        else:
            thing = await self.things.get_thing()
            await thing.set_href_prefix(self.base_path)
            des = await thing.as_thing_description()
            routes = [
                Route("/", ThingHandler),
                WebSocketRoute("/", WsThingHandler),
                Route("/properties", PropertiesHandler),
                Route("/properties/{property_name:str}", PropertyHandler),
                Route("/actions", ActionsHandler),
                Route("/actions/{action_name:str}", ActionHandler),
                Route("/actions/{action_name:str}/{action_id:str}", ActionIDHandler),
                Route("/events", EventsHandler),
                Route("/events/{event_name:str}", EventHandler),
            ]

        if isinstance(self.additional_routes, list):
            routes = self.additional_routes + routes

        if self.base_path:
            for h in routes:
                h[0] = self.base_path + h[0]
        return routes

    async def start(self):
        """Start listening for incoming connections."""
        self.name = await self.things.get_name()
        self.service_info = ServiceInfo(
            "_webthing._tcp.local.",
            f"{self.name}._webthing._tcp.local.",
            address=socket.inet_aton(get_ip()),
            port=self.port,
            properties={"path": "/",},
            server=f"{socket.gethostname()}.local.",
        )
        self.zeroconf = Zeroconf()
        self.zeroconf.register_service(self.service_info)
        # print(self.service_info)

    async def stop(self):
        """Stop listening."""
        self.zeroconf.unregister_service(self.service_info)
        self.zeroconf.close()


@contextmanager
def background_thread_loop():
    def run_forever(loop):
        asyncio.set_event_loop(loop)
        loop.run_forever()

    loop = asyncio.new_event_loop()
    try:
        thread = Thread(target=run_forever, args=(loop,))
        thread.start()
        yield loop
    finally:
        loop.call_soon_threadsafe(loop.stop)
        thread.join()


with background_thread_loop() as loop:
    # server = WebThingServer(loop, FileThing().build)
    server = WebThingServer(loop, make_thing)
    routes = server.build_routes()

app = Starlette(
    debug=True, routes=routes, on_startup=[server.start], on_shutdown=[server.stop],
)

app.state.things = server.things

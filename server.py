"""Python Web Thing server implementation."""

from zeroconf import ServiceInfo, Zeroconf
import socket
import asyncio
import uvicorn

from starlette.routing import Route
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from handlers import (
    ThingHandler,
    ThingsHandler,
    PropertyHandler,
    EventHandler,
    PropertiesHandler,
    ActionHandler,
    ActionsHandler,
    EventsHandler,
)
from containers import SingleThing, MultipleThings
from utils import get_addresses, get_ip
from test import make_thing


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


class WebThingServer:
    """Server to represent a Web Thing over HTTP."""

    def __init__(
        self, things, port=8000, hostname=None, additional_routes=None, base_path=""
    ):
        print("before create")
        return asyncio.run_coroutine_threadsafe(
            self.create(things, port, hostname, additional_routes, base_path),
            asyncio.get_running_loop(),
        ).result()

    async def create(
        self, things, port=8000, hostname=None, additional_routes=None, base_path=""
    ):
        """
        Initialize the WebThingServer.
        For documentation on the additional route format, see:
        https://www.starlette.io/applications/
        things -- things managed by this server -- should be of type
                  SingleThing or MultipleThings
        port -- port to listen on (defaults to 80)
        hostname -- Optional host name, i.e. mything.com
        additional_routes -- list of additional routes to add to the server
        base_path -- base URL path to use, rather than '/'
        """
        print(type(things))
        self.things = things
        self.name = await things.get_name()
        self.port = port
        self.hostname = hostname
        self.base_path = base_path.rstrip("/")
        print("create")
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

        if isinstance(self.things, MultipleThings):
            for idx, thing in enumerate(await self.things.get_things()):
                await thing.set_href_prefix(f"{self.base_path}/{idx}")

            routes = [
                Route("/", ThingsHandler),
                Route("/{thing_id:int}", ThingHandler),
                Route("/{thing_id:int}/properties", PropertiesHandler),
                Route("/{thing_id:int}/properties/{property_name}", PropertyHandler),
                Route("/{thing_id:int}/actions", ActionsHandler),
                Route("/{thing_id:int}/actions/{action_name}", ActionHandler),
                Route(
                    "/{thing_id:int}/actions/{action_name}/{action_id}", ActionHandler
                ),
                Route("/{thing_id:int}/events", EventHandler),
                Route("/{thing_id:int}/events/{event_name}", EventHandler),
            ]
        else:
            thing = await self.things.get_thing()
            await thing.set_href_prefix(self.base_path)
            routes = [
                Route("/", ThingHandler),
                Route("/properties", PropertiesHandler),
                Route("/properties/{property_name}", PropertyHandler),
                Route("/actions", ActionsHandler),
                Route("/actions/{action_name}", ActionHandler),
                Route("/actions/{action_name}/{action_id}", ActionHandler),
                Route("/events", EventsHandler),
                Route("/events/{event_name}", EventHandler),
            ]

        if isinstance(additional_routes, list):
            routes = additional_routes + routes

        self.routes = routes

        if self.base_path:
            for h in self.routes:
                h[0] = self.base_path + h[0]

    async def start(self):
        """Start listening for incoming connections."""
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
        print("start")

    async def stop(self):
        """Stop listening."""
        self.zeroconf.unregister_service(self.service_info)
        self.zeroconf.close()
        print("stop")


if __name__ == "__main__":
    thing = asyncio.run_coroutine_threadsafe(
        make_thing(), asyncio.get_running_loop()
    ).result()

    print("before app")
    server = WebThingServer(SingleThing(thing))

    app = Starlette(
        debug=True,
        routes=server.routes,
        on_startup=[server.start],
        on_shutdown=[server.stop],
    )

    app.state.things = server.things

    uvicorn.run("example:app", host="127.0.0.1", port=8000, log_level="info")

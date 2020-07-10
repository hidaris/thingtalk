"""Python Web Thing server implementation."""

import socket

from zeroconf import ServiceInfo, Zeroconf

from starlette.routing import Route, WebSocketRoute, Mount
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.middleware.authentication import AuthenticationMiddleware

from .handlers import (
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
from .containers import (
    MultipleThings, SingleThing, DevicePairingEvent, DeviceRemoveEvent
)
from .utils import get_addresses, get_ip
from .mixins import AsyncMixin
from .thing import Thing
from .value import Value
from .property import Property


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
    Middleware(TrustedHostMiddleware, allowed_hosts=["*"]),
]


class Server(Thing):
    type = ["Server"]
    description = "Webthing Server"

    def __init__(self):
        super().__init__(
            "urn:webthing:server",
            "Webthing Server",
        )

    async def build(self):
        await self.add_property(
            Property(
                "state",
                Value("ON"),
                metadata={
                    "@type": "ServerStateProperty",
                    "title": "State",
                    "type": "string",
                    "enum": ["ON", "OFF", "REBOOT"],
                    "description": "state of webthing server",
                },
            )
        )

        await self.add_available_event(
            DevicePairingEvent,
            {
                "description": "new device",
                "type": "object",
                "required": ["@type", "id", "title"],
                "properties": {
                    "@type": {
                        "type": "array",
                    },
                    "id": {
                        "type": "string",
                    },
                    "title": {
                        "type": "string",
                    },
                },
            }
        )

        await self.add_available_event(
            DeviceRemoveEvent,
            {
                "description": "device removed event",
                "type": "object",
                "required": ["id", "title"],
                "properties": {
                    "id": {
                        "type": "string",
                    },
                    "title": {
                        "type": "string",
                    },
                },
            }
        )

        return self


class WebThingServer(AsyncMixin):
    """Server to represent a Web Thing over HTTP."""

    def __init__(
            self,
            loop,
            thing_cls=None,
            port=8000,
            hostname=None,
            base_path="",
            additional_routes=None,
            additional_middlewares=None,
            additional_on_startup=None,
            additional_on_shutdown=None,
    ):
        """
        Initialize the WebThingServer.
        For documentation on the additional route format, see:
        https://www.starlette.io/applications/
        loop -- event loop
        thing_cls -- make things managed by this server -- should be of type
                  Thing or List of Things
        port -- port to listen on (defaults to 8000)
        hostname -- Optional host name, i.e. mything.com
        base_path -- base URL path to use, rather than '/'
        additional_routes -- list of additional routes to add to the server
        additional_middlewares -- list of additional middlewares
        additional_on_startup -- list of additional starup event handlers
        additional_on_shutdown -- list of additional shutdown event handlers
        """
        self._loop = loop
        server = self._run_async(Server().build())
        self.things = MultipleThings({server.id: server}, "things")
        self.thing_cls = thing_cls if isinstance(thing_cls, list) else [thing_cls]
        self.port = port
        self.hostname = hostname
        self.base_path = base_path.rstrip("/") if base_path else "/things"
        self.additional_routes = additional_routes
        self.additional_middlewares = additional_middlewares
        self.additional_on_startup = [] if additional_on_startup is None else list(additional_on_startup)
        self.additional_on_shutdown = [] if additional_on_shutdown is None else list(additional_on_shutdown)
        system_hostname = socket.gethostname().lower()

        self.hosts = [
            "localhost",
            f"localhost:{self.port}",
            f"{system_hostname}.local",
            f"{system_hostname}.local:{self.port}",
        ]

        for address in get_addresses():
            self.hosts.extend(
                [address, f"{address}:{self.port}", ]
            )

        if self.hostname is not None:
            self.hostname = self.hostname.lower()
            self.hosts.extend(
                [self.hostname, f"{self.hostname}:{self.port}", ]
            )

    def create(self):
        return self._run_async(self._create())

    async def config_things(self):
        for cls in self.thing_cls:
            thing = await cls().build()
            await self.things.add_thing(thing)

    async def config_routes(self):
        if isinstance(self.things, MultipleThings):
            for idx, thing in await self.things.get_things():
                await thing.set_href_prefix(f"{self.base_path}/{idx}")

            base_route = [
                Route(f"{self.base_path}",
                      ThingsHandler),
            ]
            routes = [
                Route("/{thing_id:str}",
                      ThingHandler),
                WebSocketRoute("/{thing_id:str}",
                               WsThingHandler),
                Route("/{thing_id:str}/properties",
                      PropertiesHandler),
                Route("/{thing_id:str}/properties/{property_name:str}",
                      PropertyHandler),
                Route("/{thing_id:str}/actions",
                      ActionsHandler),
                Route("/{thing_id:str}/actions/{action_name:str}",
                      ActionHandler),
                Route("/{thing_id:str}/actions/{action_name:str}/{action_id}",
                      ActionHandler),
                Route("/{thing_id:str}/events",
                      EventHandler),
                Route("/{thing_id:str}/events/{event_name:str}",
                      EventHandler),
            ]
        else:
            thing = await self.things.get_thing()
            await thing.set_href_prefix(self.base_path)

            base_route = [
                Route(f"{self.base_path}",
                      ThingHandler),
                WebSocketRoute(f"{self.base_path}",
                               WsThingHandler),
            ]
            routes = [
                Route("/properties",
                      PropertiesHandler),
                Route("/properties/{property_name:str}",
                      PropertyHandler),
                Route("/actions",
                      ActionsHandler),
                Route("/actions/{action_name:str}",
                      ActionHandler),
                Route("/actions/{action_name:str}/{action_id:str}",
                      ActionIDHandler),
                Route("/events",
                      EventsHandler),
                Route("/events/{event_name:str}",
                      EventHandler),
            ]

        if isinstance(self.additional_routes, list):
            routes = self.additional_routes + routes

        if self.base_path:
            routes = base_route + [
                # Route('/', homepage),
                Mount(f"{self.base_path}", routes=routes),
            ]

        return routes

    async def config_middlewares(self):
        middlewares = []
        if self.additional_middlewares:
            assert isinstance(self.additional_middlewares, list)
            middlewares.extend(self.additional_middlewares)

        return middlewares

    async def config_on_startups(self):
        on_startups = [self.start]
        if self.additional_on_startup:
            on_startups.extend(self.additional_on_startup)

        return on_startups

    async def config_on_shutdowns(self):
        on_shutdowns = [self.stop]
        if self.additional_on_shutdown:
            assert isinstance(self.additional_on_shutdown, list)
            on_shutdowns.extend(self.additional_on_shutdown)

        return on_shutdowns

    async def _create(self):
        await self.config_things()
        routes = await self.config_routes()
        middlewares = await self.config_middlewares()
        on_startups = await self.config_on_startups()
        on_shutdowns = await self.config_on_shutdowns()

        app = Starlette(
            debug=True, routes=routes, middleware=middlewares, on_startup=on_startups, on_shutdown=on_shutdowns,
        )

        app.state.things = self.things

        require_auth = False
        for middleware in middlewares:
            if middleware.cls == AuthenticationMiddleware:
                require_auth = True

        app.state.require_auth = require_auth

        return app

    async def start(self):
        """Start listening for incoming connections."""
        name = await self.things.get_name()
        args = [
            '_webthing._tcp.local.',
            f"{name}._webthing._tcp.local.",
        ]
        kwargs = {'port': self.port, 'properties': {
            'path': '/',
        }, 'server': '{}.local.'.format(socket.gethostname()), 'addresses': [socket.inet_aton(get_ip())]}
        self.service_info = ServiceInfo(*args, **kwargs)
        self.zeroconf = Zeroconf()
        self.zeroconf.register_service(self.service_info)

    async def stop(self):
        """Stop listening."""
        self.zeroconf.unregister_service(self.service_info)
        self.zeroconf.close()

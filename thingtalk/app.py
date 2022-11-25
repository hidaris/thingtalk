import socket

from typing import Optional, Sequence

from fastapi import FastAPI, APIRouter, Depends

from loguru import logger
from zeroconf.asyncio import AsyncZeroconf, AsyncServiceInfo

from .models.thing import Server
from .models.containers import MultipleThings
from .routers import things, properties, actions, events, websockets
from .utils import get_ip


class ThingTalk:
    def __init__(
            self,
            title: str = "ThingTalk",
            description: str = "",
            version: str = "0.1.0",
            dependencies: Optional[Sequence[Depends]] = None
    ) -> None:
        self.app = FastAPI(
            title=title,
            version=version,
            description=description,
            dependencies=dependencies
        )

        server = Server()
        server.href_prefix = f"/things/{server._id}"
        self.app.state.things = MultipleThings({server._id: server}, "things")
        self.include_routers()
        self.register_mdns()

    def register_mdns(self):
        zeroconf = AsyncZeroconf()

        @self.app.on_event("startup")
        async def start_mdns():
            """Start listening for incoming connections."""
            name = await self.app.state.things.get_name()
            args = [
                '_webthing._tcp.local.',
                f"{name}._webthing._tcp.local.",
            ]
            kwargs = {
                'port': '8000',  # port,
                'properties': {
                    'path': '/',
                },
                'server': f"{socket.gethostname()}.local.",
                'addresses': [socket.inet_aton(get_ip())]
            }
            self.app.state.service_info = AsyncServiceInfo(*args, **kwargs)
            await zeroconf.async_register_service(self.app.state.service_info)

        @self.app.on_event("shutdown")
        async def stop_mdns():
            """Stop listening."""
            await zeroconf.async_unregister_service(self.app.state.service_info)
            await zeroconf.async_close()

    def include_routers(self):
        restapi = APIRouter()

        restapi.include_router(things.router, tags=["thing"])
        restapi.include_router(
            properties.router,
            prefix="/things/{thing_id}",
            tags=["property"],
            responses={404: {"description": "Not found"}},
        )
        restapi.include_router(
            actions.router,
            prefix="/things/{thing_id}",
            tags=["action"],
            responses={404: {"description": "Not found"}},
        )
        restapi.include_router(
            events.router,
            prefix="/things/{thing_id}",
            tags=["event"],
            responses={404: {"description": "Not found"}},
        )

        self.app.include_router(restapi)
        self.app.include_router(websockets.router)

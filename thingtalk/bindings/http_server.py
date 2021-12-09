
from typing import TYPE_CHECKING, Optional

from fastapi import FastAPI
import uvicorn

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
        self.server = FastAPI()

    async def start(self, servient: Servient):
        """
        Start the HTTP server.
        """
        self.servient = servient
        uvicorn.run(self.server, host=self.host, port=self.port, log_level="info")

    async def expose(self, thing: ExposedThing, tdTemplate) -> None:
        """
        Expose a ThingTalk thing to the HTTP server.
        """
        self.server.include_router(things.router, prefix=self.prefix, tags=["things"])
        self.server.include_router(actions.router, prefix=self.prefix, tags=["actions"])
        self.server.include_router(properties.router, prefix=self.prefix, tags=["properties"])
        self.server.include_router(events.router, prefix=self.prefix, tags=["properties"])

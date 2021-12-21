from __future__ import annotations

import asyncio
import json
import socket
import uvicorn

from uuid import uuid4
from typing import TYPE_CHECKING, Any, Optional, Union

from loguru import logger
from zeroconf.asyncio import AsyncZeroconf, ServiceInfo

from thingtalk.bindings.http_server import HttpServer 

from .wot_impl import WoTImpl

from .models.thing import ExposedThing 
from .utils import get_ip

if TYPE_CHECKING:
    from protocol_interfaces import ProtocolClientFactory, ProtocolServer, ProtocolClient


class Servient:
    servers: list[ProtocolServer] = [HttpServer()]
    clientFactories: dict[str, ProtocolClientFactory] = {}
    things: dict[str, ExposedThing] = {}

    def __init__(self):
        server = self.servers[0]
        assert isinstance(server, HttpServer)
        self.app = server.app
        self.mqtt = None
        self.service_info = None
        self.post_init()

    def post_init(self):
        zeroconf = AsyncZeroconf()
        # ZeroConf ServiceInfo
        # service_info: Optional[ServiceInfo] = None
        @self.app.on_event("startup")
        async def start_mdns():
            """Start listening for incoming connections."""
            # name = self.things.get_name()
            args = [
                "_webthing._tcp.local.",
                "_webthing._tcp.local.",
                # f"{name}._webthing._tcp.local.",
            ]
            kwargs = {
                "port": 8000,
                "properties": {
                    "path": "/",
                },
                "server": f"{socket.gethostname()}.local.",
                "addresses": [socket.inet_aton(get_ip())],
            }
            self.service_info = ServiceInfo(*args, **kwargs)
            await zeroconf.async_register_service(self.service_info)

        @self.app.on_event("shutdown")
        async def stop_mdns():
            """Stop listening."""
            await zeroconf.async_unregister_service(self.service_info)
            await zeroconf.async_close()

    async def expose(self, thing: ExposedThing) -> None:

        if len(self.servers) == 0:
            logger.warning('Servient has no servers to expose Things')
            return

        logger.debug(f'Servient exposing {thing.title}')

        # What is a good way to to convey forms information like contentType et cetera for interactions
        tdTemplate = thing.get_description() # json.loads(json.dumps(thing))

        # initializing forms fields
        # thing.forms = []
        # for name in thing.properties:
        #     thing.properties[name].forms = []
        # for name in thing.actions:
        #     thing.actions[name].forms = []
        # for name in thing.events:
        #     thing.events[name].forms = []

        serverTasks = []
        for server in self.servers:
            serverTasks.append(asyncio.create_task(server.expose(thing, tdTemplate)))
        
        asyncio.gather(*serverTasks)

    # def discover(self, filter: Optional[WoT.ThingFilter]) -> WoT.ThingDiscovery:
    #     return ThingDiscoveryImpl(filter)

    # async def consume(self, td: WoT.ThingDescription) -> ConsumedThing:
    #     try:
    #         thing = TD.parseTD(JSON.stringify(td), True)
    #         newThing: ConsumedThing = ConsumedThing(self.srv, thing)

    #         logger.debug(
    #             f'WoTImpl consuming TD {
    #                 newThing.id ? "'" + newThing.id + "'" : "without id"
    #             } to instantiate ConsumedThing {newThing.title}'
    #         )
    #         return newThing
    #     except Exception as e:
    #         raise Exception("Cannot consume TD because " + e.message)


    '''
     * create a new Thing
     *
     * @param title title/identifier of the thing to be created
     *'''
    def produce(self, init: Union[dict, ExposedThing]) -> ExposedThing:
        try:
            # validated = Helpers.validateExposedThingInit(init);

            # if not validated.valid:
            #     raise Exception("Thing Description JSON schema validation failed:\n" + validated.errors)
            if isinstance(init, ExposedThing):
                if self.addThing(init):
                    return init
                else:
                    raise Exception("Thing already exists: " + init.title)
            newThing = ExposedThing(self, init=init)
            logger.debug(f'WoTImpl producing new ExposedThing {newThing.title}')

            if self.addThing(newThing):
                return newThing
            else:
                raise Exception("Thing already exists: " + newThing.title)
        except Exception as e:
            raise Exception("Cannot produce ExposedThing because " + str(e))
    
    def addThing(self, thing: ExposedThing) -> bool:

        if thing.id is None:
            thing.id = f"urn:uuid:{str(uuid4())}"
            logger.warning(f'Servient generating ID for {thing.title}: {thing.id}')

        if thing.id not in self.things:
            self.things[thing.id] = thing
            logger.debug(f'Servient reset ID {thing.id} with {thing.title}')
            if len(self.servers) > 1:
                thing.bind(self.mqtt)
            else:
                # bind socket.io
                pass
            return True
        else:
            return False

    async def destroyThing(self, thingId: str):
        if thingId in self.things:
            logger.debug(f'Servient destroying thing with id {thingId}');
            del self.things[thingId]
            serverTasks = []
            for server in self.servers:
                destroy_server_task = asyncio.create_task(server.destroy(thingId))
                serverTasks.append(destroy_server_task)
            asyncio.gather(*serverTasks)
        else:
            logger.warning(f'Servient was asked to destroy thing but failed to find thing with id {thingId}')

    def getThing(self, id: str) -> Optional[ExposedThing]:
        return self.things.get(id)

    def get_things_descriptions(self) -> object:
        logger.debug(f'Servient getThings size == {len(self.things)}')
        ts: dict[str, object] = {}
        for id, thing in self.things.items():
            ts[id] = thing.get_description()
        return ts

    def addServer(self, server: ProtocolServer) -> bool:
        # add all exposed Things to new server
        self.servers.append(server)
        @self.app.on_event("startup")
        async def start_mqtt():
            await server.connect()

        @self.app.on_event("shutdown")
        async def stop_mqtt():
            await server.disconnect()

        self.mqtt = server

        return True

    def getServers(self) -> list[ProtocolServer]:
        # return a copy -- FIXME: not a deep copy
        return self.servers[0]

    def addClientFactory(self, clientFactory: ProtocolClientFactory) -> None:
        self.clientFactories[clientFactory.scheme] = clientFactory

    def hasClientFor(self, scheme: str) -> bool:
        logger.debug(f'Servient checking for {scheme} scheme in {self.clientFactories.size} ClientFactories')
        return scheme in self.clientFactories

    def getClientFor(self, scheme: str) -> ProtocolClient:
        if scheme in self.clientFactories:
            logger.debug(f'Servient creating client for scheme {scheme}')
            return self.clientFactories.get(scheme).getClient()
        else:
            # FIXME returning null was bad - Error or Promise?
            # h0ru5: caller cannot react gracefully - I'd throw Error
            raise Exception(f'Servient has no ClientFactory for scheme {scheme}')

    def getClientSchemes(self) -> list[str]:
        return list(self.clientFactories.keys())

    # will return WoT object
    def start(self) -> None:
        uvicorn.run(self.app, loop='none', host='localhost', port=8080)

    async def shutdown(self) -> None:
        for clientFactory in self.clientFactories.values():
            clientFactory.destroy()
        
        tasks = [asyncio.create_task(server.stop()) for server in self.servers]
        
        await asyncio.gather(**tasks)
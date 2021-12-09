from __future__ import annotations

import asyncio
import json

from uuid import uuid4
from typing import TYPE_CHECKING, Any, Optional
from loguru import logger 

from wot_impl import WoTImpl
import Helpers from "./helpers";

if TYPE_CHECKING:
    from .models.thing import ExposedThing 
    from .content_serdes import ContentCodec
    from protocol_interfaces import ProtocolClientFactory, ProtocolServer, ProtocolClient


class Servient:
    servers: list[ProtocolServer] = []
    clientFactories: dict[str, ProtocolClientFactory] = {}
    things: dict[str, ExposedThing] = {}

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
    
    def addThing(self, thing: ExposedThing) -> bool:

        if thing.id is None:
            thing.id = f"urn:uuid:{str(uuid4())}"
            logger.warning(f'Servient generating ID for {thing.title}: {thing.id}')

        if thing.id not in self.things:
            self.things[thing.id] = thing
            logger.debug(f'Servient reset ID {thing.id} with {thing.title}')
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
            logger.warning(f'Servient was asked to destroy thing but failed to find thing with id {thingId}');


    def getThing(self, id: str) -> ExposedThing:
        return self.things.get(id)

    # FIXME should be getThingDescriptions (breaking change)
    def getThings(self) -> object:
        logger.debug(f'Servient getThings size == {len(self.things)}')
        ts: dict[str, object] = {}
        for id, thing in self.things.items():
            ts[id] = thing.getThingDescription()
        return ts

    def addServer(self, server: ProtocolServer) -> bool:
        # add all exposed Things to new server
        for _, thing in self.things.items():
            server.expose(thing)

        self.servers.append(server)
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
    async def start(self) -> WoTImpl:
        serverStatus = []
        for server in self.servers:
            serverStatus.append(asyncio.create_task(server.start(self)))
        
        for clientFactory in self.clientFactories.values():
            clientFactory.init()

        await asyncio.gather(**serverStatus)
        
        return WoTImpl(self)


    async def shutdown(self) -> None:
        for clientFactory in self.clientFactories.values():
            clientFactory.destroy()
        
        tasks = [asyncio.create_task(server.stop()) for server in self.servers]
        
        await asyncio.gather(**tasks)
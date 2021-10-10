from __future__ import annotations

import asyncio
import json

from uuid import uuid4
from typing import TYPE_CHECKING, Any
import * as WoT from "wot-typescript-definitions"
from loguru import logger 

import WoTImpl from "./wot-impl";
import Helpers from "./helpers";

if TYPE_CHECKING:
    from .exposed_thing import ExposedThing 
    from .content_serdes import ContentCodec
    from protocol_interfaces import ProtocolClientFactory, ProtocolServer, ProtocolClient

from .content_serdes import default as ContentManager


class Servient:
    servers: list[ProtocolServer] = []
    clientFactories: dict[str, ProtocolClientFactory] = {}
    things: dict[str, ExposedThing] = {}
    credentialStore: dict[str, list[Any]] = {}

    __uncaughtListeners: list<(...args:any)=>void> = []

    # add a new codec to support a mediatype; offered mediatypes are listed in TDs
    def addMediaType(self, codec: ContentCodec, offered: bool = False) -> None:
        ContentManager.addCodec(codec, offered)

    def expose(self, thing: ExposedThing):

        if len(self.servers) == 0:
            logger.warning('Servient has no servers to expose Things')
            return

        logger.debug(f'Servient exposing {thing.title}')

        # What is a good way to to convey forms information like contentType et cetera for interactions
        tdTemplate: WoT.ThingDescription = json.loads(json.dumps(thing))

        # initializing forms fields
        thing.forms = []
        for name in thing.properties:
            thing.properties[name].forms = []
        for name in thing.actions:
            thing.actions[name].forms = []
        for name in thing.events:
            thing.events[name].forms = []

        serverTasks = []
        for server in self.servers:
            serverTasks.append(asyncio.create_task(server.expose(thing, tdTemplate)))
        
        asyncio.gather(*serverTasks)
    
    def addThing(self, thing: ExposedThing) -> bool:

        if 'id' not in self.things:
            thing.id = "urn:uuid:" + str(uuid4())
            logger.warning(f'Servient generating ID for {thing.title}: {thing.id}')

        if not self.things.get(thing.id):
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
        if id in self.things:
            return self.things.get(id)
        else:
            return None

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
            raise Error(f'Servient has no ClientFactory for scheme {scheme}')

    def getClientSchemes(self) -> list[str]:
        return list(self.clientFactories.keys())

    def addCredentials(self, credentials: Any):
        if (typeof credentials === "object"):
            for i in credentials:
                logger.debug(f'Servient storing credentials for {i}')
                currentCredentials: list[Any] = self.credentialStore.get(i)
                if not currentCredentials:
                    currentCredentials = []
                    self.credentialStore[i] = currentCredentials
                currentCredentials.append(credentials[i])

    '''**
     * @deprecated use retrieveCredentials() instead which may return multiple credentials
     * 
     * @param identifier id
     *'''
    def getCredentials(self, identifier: str) -> Any:
        logger.debug(f'Servient looking up credentials for {identifier} (@deprecated)')
        currentCredentials: list[Any] = self.credentialStore.get(identifier)
        if currentCredentials and len(currentCredentials) > 0:
            # return first
            return currentCredentials[0]
        else:
            return undefined

    def retrieveCredentials(self, identifier: str) -> list[Any]:
        logger.debug(f'Servient looking up credentials for {identifier}')
        return self.credentialStore.get(identifier)

    # will return WoT object
    def start(self):
        serverStatus = []
        for server in self.servers:
            serverStatus.append(server.start(self))
        
        for clientFactory in self.clientFactories.values():
            clientFactory.init()

        return new Promise<WoT.WoT>((resolve, reject) => {
            Promise.all(serverStatus)
                .then(() => {
                    resolve(new WoTImpl(this));
                })
                .catch(err => {
                    reject(err);
                });
        })


    def shutdown(self) -> None:
        for clientFactory in self.clientFactories.values():
            clientFactory.destroy()
        
        for server in self.servers:
            server.stop()

        for listener in self.__uncaughtListeners
            process.removeListener("uncaughtException",listener)


export interface ScriptOptions {
    argv?:Array<string>;
    compiler?: CompilerFunction;
    env?:Object;
}
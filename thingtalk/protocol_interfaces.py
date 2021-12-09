from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional, Protocol

import thingtalk.td_tools.thing_description as TD

import { Subscription } from "rxjs/Subscription";

if TYPE_CHECKING:
    from servient import Servient
    from exposed_thing import ExposedThing

class Content:
    type: str
    body: NodeJS.ReadableStream


class ProtocolClient(Protocol):
    # this client is requested to perform a "read" on the resource with the given URI
    async def readResource(form: TD.Form) -> Content:
        pass

    # this cliet is requested to perform a "write" on the resource with the given URI
    async def writeResource(form: TD.Form, content: Content) -> None:
        pass

    # this client is requested to perform an "invoke" on the resource with the given URI
    async def invokeResource(form: TD.Form, content: Content) -> Content:
        pass

    # this client is requested to perform an "unlink" on the resource with the given URI
    async def unlinkResource(form: TD.Form) -> None:
        pass

    async def subscribeResource(
        form: TD.Form,
        next: (content: Content) => void,
        error?: (error: any) => void,
        complete?: () => void
    ) -> Subscription:
        pass

    # start the client (ensure it is ready to send requests)
    def start() -> bool:
        pass
    # stop the client
    def stop() -> bool:
        pass

    # apply TD security metadata
    def setSecurity(metadata: list[TD.SecurityScheme], credentials: Optional[Any]) -> bool:
        pass


class ProtocolClientFactory(Protocol):
    scheme: str
    
    def getClient() -> ProtocolClient:
        pass
    
    def init() -> bool:
        pass
    
    def destroy() -> bool:
        pass


class ProtocolServer(Protocol):
    scheme: str
    
    async def expose(thing: ExposedThing, tdTemplate: Optional[WoT.ThingDescription]) -> None:
        pass
    '''**
     * @param thingId: id of the thing to destroy
     * @returns true if the thing was found and destroyed; false if the thing was not found
     * @throws if the binding couldn't destroy the thing
     **
     '''
    async def destroy(thingId: str):
        pass
    
    async def start(servient: Servient):
        pass
    
    async def stop():
        pass
    
    def getPort() -> int:
        pass
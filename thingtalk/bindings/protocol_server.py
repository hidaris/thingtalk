from abc import abstractmethod
from __future__ import annotations
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from servient import Servient
    from exposed_thing import ExposedThing


# A ProtocolServer defines how to expose Thing for interaction via a specific protocol (e.g. HTTP,
# MQTT, etc.).

class ProtocolServer(Protocol):
    scheme: str
    
    
    def start(servient: Servient):
        """ Starts the server (e.g. HTTP server) and makes it ready for requests to the exposed things.
    
        @param servient
        @return """
        pass
    
    def stop():
        '''
        stops the server (e.g. HTTP server) and ends the exposure of the Things
        @return
        '''
        pass

    
    def expose(thing: ExposedThing):
        '''
        Exposes <code>thing</code> and allows interaction with it.

        @param thing
        @return
        '''
        pass

    
    def destroy(thing: ExposedThing):
        '''
        Stops the exposure of <code>thing</code> and allows no further interaction with the thing.
    
        @param thing
        @return
        '''
        pass

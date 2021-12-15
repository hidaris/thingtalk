from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING, NoReturn, Optional, Union

from loguru import logger

# import * as WoT from "wot-typescript-definitions";

if TYPE_CHECKING:
    from .servient import Servient
from .models.thing import ExposedThing
# from .consumed_thing import ConsumedThing
# import Helpers from "./helpers";

class WoTImpl:
    srv: Servient
    # DiscoveryMethod: WoT.DiscoveryMethod
    
    def __init__(self, srv: Servient) -> None:
        self.srv = srv

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
                if self.srv.addThing(init):
                    return init
                else:
                    raise Exception("Thing already exists: " + init.title)
            newThing = ExposedThing(self.srv, init=init)
            logger.debug(f'WoTImpl producing new ExposedThing {newThing.title}')

            if self.srv.addThing(newThing):
                return newThing
            else:
                raise Exception("Thing already exists: " + newThing.title)
        except Exception as e:
            raise Exception("Cannot produce ExposedThing because " + str(e))


class DiscoveryMethod(str, Enum):
    # does not provide any restriction
    ANY = "any"
    # for discovering Things defined in the same device
    LOCAL = "local"
    # for discovery based on a service provided by a directory or repository of Things
    DIRECTORY = "directory"
    # for discovering Things in the device's network by using a supported multicast protocol
    MULTICAST = "multicast"


# class ThingDiscoveryImpl(WoT.ThingDiscovery):
#     filter: Optional[WoT.ThingFilter]
#     active: bool
#     done: bool
#     error: Optional[Exception]
    
#     def __init__(self, filter: Optional[WoT.ThingFilter]):
#         self.filter = filter
#         self.active = False
#         self.done = False
#         self.error = Exception("not implemented")

#     def start(self) -> None:
#         self.active = True

#     def next(self) -> NoReturn:
#         # not implemented
#         raise self.error

#     def stop(self) -> None:
#         self.active = False
#         self.done = False

# # Instantiation of the WoT.DataType declaration
# class DataType(str, Enum):
#     BOOLEAN = "boolean"
#     NUMBER = "number"
#     INTEGER = "integer"
#     STRING = "string"
#     OBJECT = "object"
#     ARRAY = "array"
#     NULL = "null"
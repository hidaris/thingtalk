from __future__ import annotations

from typing import TYPE_CHECKING, Optional
from loguru import logger

from .event import ThingPairedEvent, ThingRemovedEvent


if TYPE_CHECKING:
    from .thing import Thing


class SingleThing:
    """A container for a single thing."""

    def __init__(self, thing: Thing):
        """
        Initialize the container.
        thing -- the thing to store
        """
        self.thing = thing
        # mb.emit(
        #     "register",
        #     self.thing.id,
        #     self.thing.as_thing_description()
        #     )

    def get_thing(self, _=None):
        """Get the thing at the given index."""
        return self.thing

    def get_things(self):
        """Get the list of things."""
        return [self.thing]

    def get_name(self):
        """Get the mDNS server name."""
        return self.thing.title

    # def register(self):
    #     mb.emit("register", self.thing.id, self.thing.as_thing_description())


class MultipleThings:
    """A container for multiple things."""

    def __init__(self, things: dict, name: str):
        """
        Initialize the container.
        things -- the things to store
        name -- the mDNS server name
        """
        self.things = things
        self.name = name
        self.server = self.things.get('urn:thingtalk:server')

    def get_thing(self, idx) -> Optional[Thing]:
        """
        Get the thing at the given index.
        idx -- the index
        """
        return self.things.get(idx, None)

    def get_things(self):
        """Get the list of things."""
        return self.things.items()

    def get_name(self):
        """Get the mDNS server name."""
        return self.name

    async def discover(self, thing: Thing):
        self.things.update({thing.id: thing})
        await thing.subscribe_broadcast()

    async def add_thing(self, thing: Thing):
        logger.debug("add_thing")
        self.things.update({thing.id: thing})
        await thing.init_subscripe()
        await thing.subscribe_broadcast()

        # await self.server.add_event(ThingPairedEvent({
        #     '@type': list(thing._type),
        #     'id': thing.id,
        #     'title': thing.title
        # }))

    async def remove_thing(self, thing_id):
        # 来自 zigbee2mqtt 的 left_network 事件
        # 由于适配问题，thingtalk 中不一定存在对应的设备
        if self.things.get(thing_id):
            thing = self.things[thing_id]
            await thing.remove_listener()
            del self.things[thing_id]

            await self.server.add_event(ThingRemovedEvent({
                '@type': list(thing._type),
                'id': thing.id,
                'title': thing.title
            }))

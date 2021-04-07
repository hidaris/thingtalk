from loguru import logger

from .event import ThingPairedEvent, ThingRemovedEvent
from .thing import Thing
from ..toolkits.event_bus import mb


class SingleThing:
    """A container for a single thing."""

    def __init__(self, thing: Thing):
        """
        Initialize the container.
        thing -- the thing to store
        """
        self.thing = thing
        mb.emit(
            "register",
            self.thing.id,
            self.thing.as_thing_description()
            )

    def get_thing(self, _=None):
        """Get the thing at the given index."""
        return self.thing

    def get_things(self):
        """Get the list of things."""
        return [self.thing]

    def get_name(self):
        """Get the mDNS server name."""
        return self.thing.title

    def register(self):
        mb.emit("register", self.thing.id, self.thing.as_thing_description())


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

    def get_thing(self, idx):
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
        await thing.subscribe_broadcast()
        if self.name == "gateway":
            mb.emit("discover", thing.id, thing.as_thing_description())
        else:
            mb.emit("register", thing.id, thing.as_thing_description())
        things = [thing.as_thing_description() for _, thing in self.get_things()]
        """ await mqtt.publish(f"thingtalk/things", things) """

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

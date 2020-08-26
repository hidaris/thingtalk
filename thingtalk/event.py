"""High-level Event base class implementation."""
import typing

from .utils import timestamp
from .schema import BaseModel


class Event:
    """An Event represents an individual event from a thing."""

    title = None
    description = None

    def __init__(self, data=None):
        """
        Initialize the object.
        thing -- Thing this event belongs to
        name -- name of the event
        data -- data associated with the event
        """
        self.thing = None
        self.data = data
        self.time = timestamp()

    @classmethod
    def get_meta(cls):
        assert hasattr(cls, 'Schema'), (
            f"Class {cls.__name__} missing 'Schema' attribute"
        )
        schema = cls.Schema.schema()
        schema["description"] = cls.description
        return schema

    async def as_event_description(self):
        """
        Get the event description.
        Returns a dictionary describing the event.
        """
        description = {
            self.title: {"timestamp": self.time, },
        }

        if self.data is not None:
            description[self.title]["data"] = self.data

        return description

    async def get_thing(self):
        """Get the thing associated with this event."""
        return self.thing

    async def set_thing(self, thing):
        """Set the thing associated with this event."""
        self.thing = thing

    async def get_name(self):
        """Get the event's name."""
        return self.title

    async def get_data(self):
        """Get the event's data."""
        return self.data

    async def get_time(self):
        """Get the event's timestamp."""
        return self.time


class ThingPairingEvent(Event):
    title = "thing_pairing"
    description = "new thing pairing"

    class Schema(BaseModel):
        id: str


class ThingPairedEvent(Event):
    title = "thing_paired"
    description = "new thing paired"

    class Schema(BaseModel):
        id: str
        type: typing.List[str]
        title: str


class ThingRemovedEvent(Event):
    title = "thing_removed"
    description = "thing removed"

    class Schema(BaseModel):
        id: str

"""High-level Event base class implementation."""

from ..utils import timestamp


class Event:
    """An Event represents an individual event from a thing."""

    title = None
    schema = {}

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
    schema = {
        "description": "thing pairing event",
        "type": "object",
        "required": ["id", ],
        "properties": {
            "id": {
                "type": "string",
            },
        },
    }


class ThingPairFailedEvent(Event):
    title = "thing_pair_failed"
    schema = {
        "description": "thing pair failed event",
        "type": "object",
        "required": ["id", ],
        "properties": {
            "id": {
                "type": "string",
            },
        },
    }


class ThingPairedEvent(Event):
    title = "thing_paired"
    schema = {
        "description": "new thing paired",
        "type": "object",
        "required": ["@type", "id", "title"],
        "properties": {
            "@type": {
                "type": "array",
            },
            "id": {
                "type": "string",
            },
            "title": {
                "type": "string",
            },
        },
    }


class ThingRemovedEvent(Event):
    title = "thing_removed"
    schema = {
        "description": "device removed event",
        "type": "object",
        "required": ["id", ],
        "properties": {
            "id": {
                "type": "string",
            },
        },
    }

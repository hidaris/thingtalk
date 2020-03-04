"""High-level Event base class implementation."""
from dataclasses import dataclass
from typing import Optional, Dict, Any

from thing import Thing
from utils import timestamp


@dataclass
class Event:
    """An Event represents an individual event from a thing."""

    # Initialize the object.
    # thing -- Thing this event belongs to
    # name -- name of the event
    # data -- data associated with the event
    thing: Thing
    name: str
    data: Optional[Dict[str, Any]] = None
    time: str = timestamp()

    async def as_event_description(self) -> Dict[str, Any]:
        """
        Get the event description.
        Returns a dictionary describing the event.
        """
        description = {
            self.name: {
                'timestamp': self.time,
            },
        }

        if self.data is not None:
            description[self.name]['data'] = self.data

        return description

    async def get_thing(self) -> Thing:
        """Get the thing associated with this event."""
        return self.thing

    async def get_name(self) -> str:
        """Get the event's name."""
        return self.name

    async def get_data(self) -> Dict[str, Any]:
        """Get the event's data."""
        return self.data

    async def get_time(self):
        """Get the event's timestamp."""
        return self.time

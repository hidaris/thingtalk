class SingleThing:
    """A container for a single thing."""

    def __init__(self, thing):
        """
        Initialize the container.
        thing -- the thing to store
        """
        self.thing = thing

    async def get_thing(self, _=None):
        """Get the thing at the given index."""
        return self.thing

    async def get_things(self):
        """Get the list of things."""
        return [self.thing]

    async def get_name(self):
        """Get the mDNS server name."""
        return self.thing.title


class MultipleThings:
    """A container for multiple things."""

    def __init__(self, things, name):
        """
        Initialize the container.
        things -- the things to store
        name -- the mDNS server name
        """
        self.things = things
        self.name = name

    async def get_thing(self, idx):
        """
        Get the thing at the given index.
        idx -- the index
        """
        # try:
        #     idx = int(idx)
        # except ValueError:
        #     return None

        # if idx < 0 or idx >= len(self.things):
        #     return None

        return self.things.get(idx, None)

    async def get_things(self):
        """Get the list of things."""
        return self.things.items()

    async def get_name(self):
        """Get the mDNS server name."""
        return self.name

"""High-level Action base class implementation."""

from .utils import timestamp


class Action:
    """An Action represents an individual action on a thing."""

    def __init__(self, id_, thing, name, input_):
        """
        Initialize the object.
        id_ ID of this action
        thing -- the Thing this action belongs to
        name -- name of the action
        input_ -- any action inputs
        """
        self.id = id_
        self.thing = thing
        self.name = name
        self.input = input_
        self.href_prefix = ""
        self.href = f"/actions/{self.name}/{self.id}"
        self.status = "created"
        self.time_requested = timestamp()
        self.time_completed = None

    async def as_action_description(self):
        """
        Get the action description.
        Returns a dictionary describing the action.
        """
        description = {
            self.name: {
                "href": self.href_prefix + self.href,
                "timeRequested": self.time_requested,
                "status": self.status,
            },
        }

        if self.input is not None:
            description[self.name]["input"] = self.input

        if self.time_completed is not None:
            description[self.name]["timeCompleted"] = self.time_completed

        return description

    async def set_href_prefix(self, prefix):
        """
        Set the prefix of any hrefs associated with this action.
        prefix -- the prefix
        """
        self.href_prefix = prefix

    async def get_id(self):
        """Get this action's ID."""
        return self.id

    async def get_name(self):
        """Get this action's name."""
        return self.name

    async def get_href(self):
        """Get this action's href."""
        return self.href_prefix + self.href

    async def get_status(self):
        """Get this action's status."""
        return self.status

    async def get_thing(self):
        """Get the thing associated with this action."""
        return self.thing

    async def get_time_requested(self):
        """Get the time the action was requested."""
        return self.time_requested

    async def get_time_completed(self):
        """Get the time the action was completed."""
        return self.time_completed

    async def get_input(self):
        """Get the inputs for this action."""
        return self.input

    async def start(self):
        """Start performing the action."""
        self.status = "pending"
        await self.thing.action_notify(self)
        await self.perform_action()
        await self.finish()

    async def perform_action(self):
        """Override this with the code necessary to perform the action."""
        pass

    async def cancel(self):
        """Override this with the code necessary to cancel the action."""
        pass

    async def finish(self):
        """Finish performing the action."""
        self.status = "completed"
        self.time_completed = timestamp()
        await self.thing.action_notify(self)

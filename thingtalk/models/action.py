"""High-level Action base class implementation."""

from functools import cached_property
import typing
import uuid

from ..utils import timestamp


class Action:
    """An Action represents an individual action on a thing."""

    title: str = ""
    schema: dict = {}

    def __init__(self, thing, input_, id_=uuid.uuid4().hex):
        """
        Initialize the object.
        id_ ID of this action, default uuid
        thing -- the Thing this action belongs to
        name -- name of the action
        input_ -- any action inputs
        """
        self._id = id_
        self._thing = thing
        self._input = input_
        self._href_prefix: str = ""
        self._href: str = f"/actions/{self.title}/{self._id}"
        self._status: str = "created"
        self._time_requested: str = timestamp()
        self._time_completed: typing.Optional[str] = None
        self.meta = None

    @cached_property
    def description(self):
        """
        Get the action description.
        Returns a dictionary describing the action.
        """
        description = {
            self.title: {
                "href": self.href,
                "timeRequested": self.time_requested,
                "status": self.status,
            },
        }

        if self.input is not None:
            description[self.title]["input"] = self.input

        if self.time_completed is not None:
            description[self.title]["timeCompleted"] = self.time_completed

        return description

    def clean_description_cache(self):
        if self.__dict__.get("description"):
            del self.__dict__["description"]

    @property
    def href_prefix(self):
        return self._href_prefix

    @href_prefix.setter
    def href_prefix(self, prefix):
        """
        Set the prefix of any hrefs associated with this action.
        prefix -- the prefix
        """
        self.clean_description_cache()
        self._href_prefix = prefix

    @property
    def id(self):
        """Get this action's ID."""
        return self._id

    @id.setter
    def id(self, id):
        self.clean_description_cache()
        self._id = id

    @property
    def name(self):
        """Get this action's name."""
        return self.title

    @property
    def href(self):
        """Get this action's href."""
        return self._href_prefix + self._href

    @property
    def status(self):
        """Get this action's status."""
        return self._status

    @status.setter
    def status(self, status):
        self.clean_description_cache()
        self._status = status

    @property
    def thing(self):
        """Get the thing associated with this action."""
        return self._thing

    @property
    def time_requested(self):
        """Get the time the action was requested."""
        return self._time_requested

    @property
    def time_completed(self):
        """Get the time the action was completed."""
        return self._time_completed

    @time_completed.setter
    def time_completed(self, time: str):
        """update the time completed."""
        self.clean_description_cache()
        self._time_completed = time

    @property
    def input(self):
        """Get the inputs for this action."""
        return self._input

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

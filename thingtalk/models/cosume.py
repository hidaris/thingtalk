from typing import Any, Optional
import httpx

from loguru import logger

from .property import Property


class ConsumedThing:
    """A Web Thing."""

    def __init__(self, init: dict[str, Any]):
        """
        Initialize the object.
        id_ -- the thing's unique ID - must be a URI
        title -- the thing's title
        type_ -- the thing's type(s)
        owners_ -- the thing's owner(s)
        description -- description of the thing
        """
        self.td = init
        self._type = init.get("@type")

        if not self.description:
            self.description = init.get("description")

        self._id: Optional[str] = init.get("id")
        self._context: str = "https://webthings.io/schemas"
        self._title: Optional[str] = init.get("title")
        self.properties: dict[str, Property] = {}
        self.available_actions = {}
        self.available_events = {}
        self.actions = {}
        self.events = []
        self._href_prefix = ""
        self._ui_href = ""
        self.subscribe_topics = [f"things/{self._id}"]

    @property
    def thing_description(self):
        """
        Return the thing state as a Thing Description.
        Returns the state as a dictionary.
        """
        return self.td

    @property
    def href(self) -> str:
        """Get this thing's href."""
        # if self._href_prefix:
        #     return self._href_prefix

        # return "/"
        return self.td.get("href", '')

    @property
    def href_prefix(self) -> str:
        """Get this thing's href."""
        return self.href.split("/")[0]

    # @property
    # def ui_href(self) -> str:
    #     """Get the UI href."""
    #     return self._ui_href

    @property
    def id(self) -> str:
        """
        Get the ID of the thing.
        Returns the ID as a string.
        """
        return self.td.get("id", '')

    @property
    def title(self) -> str:
        """
        Get the title of the thing.
        Returns the title as a string.
        """
        return self.td.get("title", "")

    @property
    def context(self) -> str:
        """
        Get the type context of the thing.
        Returns the context as a string.
        """
        return self.td.get("@context", "")

    @property
    def type(self) -> list[str]:
        """
        Get the type(s) of the thing.
        Returns the list of types.
        """
        return self.td.get("@type", [])

    def get_property_descriptions(self):
        """
        Get the thing's properties as a dictionary.
        Returns the properties as a dictionary, i.e. name -> description.
        """
        # return {k: v.description for k, v in self.properties.items()}
        return self.td.get('properties', {})

    def get_action_descriptions(self, action_name=None):
        '''
        Get the thing's actions as a dictionary.
        Returns the actions as a dictionary, i.e. name -> description.
        '''
        return self.td.get('actions', {})

    def get_event_descriptions(self):
        """
        Get the thing's events as an dictionary.
        Returns the events as a dictionary, i.e. name -> description.
        """
        return self.td.get('events', {})

    def find_property(self, property_name):
        """
        Find a property by name.
        property_name -- the property to find
        Returns a Property object, if found, else None.
        """
        return self.properties.get(property_name, None)

    def get_property(self, property_name):
        """
        Get a property's value.
        property_name -- the property to get the value of
        Returns the properties value, if found, else None.
        """
        prop = self.find_property(property_name)
        if prop:
            return prop.value

        return None

    async def get_properties(self):
        """
        Get a mapping of all properties and their values.
        Returns a dictionary of property_name -> value.
        """
        return {prop.name: prop.value for prop in self.properties.values()}

    def has_property(self, property_name):
        """
        Determine whether or not this thing has a given property.
        property_name -- the property to look for
        Returns a boolean, indicating whether or not the thing has the
        property.
        """
        return property_name in self.properties

    async def set_property(self, property_name: str, value) -> Optional[httpx.Response]:
        """
        Set a property value.
        property_name -- name of the property to set
        value -- value to set
        """
        prop = self.find_property(property_name)
        if not prop:
            logger.error(f"{self._title} doesn't support {property_name}")
            return
        logger.info(f"set {self._title}'s property {property_name} to {value}")
        
        async with httpx.AsyncClient() as client:
            r = await client.put(f"{self.href}/properties/{property_name}", json={property_name: value})

        return r

    async def request_action(self, action_name: str, params: dict[str, Any]) -> Optional[httpx.Response]:
        """
        Request an action.
        action_name -- name of the action to request
        params -- parameters to pass to the action
        """
        action = self.find_action(action_name)
        if not action:
            logger.error(f"{self._title} doesn't support {action_name}")
            return
        logger.info(f"request {self._title}'s action {action_name}")
        
        async with httpx.AsyncClient() as client:
            r = await client.post(f"{self.href}/actions/{action_name}", json={action_name: {"input": params}})

        return r

    # async def sync_property(self, property_name: str, value):
    #     """
    #     Sync a property value from cloud or mqtt etc.
    #     property_name -- name of the property to set
    #     value -- value to set
    #     """
    #     prop = self.find_property(property_name)
    #     if not prop:
    #         logger.warning(f"{self._title} doesn't support {property_name}")
    #         return
    #     logger.info(f"sync {self._title} {self.id}'s property {property_name} to {value}")
    #     try:
    #         prop.value = value
    #         await self.property_notify({property_name: value})
    #     except PropertyError as e:
    #         await self.error_notify(str(e))

    # async def bulk_sync_property(self, data: dict):
    #     """
    #     Bulk yync property value from cloud or mqtt etc.
    #     property_name -- name of the property to set
    #     value -- value to set
    #     """
    #     logger.info(f"id {self.id}")
    #     for property_name, value in tuple(data.items()):
    #         prop = self.find_property(property_name)
    #         if not prop:
    #             logger.warning(f"{self._title} doesn't support {property_name}")
    #             del data[property_name]
    #             continue
    #         logger.info(f"sync {self._title}'s property {property_name} to {value}")
    #         try:
    #             prop.value = value
    #         except PropertyError as e:
    #             del data[property_name]
    #             await self.error_notify(str(e))
    #     await self.property_notify(data)

    def get_action(self, action_name, action_id):
        """
        Get an action.
        action_name -- name of the action
        action_id -- ID of the action
        Returns the requested action if found, else None.
        """
        if action_name not in self.actions:
            return None

        for action in self.actions[action_name]:
            if action.id == action_id:
                return action

        return None

    async def add_event(self, event: Event):
        """
        Add a new event and notify subscribers.
        event -- the event that occurred
        """
        self.events.append(event)
        event.thing = self
        await self.event_notify(event)

    def add_available_event(self, cls, metadata=None):
        """
        Add an available event.
        name -- name of the event
        metadata -- event metadata, i.e. type, description, etc., as a dict
        """
        if metadata is None:
            metadata = cls.schema

        self.available_events[cls.title] = {
            "metadata": metadata,
            "subscribers": {},
        }

    def add_available_events(self, evts):
        """
        Add list of available event.
        evts -- list of the event
        """
        for evt in evts:
            self.add_available_event(evt)

    async def remove_action(self, action_name, action_id):
        """
        Remove an existing action.
        action_name -- name of the action
        action_id -- ID of the action
        Returns a boolean indicating the presence of the action.
        """
        action = self.get_action(action_name, action_id)
        if action is None:
            return False

        await action.cancel()
        self.actions[action_name].remove(action)
        return True

    def add_available_action(self, cls, metadata=None):
        """
        Add an available action.
        name -- name of the action, default use cls.name
        metadata -- action metadata, i.e. type, description, etc., as a dict
        cls -- class to instantiate for this action
        """
        if metadata is None:
            metadata = cls.schema

        name = cls.title
        self.available_actions[name] = {
            "metadata": metadata,
            "class": cls,
        }
        self.actions[name] = []

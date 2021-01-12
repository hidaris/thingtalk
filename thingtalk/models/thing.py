"""High-level Thing base class implementation."""

import asyncio
from typing import Dict

from jsonschema import validate
from jsonschema.exceptions import ValidationError

from loguru import logger

from .event import (
    Event,
    ThingPairingEvent,
    ThingPairedEvent,
    ThingRemovedEvent,
    ThingPairFailedEvent,
)
from .value import Value
from .property import Property
from .action import Action
from .errors import PropertyError

from ..toolkits.event_bus import ee
from ..schema import InputMsg, OutMsg


async def perform_action(action):
    """Perform an Action in a coroutine."""
    await action.start()


class Thing:
    """A Web Thing."""

    type = []
    description = ""

    def __init__(self, id_, title, type_=[], description_=""):
        """
        Initialize the object.
        id_ -- the thing's unique ID - must be a URI
        title -- the thing's title
        type_ -- the thing's type(s)
        owners_ -- the thing's owner(s)
        description -- description of the thing
        """
        self._type = set()
        if not isinstance(type_, list):
            self._type.add(type_)
        else:
            self._type = self._type.union(set(type_))

        self._type = self._type.union(set(self.type))

        if not self.description:
            self.description = description_

        self._id = id_
        self._context = "https://iot.mozilla.org/schemas"
        self._title = title
        self.properties: Dict[str, Property] = {}
        self.available_actions = {}
        self.available_events = {}
        self.actions = {}
        self.events = []
        self.owners = []
        self._href_prefix = ""
        self._ui_href = ""
        self.subscribe_topics = [f"things/{self._id}"]
        ee.on(f"things/{self._id}", self.dispatch)

    async def subscribe_broadcast(self):
        pass

    async def remove_listener(self):
        for topic in self.subscribe_topics:
            logger.info(f"remove topic {topic}'s listener dispatch")
            ee.remove_listener(topic, self.dispatch)

    async def dispatch(self, message: InputMsg):
        logger.debug(f"dispatch {message}")
        msg_type = message.messageType

        if msg_type == "setProperty":
            for property_name, property_value in message.data.items():
                await self.set_property(property_name, property_value)

        elif msg_type == "syncProperty":
            for property_name, property_value in message.data.items():
                await self.sync_property(property_name, property_value)

        elif msg_type == "requestAction":
            for action_name, action_params in message.data.items():
                input_ = None
                if "input" in action_params:
                    input_ = action_params["input"]

                action = await self.perform_action(action_name, input_)
                if action:
                    asyncio.create_task(perform_action(action))
                else:
                    await self.error_notify("Invalid action request", message)

        else:
            await self.error_notify(f"Unknown messageType: {msg_type}", message)

    def as_thing_description(self):
        """
        Return the thing state as a Thing Description.
        Returns the state as a dictionary.
        """

        thing = {
            "id": self.id,
            "title": self.title,
            "@context": self.context,
            "properties": self.get_property_descriptions(),
            "actions": {},
            "events": {},
            "links": [
                {
                    "rel": "properties",
                    "href": f"{self.href_prefix}/properties",
                },
                {
                    "rel": "actions",
                    "href": f"{self.href_prefix}/actions",
                },
                {
                    "rel": "events",
                    "href": f"{self.href_prefix}/events",
                },
            ],
        }

        for name, action in self.available_actions.items():
            thing["actions"][name] = action["metadata"]
            thing["actions"][name]["links"] = [
                {
                    "rel": "action",
                    "href": f"{self.href_prefix}/actions/{name}",
                },
            ]

        for name, event in self.available_events.items():
            thing["events"][name] = event["metadata"]

            thing["events"][name]["links"] = [
                {
                    "rel": "event",
                    "href": f"{self.href_prefix}/events/{name}",
                },
            ]

        if self.ui_href:
            thing["links"].append(
                {
                    "rel": "alternate",
                    "mediaType": "text/html",
                    "href": self.ui_href,
                }
            )

        if self.description:
            thing["description"] = self.description

        if self._type:
            thing["@type"] = list(self._type)

        return thing

    @property
    def href(self) -> str:
        """Get this thing's href."""
        if self._href_prefix:
            return self._href_prefix

        return "/"

    @property
    def href_prefix(self) -> str:
        """Get this thing's href."""
        return self._href_prefix

    @href_prefix.setter
    def href_prefix(self, prefix: str):
        """
        Set the prefix of any hrefs associated with this thing.
        prefix -- the prefix
        """
        self._href_prefix = prefix

        for property_ in self.properties.values():
            property_.href_prefix = prefix

        for action_name in self.actions.keys():
            for action in self.actions[action_name]:
                action.href_prefix = prefix

    @property
    def ui_href(self) -> str:
        """Get the UI href."""
        return self._ui_href

    @ui_href.setter
    def ui_href(self, href):
        """
        Set the href of this thing's custom UI.
        href -- the href
        """
        self._ui_href = href

    @property
    def id(self):
        """
        Get the ID of the thing.
        Returns the ID as a string.
        """
        return self._id

    @property
    def title(self):
        """
        Get the title of the thing.
        Returns the title as a string.
        """
        return self._title

    @title.setter
    def title(self, title):
        """
        Set the new title of this thing.
        title -- the new title
        """
        self._title = title

    @property
    def context(self):
        """
        Get the type context of the thing.
        Returns the context as a string.
        """
        return self._context

    def get_type(self):
        """
        Get the type(s) of the thing.
        Returns the list of types.
        """
        return self.type

    def get_description(self):
        """
        Get the description of the thing.
        Returns the description as a string.
        """
        return self.description

    def get_property_descriptions(self):
        """
        Get the thing's properties as a dictionary.
        Returns the properties as a dictionary, i.e. name -> description.
        """
        return {k: v.description for k, v in self.properties.items()}

    def get_action_descriptions(self, action_name=None):
        """
        Get the thing's actions as an array.
        action_name -- Optional action name to get descriptions for
        Returns the action descriptions.
        """
        descriptions = []

        if action_name is None:
            for name in self.actions:
                for action in self.actions[name]:
                    descriptions.append(action.description)
        elif action_name in self.actions:
            for action in self.actions[action_name]:
                descriptions.append(action.description)

        return descriptions

    def get_event_descriptions(self, event_name=None):
        """
        Get the thing's events as an array.
        event_name -- Optional event name to get descriptions for
        Returns the event descriptions.
        """
        if event_name is None:
            return [e.description for e in self.events]
        else:
            return [e.description for e in self.events if e.name == event_name]

    def add_property(self, property_: Property):
        """
        Add a property to this thing.
        property_ -- property to add
        """
        property_.href_prefix = self._href_prefix
        property_.thing = self
        self.properties[property_.name] = property_

    def remove_property(self, property_: Property):
        """
        Remove a property from this thing.
        property_ -- property to remove
        """
        if property_.name in self.properties:
            del self.properties[property_.name]

    def find_property(self, property_name):
        """
        Find a property by name.
        property_name -- the property to find
        Returns a Property object, if found, else None.
        """
        return self.properties.get(property_name, None)

    async def get_property(self, property_name):
        """
        Get a property's value.
        property_name -- the property to get the value of
        Returns the properties value, if found, else None.
        """
        prop = self.find_property(property_name)
        if prop:
            return await prop.get_value()

        return None

    async def get_properties(self):
        """
        Get a mapping of all properties and their values.
        Returns a dictionary of property_name -> value.
        """
        return {prop.name: await prop.get_value() for prop in self.properties.values()}

    def has_property(self, property_name):
        """
        Determine whether or not this thing has a given property.
        property_name -- the property to look for
        Returns a boolean, indicating whether or not the thing has the
        property.
        """
        return property_name in self.properties

    async def set_property(self, property_name: str, value):
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
        try:
            await prop.set_value(value)
            await self.property_notify({property_name: value})
            await self.property_action(prop)
        except PropertyError as e:
            await self.error_notify(str(e))

    async def sync_property(self, property_name: str, value):
        """
        Sync a property value from cloud or mqtt etc.
        property_name -- name of the property to set
        value -- value to set
        """
        prop = self.find_property(property_name)
        if not prop:
            logger.warning(f"{self._title} doesn't support {property_name}")
            return
        logger.info(f"sync {self._title}'s property {property_name} to {value}")
        try:
            await prop.set_value(value, with_action=False)
            await self.property_notify({property_name: value})
        except PropertyError as e:
            await self.error_notify(str(e))

    async def bulk_sync_property(self, data: dict):
        """
        Bulk yync property value from cloud or mqtt etc.
        property_name -- name of the property to set
        value -- value to set
        """
        for property_name, value in tuple(data.items()):
            prop = self.find_property(property_name)
            if not prop:
                logger.warning(f"{self._title} doesn't support {property_name}")
                del data[property_name]
                continue
            logger.info(f"sync {self._title}'s property {property_name} to {value}")
            try:
                await prop.set_value(value, with_action=False)
            except PropertyError as e:
                del data[property_name]
                await self.error_notify(str(e))
        await self.property_notify(data)

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

    async def perform_action(self, action_name, input_=None):
        """
        Perform an action on the thing.
        action_name -- name of the action
        input_ -- any action inputs
        Returns the action that was created.
        """
        if action_name not in self.available_actions:
            return None

        action_type = self.available_actions[action_name]

        if "input" in action_type["metadata"]:
            try:
                validate(input_, action_type["metadata"]["input"])
            except ValidationError as e:
                logger.error(str(e))
                return None

        action = action_type["class"](self, input_=input_)
        action.href_prefix = self.href_prefix
        await self.action_notify(action)
        self.actions[action_name].append(action)
        return action

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

    async def property_notify(self, data: dict):
        """
        Notify all subscribers of a property change.
        property_ -- the property that changed
        """
        message = {
            "topic": f"things/{self.id}",
            "messageType": "propertyStatus",
            "data": data,
        }
        try:
            message = OutMsg(**message)
            ee.emit(f"things/{self.id}/state", message)
        except ValidationError as e:
            logger.error(str(e))

    async def error_notify(self, error_, request=None):
        """
        Notify all subscribers of a error.
        error_ -- the error that reported
        """
        message = {
            "topic": f"things/{self.id}",
            "messageType": "error",
            "data": {
                "status": "400 Bad Request",
                "message": str(error_),
            },
        }
        if request:
            message.update({"request": request})

        try:
            message = OutMsg(**message)
            ee.emit(f"things/{self.id}/error", message)
        except ValidationError as e:
            logger.error(str(e))

    async def property_action(self, property_):
        """
        Addional action when a property change.
        property_ -- the property that changed
        """
        pass

    async def action_notify(self, action: Action):
        """
        Notify all subscribers of an action status change.
        action -- the action whose status changed
        """
        message = {
            "topic": f"things/{self.id}",
            "messageType": "actionStatus",
            "data": action.description,
        }
        try:
            message = OutMsg(**message)
            ee.emit(f"things/{self.id}/state", message)
        except ValidationError as e:
            logger.error(str(e))

    async def event_notify(self, event):
        """
        Notify all subscribers of an event.
        event -- the event that occurred
        """

        if event.title not in self.available_events:
            return

        message = {
            "topic": f"things/{self.id}",
            "messageType": "event",
            "data": event.description,
        }
        try:
            message = OutMsg(**message)
            ee.emit(f"things/{self.id}/event", message)
        except ValidationError as e:
            logger.error(str(e))

    def add_owner(self, owner: str):
        """
        Add a new owner.
        owner -- the owner
        """
        self.owners.append(owner)

    def get_owners(self):
        """Get this thing's owner(s)."""
        return self.owners


class Server(Thing):
    type = ["Server"]
    description = "Web Thing Environment"

    def __init__(self):
        super().__init__(
            "urn:thingtalk:server",
            "Web Thing Environment",
        )

        self.add_property(
            Property(
                "state",
                Value("ON"),
                metadata={
                    "@type": "ServerStateProperty",
                    "title": "State",
                    "display_name": "state",
                    "type": "string",
                    "enum": ["ON", "OFF", "REBOOT"],
                    "description": "state of thingtalk server",
                },
            )
        )

        self.add_available_events(
            [
                ThingPairingEvent,
                ThingPairedEvent,
                ThingRemovedEvent,
                ThingPairFailedEvent,
            ]
        )

"""High-level Property base class implementation."""

from copy import deepcopy
from jsonschema import validate
from jsonschema.exceptions import ValidationError
from loguru import logger

from .errors import PropertyError


class Property:
    """A Property represents an individual state value of a thing."""

    __slots__ = ['thing', 'name', 'value', 'metadata', 'href_prefix', 'href', 'media_type']

    def __init__(self, name, value, thing=None, metadata=None):
        """
        Initialize the object.
        thing -- the Thing this property belongs to
        name -- name of the property
        value -- Value object to hold the property value
        metadata -- property metadata, i.e. type, description, unit, etc.,
                    as a dict
        """
        self.thing = thing
        self.name = name
        self.value = value
        self.metadata = metadata if metadata is not None else {}
        self.href_prefix = ""
        self.href = f"/properties/{self.name}"
        self.media_type = "application/json"

        # Add the property change observer to notify the Thing about a property
        # change.
        # self.value.on("update", lambda value_: self.thing.property_notify(self, value_))
        # self.value.on("sync", lambda value_: self.thing.property_notify(self, value_))
        # self.value.on("update", lambda _: self.thing.property_action(self))

    async def validate_value(self, value):
        """
        Validate new property value before setting it.
        value -- New value
        """
        if "readOnly" in self.metadata and self.metadata["readOnly"]:
            logger.error("Read-only property")
            raise PropertyError("Read-only property")

        try:
            validate(value, self.metadata)
        except ValidationError:
            logger.error(f"Invalid property value {value}")
            raise PropertyError(f"Invalid property value {value}")

    async def as_property_description(self):
        """
        Get the property description.
        Returns a dictionary describing the property.
        """
        description = deepcopy(self.metadata)

        if "links" not in description:
            description["links"] = []

        if description["@type"] in ["VideoProperty", "ImageProperty"]:
            description["links"].append(
                {"rel": "property", "href": self.href, "mediaType": self.media_type}
            )
        else:
            description["links"].append(
                {"rel": "property", "href": self.href_prefix + self.href, "mediaType": self.media_type}
            )
        return description

    def set_href_prefix(self, prefix):
        """
        Set the prefix of any hrefs associated with this property.
        prefix -- the prefix
        """
        self.href_prefix = prefix

    def set_href(self, href):
        """
        Set the href associated with this property.
        href -- the new prefix
        """
        self.href = href

    def set_media_type(self, media_type):
        """
        Set the media type associated with this property.
        media_type -- the new media type
        """
        self.media_type = media_type

    def get_href(self):
        """
        Get the href of this property.
        Returns the href.
        """
        return self.href_prefix + self.href

    async def get_value(self):
        """
        Get the current property value.
        Returns the value.
        """
        return await self.value.get()

    async def set_value(self, value, with_action=True):
        """
        Set the current value of the property.
        value -- the value to set
        """
        await self.validate_value(value)
        await self.value.set(value, with_action=with_action)

    async def get_name(self):
        """
        Get the name of this property.
        Returns the name.
        """
        return self.name

    def set_thing(self, thing):
        """Set the thing associated with this property."""
        self.thing = thing

    def get_thing(self):
        """Get the thing associated with this property."""
        return self.thing

    async def get_metadata(self):
        """Get the metadata associated with this property."""
        return self.metadata

    def __repr__(self):
        return f"(Property {self.name})"

"""High-level Property base class implementation."""

from copy import deepcopy
from functools import cached_property
from jsonschema import validate
from jsonschema.exceptions import ValidationError
from loguru import logger

from .errors import PropertyError


class Property:
    """A Property represents an individual state value of a thing."""

    __slots__ = [
        "_thing",
        "_name",
        "value",
        "_metadata",
        "_href_prefix",
        "_href",
        "_media_type",
        "__dict__",
    ]

    def __init__(self, name, value, thing=None, metadata=None):
        """
        Initialize the object.
        thing -- the Thing this property belongs to
        name -- name of the property
        value -- Value object to hold the property value
        metadata -- property metadata, i.e. type, description, unit, etc.,
                    as a dict
        """
        self._thing = thing
        self._name = name
        self.value = value
        self._metadata = metadata if metadata is not None else {}
        self._href_prefix = ""
        self._href = f"/properties/{self._name}"
        self._media_type = "application/json"

    def validate_value(self, value):
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

    @cached_property
    def description(self):
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
                {
                    "rel": "property",
                    "href": self.href,
                    "mediaType": self.media_type,
                }
            )
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
        Set the prefix of any hrefs associated with this property.
        prefix -- the prefix
        """
        self.clean_description_cache()
        self._href_prefix = prefix

    @property
    def href(self):
        """
        Get the href of this property.
        Returns the href.
        """
        return self._href_prefix + self._href

    @href.setter
    def href(self, href):
        """
        Set the href associated with this property.
        href -- the new prefix
        """
        self.clean_description_cache()
        self._href = href

    @property
    def media_type(self):
        return self._media_type

    @media_type.setter
    def media_type(self, media_type):
        """
        Set the media type associated with this property.
        media_type -- the new media type
        """
        self.clean_description_cache()
        self._media_type = media_type

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
        self.validate_value(value)
        await self.value.set(value, with_action=with_action)

    @property
    def name(self):
        """
        Get the name of this property.
        Returns the name.
        """
        return self._name

    @property
    def thing(self):
        """Get the thing associated with this property."""
        return self._thing

    @thing.setter
    def thing(self, thing):
        """Set the thing associated with this property."""
        self._thing = thing

    @property
    def metadata(self):
        """Get the metadata associated with this property."""
        return self._metadata

    def __repr__(self):
        return f"(Property {self._name})"

from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field


class ThingDescription(BaseModel):
    context: str = Field(alias="@context", default="https://webthings.io/schemas")
    type: list[str] = Field(alias="@type", default=["Thing"])
    id: Optional[str] = None
    title: str
    description: str
    properties: dict[str, PropertyDescription] = {}
    actions: dict[str, ActionDescription] = {}
    events: dict[str, EventDescription] = {}


class PropertyDescription(BaseModel):
    schema_type: str = Field(alias="@type", default="Property")
    type: str
    title: str
    description: str
    links: dict[str, str] = {}

class ActionDescription(BaseModel):
    schema_type: str = Field(alias="@type", default="Action")
    title: str
    description: str
    input: dict[str, DataSchema] = {}
    links: dict[str, str] = {}

class EventDescription(BaseModel):
    schema_type: str = Field(alias="@type", default="Event")
    type: str
    title: str
    description: str
    links: dict[str, str] = {}
#!/usr/bin/env python3

import uuid
import time
import httpx

from thing import Thing
from property import Property
from value import Value
from action import Action
from event import Event


class OverheatedEvent(Event):
    def __init__(self, thing, data):
        Event.__init__(self, thing, "overheated", data=data)


class SwitchAction(Action):
    def __init__(self, thing, input_):
        Action.__init__(self, uuid.uuid4().hex, thing, "switch", input_=input_)

    async def perform_action(self):
        time.sleep(self.input["duration"] / 1000)
        await self.thing.set_property("brightness", self.input["brightness"])
        await self.thing.add_event(OverheatedEvent(self.thing, 102))


class TuyaSwitch(Thing):
    def __init__(self, id_, title):
        Thing.__init__(
            self, id_, title, ["OnOffSwitch",], "A web connected tuya switch",
        )

    async def add_on_property(self, name, friendly_name):
        await self.add_property(
            Property(
                self,
                name,
                Value(True),
                metadata={
                    "@type": "OnOffProperty",
                    "title": friendly_name,
                    "type": "boolean",
                    "description": "Whether the switch is turned on",
                },
            )
        )

    async def build(self):
        await self.add_property(
            Property(
                self,
                "on",
                Value(True),
                metadata={
                    "@type": "OnOffProperty",
                    "title": "On/Off",
                    "type": "boolean",
                    "description": "Whether the switch is turned on",
                },
            )
        )

        await self.add_available_action(
            "fade",
            {
                "title": "Fade",
                "description": "Fade the lamp to a given level",
                "input": {
                    "type": "object",
                    "required": ["brightness", "duration",],
                    "properties": {
                        "brightness": {
                            "type": "integer",
                            "minimum": 0,
                            "maximum": 100,
                            "unit": "percent",
                        },
                        "duration": {
                            "type": "integer",
                            "minimum": 1,
                            "unit": "milliseconds",
                        },
                    },
                },
            },
            SwitchAction,
        )

        await self.add_available_event(
            "overheated",
            {
                "description": "The lamp has exceeded its safe operating temperature",
                "type": "number",
                "unit": "degree celsius",
            },
        )

        return self


class TuyaLight(Thing):
    def __init__(self, id_, title):
        Thing.__init__(
            self, id_, title, ["OnOffSwitch", "Light"], "A web connected tuya Light",
        )

    async def add_on_property(self, name, friendly_name):
        await self.add_property(
            Property(
                self,
                name,
                Value(True),
                metadata={
                    "@type": "OnOffProperty",
                    "title": friendly_name,
                    "type": "boolean",
                    "description": "Whether the switch is turned on",
                },
            )
        )

    async def add_brightness_property(self):
        await self.add_property(
            Property(
                self,
                "brightness",
                Value(50),
                metadata={
                    "@type": "BrightnessProperty",
                    "title": "Brightness",
                    "type": "integer",
                    "description": "The level of light from 25-255",
                    "minimum": 25,
                    "maximum": 255,
                    "unit": "percent",
                },
            )
        )

    async def add_color_temp_property(self):
        await self.add_property(
            Property(
                self,
                "color_temp",
                Value(50),
                metadata={
                    "@type": "ColorTempProperty",
                    "title": "color_temp",
                    "type": "integer",
                    "description": "The level of light from 0-255",
                    "minimum": 0,
                    "maximum": 255,
                    "unit": "percent",
                },
            )
        )

    async def add_hs_color_property(self):
        await self.add_property(
            Property(
                self,
                "hs_color",
                Value(50),
                metadata={
                    "@type": "HsColorProperty",
                    "title": "color_temp",
                    "type": "integer",
                    "description": "The level of light from 0-255",
                    "minimum": 0,
                    "maximum": 255,
                    "unit": "percent",
                },
            )
        )


class TuyaVacuum(Thing):
    def __init__(self, id_, title):
        Thing.__init__(
            self, id_, title, ["OnOffSwitch", "Vaccum"], "A web connected tuya Vaccum",
        )

    async def add_on_property(self, name, friendly_name):
        await self.add_property(
            Property(
                self,
                name,
                Value(True),
                metadata={
                    "@type": "OnOffProperty",
                    "title": friendly_name,
                    "type": "boolean",
                    "description": "Whether the switch is turned on",
                },
            )
        )

    async def add_brightness_property(self):
        await self.add_property(
            Property(
                self,
                "brightness",
                Value(50),
                metadata={
                    "@type": "BrightnessProperty",
                    "title": "Brightness",
                    "type": "integer",
                    "description": "The level of light from 25-255",
                    "minimum": 25,
                    "maximum": 255,
                    "unit": "percent",
                },
            )
        )

    async def add_color_temp_property(self):
        await self.add_property(
            Property(
                self,
                "color_temp",
                Value(50),
                metadata={
                    "@type": "ColorTempProperty",
                    "title": "color_temp",
                    "type": "integer",
                    "description": "The level of light from 0-255",
                    "minimum": 0,
                    "maximum": 255,
                    "unit": "percent",
                },
            )
        )

    async def add_hs_color_property(self):
        await self.add_property(
            Property(
                self,
                "hs_color",
                Value(50),
                metadata={
                    "@type": "HsColorProperty",
                    "title": "color_temp",
                    "type": "integer",
                    "description": "The level of light from 0-255",
                    "minimum": 0,
                    "maximum": 255,
                    "unit": "percent",
                },
            )
        )

from starlette.middleware import Middleware

from webthing import background_thread_loop, Value, Thing, Property, Event, Action, WebThingServer
from starlette.middleware.cors import CORSMiddleware

# import logging
import time


class OverheatedEvent(Event):
    def __init__(self, thing, data):
        Event.__init__(self, thing, "overheated", data=data)


class FadeAction(Action):
    name = "fade"

    async def perform_action(self):
        time.sleep(self.input["duration"] / 1000)
        await self.thing.set_property("brightness", self.input["brightness"])
        await self.thing.add_event(OverheatedEvent(self.thing, 102))


class Light(Thing):
    type = ["OnOffSwitch"],
    description = "A web connected lamp",

    def __init__(self):
        super().__init__(
            "urn:dev:ops:my-lamp-1234",
            "My Lamp",
        )

    async def build(self):
        await self.add_property(
            Property(
                "on",
                Value(True),
                metadata={
                    "@type": "OnOffProperty",
                    "title": "On/Off",
                    "type": "boolean",
                    "description": "Whether the lamp is turned on",
                },
            )
        )

        await self.add_property(
            Property(
                "brightness",
                Value(50),
                metadata={
                    "@type": "BrightnessProperty",
                    "title": "Brightness",
                    "type": "integer",
                    "description": "The level of light from 0-100",
                    "minimum": 0,
                    "maximum": 100,
                    "unit": "percent",
                },
            )
        )

        await self.add_available_action(
            {
                "title": "Fade",
                "description": "Fade the lamp to a given level",
                "input": {
                    "type": "object",
                    "required": ["brightness", "duration", ],
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
            FadeAction,
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


with background_thread_loop() as loop:
    app = WebThingServer(loop, Light, additional_middlewares=[Middleware(CORSMiddleware, allow_origins=['*'])]).create()
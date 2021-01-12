from starlette.middleware import Middleware

from thingtalk import background_thread_loop, Value, Thing, Property, Event, Action, ThingTalk
from starlette.middleware.cors import CORSMiddleware

# import logging
import time
import httpx


class OverheatedEvent(Event):
    def __init__(self, thing, data):
        Event.__init__(self, thing, "overheated", data=data)


class Request(Action):
    title = "request"

    async def perform_action(self):
        time.sleep(self._input["duration"] / 1000)
        await self._thing.set_property("brightness", self._input["brightness"])
        await self._thing.add_event(OverheatedEvent(self._thing, 102))


class HTTPRequester(Thing):
    type = ["HTTPRequester"],
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

        await self.add_available_action(
            {
                "title": "Request",
                "description": "Request Action",
                "input": {
                    "type": "object",
                    "required": ["url", "method", "headers", ],
                    "properties": {
                        "brightness": {
                            "type": "integer",
                            "minimum": 0,
                            "maximum": 100,
                            "unit": "percent",
                        },
                        "url": {
                            "type": "string",
                        },
                        "method": {
                            "type": "string",
                        }
                    },
                },
            },
            Request,
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
    app = ThingTalk(loop, Light,
                    additional_middlewares=[Middleware(CORSMiddleware, allow_origins=['*'])]).create()

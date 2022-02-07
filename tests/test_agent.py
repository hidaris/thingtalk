from loguru import logger

from thingtalk.agent import Agent
import time

from thingtalk import ExposedThing, Property, Event, Action


class OverheatedEvent(Event):
    title = "overheated"
    schema = {
        "description": "The lamp has exceeded its safe operating temperature",
        "type": "number",
        "unit": "degree celsius",
    }


class Fade(Action):
    title: str = "fade"
    schema: dict = {
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
    }

    async def perform_action(self):
        time.sleep(self.input["duration"] / 1000)
        await self.thing.set_property("brightness", self.input["brightness"])
        await self.thing.add_event(OverheatedEvent(102))


class Light(ExposedThing):
    type = ["OnOffSwitch", "Light"]
    description = "A web connected lamp"

    def __init__(self):
        super().__init__(
            {"id": "urn:dev:ops:my-lamp-1234",
            "title": "My Lamp",
            "@type": ["OnOffSwitch", "Light"]}
        )
        self.href_prefix = f"/things/{self.id}"

        self.add_property(
            Property(
                "on",
                value=True,
                metadata={
                    "@type": "OnOffProperty",
                    "title": "On/Off",
                    "type": "boolean",
                    "description": "Whether the lamp is turned on",
                },
            )
        )

        self.add_property(
            Property(
                "brightness",
                value=50,
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

        self.add_available_action(
            Fade
        )

        self.add_available_event(
            OverheatedEvent
        )
# from example.test_light import Light

agent = Agent()

""" thing = agent.produce(
    {
        "@context": "https://www.w3.org/2019/wot/td/v1",
        "@type": "Thing",
        "title": "MyCounter",
        "properties": {
            "count": {
                type: "integer",
            },
        },
    }
) """
agent.produce(Light())

# thing.writeProperty("count", 0)
# await thing.expose()
# c = thing.readProperty("count")

agent.start()
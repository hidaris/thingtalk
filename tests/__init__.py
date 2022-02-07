# import time

# from fastapi import APIRouter

# from ..thingtalk import ExposedThing, Property, Event, Action
# from ..thingtalk.app import ThingTalk
# from ..thingtalk.routers import things, websockets, properties, events, actions


# class OverheatedEvent(Event):
#     title = "overheated"
#     schema = {
#         "description": "The lamp has exceeded its safe operating temperature",
#         "type": "number",
#         "unit": "degree celsius",
#     }


# class Fade(Action):
#     title: str = "fade"
#     schema: dict = {
#         "title": "Fade",
#         "description": "Fade the lamp to a given level",
#         "input": {
#             "type": "object",
#             "required": ["brightness", "duration", ],
#             "properties": {
#                 "brightness": {
#                     "type": "integer",
#                     "minimum": 0,
#                     "maximum": 100,
#                     "unit": "percent",
#                 },
#                 "duration": {
#                     "type": "integer",
#                     "minimum": 1,
#                     "unit": "milliseconds",
#                 },
#             },
#         },
#     }

#     async def perform_action(self):
#         time.sleep(self.input["duration"] / 1000)
#         await self.thing.set_property("brightness", self.input["brightness"])
#         await self.thing.add_event(OverheatedEvent(data=102))


# class Light(ExposedThing):
#     type = ["OnOffSwitch", "Light"]
#     description = "A web connected lamp"

#     def __init__(self):
#         super().__init__(
#             "urn:dev:ops:my-lamp-1234",
#             "My Lamp",
#         )
#         self.href_prefix = f"/things/{self.id}"

#         self.add_property(
#             Property(
#                 "on",
#                 value=True,
#                 metadata={
#                     "@type": "OnOffProperty",
#                     "title": "On/Off",
#                     "type": "boolean",
#                     "description": "Whether the lamp is turned on",
#                 },
#             )
#         )

#         self.add_property(
#             Property(
#                 "brightness",
#                 value=50,
#                 metadata={
#                     "@type": "BrightnessProperty",
#                     "title": "Brightness",
#                     "type": "integer",
#                     "description": "The level of light from 0-100",
#                     "minimum": 0,
#                     "maximum": 100,
#                     "unit": "percent",
#                 },
#             )
#         )

#         self.add_available_action(
#             Fade
#         )

#         self.add_available_event(
#             OverheatedEvent
#         )


# light = Light()

# # mqtt = ThingMqtt("127.0.0.1", "1883")

# app = ThingTalk(
#     title="Zigbee adapter",
#     version="0.1.0",
#     description="Zigbee 🐝 to WoT bridge 🌉, get rid of your proprietary Zigbee bridges",
#     mode="single",
#     thing=light
# )

# restapi = APIRouter()

# restapi.include_router(things.router, tags=["thing"])
# restapi.include_router(
#     properties.router,
#     prefix="/things/{thing_id}",
#     tags=["property"],
#     responses={404: {"description": "Not found"}},
# )
# restapi.include_router(
#     actions.router,
#     prefix="/things/{thing_id}",
#     tags=["action"],
#     responses={404: {"description": "Not found"}},
# )
# restapi.include_router(
#     events.router,
#     prefix="/things/{thing_id}",
#     tags=["event"],
#     responses={404: {"description": "Not found"}},
# )

# app.include_router(restapi)
# app.include_router(websockets.router)

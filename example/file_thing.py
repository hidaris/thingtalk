#!/usr/bin/env python3

import uuid
import time

from starlette.concurrency import run_in_threadpool

from thing import Thing
from property import Property
from value import Value
from action import Action
from event import Event
from containers import SingleThing, MultipleThings
import aiofiles

# class OverheatedEvent(Event):
#     def __init__(self, thing, data):
#         Event.__init__(self, thing, "overheated", data=data)


class ReadAction(Action):
    def __init__(self, thing, input_):
        Action.__init__(self, uuid.uuid4().hex, thing, "read", input_=input_)

    async def perform_action(self):
        # time.sleep(self.input["duration"] / 1000)
        async with aiofiles.open(self.input["filename"], "r") as f:
            content = await f.read()
        import os

        fsize = os.path.getsize(self.input["filename"])
        await self.thing.set_property("size", fsize)
        await self.thing.set_property("content", content)
        # await self.thing.add_event(OverheatedEvent(self.thing, 102))


class FileThing(Thing):
    def __init__(self):
        Thing.__init__(
            self,
            "urn:dev:ops:my-lamp-1234",
            "File thing",
            ["OnOffSwitch", "Light"],
            "A web connected file system",
        )

    async def build(self):
        await self.add_property(
            Property(
                self,
                "size",
                Value(0),
                metadata={
                    "@type": "SizeProperty",
                    "title": "FileSize",
                    "type": "integer",
                    "description": "文件大小",
                },
            )
        )

        await self.add_property(
            Property(
                self,
                "size2",
                Value(0),
                metadata={
                    "@type": "SizeProperty",
                    "title": "FileSize",
                    "type": "integer",
                    "description": "文件大小",
                },
            )
        )

        await self.add_property(
            Property(
                self,
                "content",
                Value(""),
                metadata={
                    "@type": "ContentProperty",
                    "title": "Content",
                    "type": "string",
                    "description": "文件内容",
                },
            )
        )

        await self.add_available_action(
            "read",
            {
                "title": "Read",
                "description": "读取文件内容",
                "input": {
                    "type": "object",
                    "required": ["filename",],
                    "properties": {"filename": {"type": "string",}},
                },
            },
            ReadAction,
        )

        await self.add_available_event(
            "overheated",
            {
                "description": "The lamp has exceeded its safe operating temperature",
                "type": "number",
                "unit": "degree celsius",
            },
        )

        # return MultipleThings([self], "File things")
        return MultipleThings({self.id: self}, "File things")

import uuid
import time

from webthing import (
    Thing,
    Property,
    Value,
    Action,
    Event,
    SingleThing,
    MultipleThings,
    WebThingServer,
    background_thread_loop,
)

import aiofiles


class ReadAction(Action):

    name = "read"

    async def perform_action(self):
        async with aiofiles.open(self.input["filename"], "r") as f:
            content = await f.read()
        import os

        fsize = os.path.getsize(self.input["filename"])
        await self.thing.set_property("size", fsize)
        await self.thing.set_property("content", content)
        # await self.thing.add_event(OverheatedEvent(self.thing, 102))


class FileThing(Thing):

    type = ["OnOffSwitch", ]
    description = "A web connected file system"

    def __init__(self):
        super().__init__(
            "urn:dev:ops:my-lamp-1234",
            "File thing"
        )

    async def build(self):
        await self.add_property(
            Property(
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

        return self


with background_thread_loop() as loop:
    app = WebThingServer(loop, FileThing).create()

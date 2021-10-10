from __future__ import annotations

from typing import Protocol, TypedDict

from loguru import logger
from .protocol_interfaces import Content
import JsonCodec from "./codecs/json-codec";
import TextCodec from "./codecs/text-codec";
import Base64Codec from "./codecs/base64-codec";
import OctetstreamCodec from "./codecs/octetstream-codec";
from .td import DataSchema, DataSchemaValue
import { Readable } from "stream";
import { ProtocolHelpers } from "./core";
import { ReadableStream } from "web-streams-polyfill/ponyfill/es2018";

# is a plugin for ContentSerdes for a specific format (such as JSON or EXI)
class ContentCodec(Protocol):
    def getMediaType() -> str:
        pass
    
    def bytesToValue(bytes: Buffer, schema: DataSchema, parameters: dict[str, str]) -> DataSchemaValue:
        pass
    
    def valueToBytes(value: unknown, schema: DataSchema, parameters: dict[str, str]) -> Buffer:
        pass


class ReadContent(TypedDict):
    type: str
    body: Buffer

'''**
 * is a singleton that is used to serialize and deserialize data
 * it can accept multiple serializers and decoders
 *'''
class ContentSerdes:
    instance: ContentSerdes

    DEFAULT: str = "application/json"
    TD: str = "application/td+json"
    JSON_LD: str = "application/ld+json"

    codecs: dict[str, ContentCodec] = {}
    offered: set[str] = set()

    @staticmethod
    def get() -> ContentSerdes:
        if not ContentSerdes.instance:
            ContentSerdes.instance = ContentSerdes()
            # JSON
            ContentSerdes.instance.addCodec(JsonCodec(), True)
            ContentSerdes.instance.addCodec(JsonCodec("application/senml+json"))
            # Text
            ContentSerdes.instance.addCodec(TextCodec())
            ContentSerdes.instance.addCodec(TextCodec("text/html"))
            ContentSerdes.instance.addCodec(TextCodec("text/css"))
            ContentSerdes.instance.addCodec(TextCodec("application/xml"))
            ContentSerdes.instance.addCodec(TextCodec("application/xhtml+xml"))
            ContentSerdes.instance.addCodec(TextCodec("image/svg+xml"))
            # Base64
            ContentSerdes.instance.addCodec(Base64Codec("image/png"))
            ContentSerdes.instance.addCodec(Base64Codec("image/gif"))
            ContentSerdes.instance.addCodec(Base64Codec("image/jpeg"))
            # OctetStream
            ContentSerdes.instance.addCodec(OctetstreamCodec())
        
        return ContentSerdes.instance

    @staticmethod
    def getMediaType(contentType: str) -> str:
        parts = contentType.split(";")
        return parts[0].strip()

    @staticmethod
    def getMediaTypeParameters(contentType: str) -> dict[str, str]:
        parts = contentType.split(";")[1]

        # parse parameters into object
        params: dict[str, str] = {}
        for p in parts:
            eq = p.indexOf("=")

            if eq >= 0:
                params[p.substr(0, eq).trim()] = p.substr(eq + 1).trim();
            else:
                # handle parameters without value
                params[p.trim()] = None

        return params

    def addCodec(codec: ContentCodec, offered = False) -> None:
        ContentSerdes.get().codecs[codec.getMediaType()] = codec
        if offered:
            ContentSerdes.get().offered.add(codec.getMediaType())


    def getSupportedMediaTypes() -> list[str]:
        return list(ContentSerdes.get().codecs.keys())

    def getOfferedMediaTypes() -> list[str]:
        return list(ContentSerdes.get().offered)

    def isSupported(self, contentType: str) -> bool:
        mt = ContentSerdes.getMediaType(contentType)
        return mt in self.codecs

    def contentToValue(self, content: ReadContent, schema: DataSchema) -> DataSchemaValue:
        if content.type == undefined:
            if content.body.byteLength > 0:
                # default to application/json
                content.type = ContentSerdes.DEFAULT
            else:
                # empty payload without media type -> void/undefined (note: e.g., empty payload with text/plain -> "")
                return

        # split into media type and parameters
        mt = ContentSerdes.getMediaType(content.type)
        par = ContentSerdes.getMediaTypeParameters(content.type)

        # choose codec based on mediaType
        if mt in self.codecs:
            logger.debug(f'ContentSerdes deserializing from {content.type}')

            codec = self.codecs.get(mt)

            # use codec to deserialize
            res = codec.bytesToValue(content.body, schema, par)

            return res
        else:
            logger.warning(f'ContentSerdes passthrough due to unsupported media type {mt}')
            return str(content.body)

    def valueToContent(
        self,
        value: DataSchemaValue | ReadableStream,
        schema: DataSchema,
        contentType = ContentSerdes.DEFAULT
    ) -> Content:
        if value == undefined:
            logger.warning("ContentSerdes valueToContent got no value")

        if isinstance(value, ReadableStream):
            return { type: contentType, body: ProtocolHelpers.toNodeStream(value) }

        bytes = None

        # split into media type and parameters
        mt = ContentSerdes.getMediaType(contentType)
        par = ContentSerdes.getMediaTypeParameters(contentType)

        # choose codec based on mediaType
        if mt in self.codecs:
            logger.debug(f'ContentSerdes serializing to {contentType}')
            codec = self.codecs.get(mt)
            bytes = codec.valueToBytes(value, schema, par)
        else:
            logger.warning(
                f'ContentSerdes passthrough due to unsupported serialization format {contentType}'
            )
            bytes = Buffer.from(value.toString())
        # http server does not like Readable.from(bytes)
        # it works only with Arrays or strings
        return { type: contentType, body: Readable.from([bytes]) }


# export singleton instance
default = ContentSerdes.get()
from __future__ import annotations

from typing import Any, Literal, TypedDict, Union

# import * as WoT from "wot-typescript-definitions";

DEFAULT_CONTEXT = "https://www.w3.org/2019/wot/td/v1"
DEFAULT_CONTEXT_LANGUAGE = "en"
DEFAULT_THING_TYPE = "Thing"

""" TODOs / Questions
 ~ In Thing index structure could be read-only (sanitizing needs write access)
"""

MultiLanguage = dict[str, str]

# Implements the Thing Description as software object
class Thing:
    id: str
    title: str
    titles: MultiLanguage
    description: str
    descriptions: MultiLanguage
    support: str
    created: str
    modified: str
    version: VersionInfo
    securityDefinitions: dict[str, SecurityType]

    security: list[str]
    base: str

    properties: dict[str, ThingProperty]

    actions: dict[str, ThingAction]

    events: dict[str, ThingEvent]

    links: list[Link]
    forms: list[Form]

    # [key: string]: any

    def __init__(self) -> None:
        self.context = DEFAULT_CONTEXT
        self.type = DEFAULT_THING_TYPE
        self.security = []
        self.properties = {}
        self.actions = {}
        self.events = {}
        self.links = []


# Basis from implementing the Thing Interaction descriptions for Property, Action, and Event
class ThingInteraction:
    title: str
    titles: MultiLanguage
    description: str
    descriptions: MultiLanguage
    scopes: list[str]
    uriVariables: dict[str, DataSchema]
    security: list[str]
    forms: list[Form]

    # [key: string]: any


# Carries version information about the TD instance. If required, additional version information such as firmware and hardware version (term definitions outside of the TD namespace) can be extended here.
class VersionInfo(TypedDict):
    instance: str


class Link(TypedDict):
    href: str
    rel: str | list[str]
    type: str  # media type hint, no media type parameters
    anchor: str


class ExpectedResponse(TypedDict):
    contentType: str


# Implements the Interaction Form description
class Form:
    op: str | list[str]
    href: str
    subprotocol: str
    contentType: str  # media type + parameter(s), e.g., text/plain;charset=utf8
    security: list[
        str
    ]  # Set of security definition names, chosen from those defined in securityDefinitions  // Security;
    scopes: list[str]
    response: ExpectedResponse

    def __init__(self, href: str, contentType: str):
        self.href = href
        if contentType:
            self.contentType = contentType


number = Union[int, float]


class BaseSchema:
    type: str
    title: str
    titles: MultiLanguage
    description: str
    descriptions: MultiLanguage
    writeOnly: bool
    readOnly: bool
    oneOf: list[DataSchema]
    unit: str
    const: Any
    enum: list[Any]


class BooleanSchema(BaseSchema):
    type: Literal["boolean"]


class IntegerSchema(BaseSchema):
    type: Literal["integer"]
    minimum: int
    maximum: int


class NumberSchema(BaseSchema):
    type: Literal["number"]
    minimum: number
    maximum: number


class StringSchema(BaseSchema):
    type: Literal["string"]


class ObjectSchema(BaseSchema):
    type: Literal["object"]
    properties: dict[str, DataSchema]
    required: list[str]


class ArraySchema(BaseSchema):
    type: Literal["array"]
    items: DataSchema
    minItems: number
    maxItems: number


class NullSchema(BaseSchema):
    type: Literal["null"]


DataSchema = Union[
    BooleanSchema,
    IntegerSchema,
    NumberSchema,
    StringSchema,
    ObjectSchema,
    ArraySchema,
    NullSchema,
]


class SecurityScheme(TypedDict):
    scheme: str
    description: str
    proxy: str


class NoSecurityScheme(SecurityScheme):
    scheme: Literal["nosec"]


class BasicSecurityScheme(SecurityScheme):
    scheme: Literal["basic"]
    _in: str
    name: str


class DigestSecurityScheme(SecurityScheme):
    scheme: Literal["digest"]
    name: str
    _in: str
    qop: str


class APIKeySecurityScheme(SecurityScheme):
    scheme: Literal["apikey"]
    _in: str
    name: str


class BearerSecurityScheme(SecurityScheme):
    scheme: Literal["bearer"]
    _in: str
    alg: str
    format: str
    name: str
    authorization: str


class CertSecurityScheme(SecurityScheme):
    scheme: Literal["cert"]
    identity: str


class PSKSecurityScheme(SecurityScheme):
    scheme: Literal["psk"]
    identity: str


class PublicSecurityScheme(SecurityScheme):
    scheme: Literal["public"]
    identity: str


class PoPSecurityScheme(SecurityScheme):
    scheme: Literal["pop"]
    format: str
    authorization: str
    alg: str
    name: str
    _in: str


class OAuth2SecurityScheme(SecurityScheme):
    scheme: Literal["oauth2"]
    authorization: str
    flow: str  # one of implicit, password, client, or code
    token: str
    refresh: str
    scopes: list[str]


SecurityType = Union[
    NoSecurityScheme,
    BasicSecurityScheme,
    DigestSecurityScheme,
    BearerSecurityScheme,
    CertSecurityScheme,
    PoPSecurityScheme,
    APIKeySecurityScheme,
    OAuth2SecurityScheme,
    PSKSecurityScheme,
    PublicSecurityScheme,
]

# Implements the Thing Property description
class ThingProperty(BaseSchema, ThingInteraction):
    # writable: boolean;
    observable: bool
    type: str

    # ThingInteraction
    forms: list[Form]
    title: str
    titles: MultiLanguage
    description: str
    descriptions: MultiLanguage
    scopes: list[str]
    uriVariables: dict[str, DataSchema]

    security: list[str]

    # [key: string]: any;


# Implements the Thing Action description
class ThingAction(ThingInteraction):
    input: DataSchema
    output: DataSchema
    safe: bool
    idempotent: bool

    # ThingInteraction
    forms: list[Form]
    title: str
    titles: MultiLanguage
    description: str
    descriptions: MultiLanguage
    scopes: list[str]
    uriVariables: dict[str, DataSchema]
    security: list[str]


# Implements the Thing Event description
class ThingEvent(ThingInteraction):
    subscription: DataSchema
    data: DataSchema
    cancellation: DataSchema

    # ThingInteraction
    forms: list[Form]
    title: str
    titles: MultiLanguage
    description: str
    descriptions: MultiLanguage
    scopes: list[str]
    uriVariables: dict[str, DataSchema]
    security: list[str]

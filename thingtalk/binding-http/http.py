from __future__ import annotations
from typing import Literal, Optional, TypedDict, Union

import * as TD from "@node-wot/td-tools";
import { Method } from "./oauth-token-validation";

export { default as HttpServer } from "./http-server";
export { default as HttpClient } from "./http-client";
export { default as HttpClientFactory } from "./http-client-factory";
export { default as HttpsClientFactory } from "./https-client-factory";
export * from "./http-server";
export * from "./http-client";
export * from "./http-client-factory";
export * from "./https-client-factory";

class HttpConfig(TypedDict):
    port: int
    address: str
    baseUri: str
    proxy: HttpProxyConfig
    allowSelfSigned: bool
    serverKey: str
    serverCert: str
    security: TD.SecurityScheme


class OAuth2ServerConfig(TD.SecurityScheme):
    method: Method
    # Regex to select the valid clients ids. Default: .*
    allowedClients: str


class HttpProxyConfig:
    href: str
    scheme: Literal["basic", "bearer"]
    token: str
    username: str
    password: str


class HttpForm(TD.Form):
    "htv:methodName": Optional[HTTPMethodName]
    "htv:headers": Optional[Union[list[HttpHeader], HttpHeader]]


HTTPMethodName = "GET" | "PUT" | "POST" | "DELETE" | "PATCH" | "HEAD"

class HttpHeader:
    public "htv:fieldName": str
    public "htv:fieldValue": str

from __future__ import annotations

from typing import Literal, TYPE_CHECKING

from loguru import logger

if TYPE_CHECKING:
    from .http import HttpConfig
    from thingtalk.exposed_thing import ExposedThing
    from thingtalk.servient import Servient


class HttpServer:
    scheme: Literal["http", "https"]

    PROPERTY_DIR: str = "properties"
    ACTION_DIR: str = "actions"
    EVENT_DIR: str = "events"

    OBSERVABLE_DIR: str = "observable"

    # OPTIONS_URI_VARIABLES ='uriVariables'
    # OPTIONS_BODY_VARIABLES ='body'

    port: int = 8080
    address: str
    baseUri: str
    httpSecurityScheme: str = "NoSec" # HTTP header compatible string
    validOAuthClients: RegExp = /.*/g;
    server: http.Server | https.Server = None
    things: dict[str, ExposedThing] = {}
    servient: Servient
    oAuthValidator: Validator;

    def __init__(self, config: HttpConfig):
        if not isinstance(config, HttpConfig):
            raise TypeError(f'HttpServer requires config object (got {type(config)})')

        if config.port:
            self.port = config.port

        environmentObj = ["WOT_PORT", "PORT"]
            .map((envVar) => {
                return { key: envVar, value: process.env[envVar] };
            })
            .find((envObj) => envObj.value != null);

        if environmentObj:
            logger.info(
                f'HttpServer Port Overridden to {environmentObj.value} by Environment Variable {environmentObj.key}'
            )
            self.port = +environmentObj.value;

        if config.address:
            self.address = config.address

        if config.baseUri:
            self.baseUri = config.baseUri

        # TLS
        if config.serverKey and config.serverCert:
            options = {}
            options.key = fs.readFileSync(config.serverKey);
            options.cert = fs.readFileSync(config.serverCert);
            self.scheme = "https"
            self.server = https.createServer(options, (req, res) => {
                this.handleRequest(req, res);
            })
        else:
            self.scheme = "http"
            self.server = http.createServer((req, res) => {
                this.handleRequest(req, res);
            })

    def start(self, servient: Servient):
        logger.info(
            f'HttpServer starting on {self.address}port {self.port}'
        )
        # store servient to get credentials
        self.servient = servient

        # long timeout for long polling
        self.server.setTimeout(60 * 60 * 1000, () => {
            console.debug("[binding-http]", `HttpServer on port ${this.getPort()} timed out connection`);
        })
        # no keep-alive because NodeJS HTTP clients do not properly use same socket due to pooling
        self.server.keepAliveTimeout = 0

        # start promise handles all errors until successful start

    def stop(self):
        logger.info(f'HttpServer stopping on port {self.getPort()}')
        return new Promise<void>((resolve, reject) => {
            // stop promise handles all errors from now on
            this.server.once("error", (err: Error) => {
                reject(err);
            });
            this.server.once("close", () => {
                resolve();
            });
            this.server.close();
        });
    }

    # returns http.Server to be re-used by other HTTP-based bindings (e.g., WebSockets)
    def getServer(self) -> http.Server | https.Server:
        return self.server


    # returns server port number and indicates that server is running when larger than -1
    def getPort(self) -> int:
        if self.server.address() and typeof self.server.address() === "object":
            return (<AddressInfo>this.server.address()).port
        else:
            # includes address() typeof "string" case, which is only for unix sockets
            return -1

    def getHttpSecurityScheme(self) -> str:
        return self.httpSecurityScheme

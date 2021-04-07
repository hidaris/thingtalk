import socket

from fastapi import FastAPI, APIRouter
from loguru import logger
from zeroconf import Zeroconf, ServiceInfo

from .routers.mqtt import mqtt
from .utils import get_ip
from .models.thing import Server
from .models.containers import MultipleThings
from .routers import things, properties, actions, events, websockets
from .toolkits import mb

app = FastAPI(
    title="ThingTalk",
    version="0.7.12",
    description="Web of Things framework, high performance, easy to learn, fast to code, ready for production",
)
server = Server()
server.href_prefix = f"/things/{server.id}"
# app.state.things = MultipleThings({server.id: server}, "things")
app.state.things = MultipleThings({}, "gateway")

zeroconf = Zeroconf()


@app.on_event("startup")
async def start_mdns():
    """Start listening for incoming connections."""
    name = app.state.things.get_name()
    args = [
        "_webthing._tcp.local.",
        f"{name}._webthing._tcp.local.",
    ]
    kwargs = {
        "port": 8000,
        "properties": {
            "path": "/",
        },
        "server": f"{socket.gethostname()}.local.",
        "addresses": [socket.inet_aton(get_ip())],
    }
    app.state.service_info = ServiceInfo(*args, **kwargs)
    zeroconf.register_service(app.state.service_info)


@app.on_event("shutdown")
async def stop_mdns():
    """Stop listening."""
    zeroconf.unregister_service(app.state.service_info)
    zeroconf.close()


# @app.on_event("startup")
# async def startup():
#     await mqtt.set_app(app)
#     await mqtt.connect()
    # await app.state.things.add_thing(server)


# @app.on_event("shutdown")
# async def shutdown():
#     await mqtt.disconnect()
#     mb.remove_all_listeners()


restapi = APIRouter()

restapi.include_router(things.router, tags=["thing"])
restapi.include_router(
    properties.router,
    prefix="/things/{thing_id}",
    tags=["property"],
    responses={404: {"description": "Not found"}},
)
restapi.include_router(
    actions.router,
    prefix="/things/{thing_id}",
    tags=["action"],
    responses={404: {"description": "Not found"}},
)
restapi.include_router(
    events.router,
    prefix="/things/{thing_id}",
    tags=["event"],
    responses={404: {"description": "Not found"}},
)

app.include_router(restapi)
app.include_router(websockets.router)

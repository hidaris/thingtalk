import socket

from fastapi import FastAPI, APIRouter

from loguru import logger
from zeroconf.asyncio import AsyncZeroconf, AsyncServiceInfo

from .models.thing import Server
from .models.containers import MultipleThings
from .routers import things, properties, actions, events, websockets
from .utils import get_ip

app = FastAPI(
    title="ThingTalk",
    version="0.7.12",
    description="Web of Things framework, high performance, easy to learn, fast to code, ready for production",
)
server = Server()
server.href_prefix = f"/things/{server._id}"
app.state.things = MultipleThings({server._id: server}, "things")

zeroconf = AsyncZeroconf()


@app.on_event("startup")
async def start_mdns():
    """Start listening for incoming connections."""
    name = await app.state.things.get_name()
    args = [
        '_webthing._tcp.local.',
        f"{name}._webthing._tcp.local.",
    ]
    kwargs = {
        'port': '8000',  # port,
        'properties': {
            'path': '/',
        },
        'server': f"{socket.gethostname()}.local.",
        'addresses': [socket.inet_aton(get_ip())]
    }
    app.state.service_info = AsyncServiceInfo(*args, **kwargs)
    print(app.state.service_info)
    await zeroconf.async_register_service(app.state.service_info)


@app.on_event("shutdown")
async def stop_mdns():
    """Stop listening."""
    await zeroconf.async_unregister_service(app.state.service_info)
    await zeroconf.async_close()

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

import socket
import click

from fastapi import FastAPI, APIRouter
from loguru import logger
from zeroconf import Zeroconf, ServiceInfo
from functools import partial

from config import settings
from .routers.mqtt import ThingMqtt
from .utils import get_ip
from .models.thing import Server
from .models.containers import MultipleThings
from .routers import things, properties, actions, events, websockets
from .toolkits import ee
from .schema import OutMsg


app = FastAPI(
    title="ThingTalk",
    version="0.7.12",
    description="Web of Things framework, high performance, easy to learn, fast to code, ready for production",
)
server = Server()
server.href_prefix = f"/things/{server.id}"
app.state.things = MultipleThings({server.id: server}, "things")

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


username = settings.MQTT_USERNAME
password = settings.MQTT_PASSWORD
host = settings.MQTT_HOST

mqtt = ThingMqtt(host, "1883", username=username, password=password)


@app.on_event("startup")
async def startup():
    await mqtt.connect()
    await mqtt.publish("thingtalk/test", "online")


@app.on_event("shutdown")
async def shutdown():
    await mqtt.disconnect()


async def publish(topic: str, payload: OutMsg):
    await mqtt.publish(f"thingtalk/{topic}", payload.dict())


for key, _ in app.state.things.get_things():
    ee.on(f"things/{key}/state", partial(publish, f"things/{key}/state"))
    ee.on(f"things/{key}/error", partial(publish, f"things/{key}/error"))
    ee.on(f"things/{key}/event", partial(publish, f"things/{key}/event"))


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


@click.command()
@click.option("--count", default=1, e=int, help="Number of greetings.")
@click.option("--name", type=str, prompt="Your name", help="The person to greet.")
def hello(count: int, name: str):
    """Simple program that greets NAME for a total of COUNT times."""
    for _ in range(count):
        click.echo(f"Hello, {name}!")

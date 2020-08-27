import socket

from zeroconf import ServiceInfo, Zeroconf

from fastapi import FastAPI, APIRouter


from loguru import logger

from .thing import Server
# from .auth import requires
from .utils import get_ip
from .containers import MultipleThings
from .routers import things, properties, actions, events, websockets

logger.info("initial thingtalk instance")

app = FastAPI(
    title="ThingTalk",
    version="0.2.0",
    description="Web of Things framework, high performance, easy to learn, fast to code, ready for production"
)
server = Server()
app.state.things = MultipleThings({server.id: server}, "things")

# @app.on_event("startup")
# async def init_zmq():
#     bus = MessageBus(app)
#     app.state.bus = bus
#     asyncio.create_task(bus.receive())
#     bus.subscriber.subscribe("things/urn:thingtalk:server")
#
#
# @app.on_event("shutdown")
# async def close_zmq():
#     bus = app.state.bus
#     await bus.clean_up()

# zeroconf = Zeroconf()
#
#
# @app.on_event("startup")
# async def start_mdns():
#     """Start listening for incoming connections."""
#     name = await app.state.things.get_name()
#     args = [
#         '_webthing._tcp.local.',
#         f"{name}._webthing._tcp.local.",
#     ]
#     kwargs = {
#         'port': '8000',  # port,
#         'properties': {
#             'path': '/',
#         },
#         'server': f"{socket.gethostname()}.local.",
#         'addresses': [socket.inet_aton(get_ip())]
#     }
#     app.state.service_info = ServiceInfo(*args, **kwargs)
#     print(app.state.service_info)
#     zeroconf.register_service(app.state.service_info)
#
#
# @app.on_event("shutdown")
# async def stop_mdns():
#     """Stop listening."""
#     zeroconf.unregister_service(app.state.service_info)
#     zeroconf.close()

thing_router = APIRouter()

thing_router.include_router(things.router, tags=["thing"])
thing_router.include_router(websockets.router)
thing_router.include_router(
    properties.router,
    prefix="/things/{thing_id}",
    tags=["property"],
    responses={404: {"description": "Not found"}},
)
thing_router.include_router(
    actions.router,
    prefix="/things/{thing_id}",
    tags=["action"],
    responses={404: {"description": "Not found"}},
)
thing_router.include_router(
    events.router,
    prefix="/things/{thing_id}",
    tags=["event"],
    responses={404: {"description": "Not found"}},
)

# class WsThingHandler(WebSocketEndpoint):
#     """Handle a request to /."""
#
#     encoding = "json"
#
#     async def dispatch(self) -> None:
#         websocket = WebSocket(self.scope, receive=self.receive, send=self.send)
#         try:
#             await self.on_connect(websocket)
#         except WebSocketDisconnect:
#             return
#
#         close_code = status.WS_1000_NORMAL_CLOSURE
#
#         try:
#             while True:
#                 message = await websocket.receive()
#                 if message["type"] == "websocket.receive":
#                     data = await self.decode(websocket, message)
#                     await self.on_receive(websocket, data)
#                 elif message["type"] == "websocket.disconnect":
#                     close_code = int(message.get("code", status.WS_1000_NORMAL_CLOSURE))
#                     break
#         except Exception as exc:
#             close_code = status.WS_1011_INTERNAL_ERROR
#             raise exc from None
#         finally:
#             await self.on_disconnect(websocket, close_code)
#

#             try:
#                 await websocket.send_json(description, mode="binary")
#             except (WebSocketDisconnect, ConnectionClosedOK):
#                 pass
#
#

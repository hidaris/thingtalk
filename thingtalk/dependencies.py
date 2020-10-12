from fastapi.exceptions import HTTPException
from fastapi import Request, Depends, WebSocket
from loguru import logger


async def get_thing(request: Request, thing_id: str):
    """
    Get the thing this request is for.
    request -- current request
    thing_id -- ID of the thing to get, in string form
    Returns the thing, or None if not found.
    """
    things = request.app.state.things
    thing = await things.get_thing(thing_id)
    if thing is None:
        raise HTTPException(status_code=404)
    return thing


# async def on_connect(websocket: WebSocket, thing_id: str):
#     """
#     Get the thing this request is for.
#     request -- current request
#     thing_id -- ID of the thing to get, in string form
#     Returns the thing, or None if not found.
#     """
#     await websocket.accept()
#     logger.info(f"{websocket.url} connected, ip {websocket.client.host}")
#
#     things = websocket.app.state.things
#     thing = await things.get_thing(thing_id)
#
#     if thing is None:
#         await websocket.send_json(
#             {
#                 "messageType": "error",
#                 "data": {
#                     "status": "404 Not Found",
#                     "message": "Invalid thing_id",
#                 },
#             },
#             mode="binary",
#         )
#         return None, None
#     else:
#         subscriber = Subscriber(websocket)
#         await thing.add_subscriber(subscriber)
#         ws_href = f"{websocket.url.scheme}://{websocket.headers.get('Host', '')}"
#
#         description = await thing.as_thing_description()
#         description["links"].append(
#             {"rel": "alternate", "href": f"{ws_href}{await thing.get_href()}", }
#         )
#         description[
#             "base"] = f"{websocket.url.scheme}://{websocket.headers.get('Host', '')}{await thing.get_href()}"
#         description["securityDefinitions"] = {
#             "nosec_sc": {"scheme": "nosec", },
#         }
#         description["security"] = "nosec_sc"
#
#         await subscriber.send_json(description)
#         return thing, subscriber


async def check_property_and_get_thing(property_name: str, thing=Depends(get_thing)):
    if not await thing.has_property(property_name):
        raise HTTPException(status_code=404)
    return thing


from pyee import AsyncIOEventEmitter as EventEmitter

ee = EventEmitter()

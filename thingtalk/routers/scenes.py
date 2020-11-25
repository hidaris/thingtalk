import os
import uuid
import typing

from enum import Enum

from loguru import logger
from pydantic import ValidationError, BaseModel, constr

from fastapi import Depends, APIRouter
from fastapi.responses import UJSONResponse

from tinydb import TinyDB, Query

from ..toolkits.event_bus import ee


router = APIRouter()

data_ref = os.environ.get("TINY_DB", '/data/db.json')
# data_ref = os.environ.get("TINY_DB", '/tmp/db.json')
db = TinyDB(data_ref)

table = db.table("scenes")


{
     "name": "这是一个场景",
    "timeout": 0,
    "data": [
        {
            "thing_id": "xxxxx",
            "messageType": "setProperty",
            "data": {}
        },
        {
            "thing_id": "xxxxx",
            "messageType": "setProperty",
            "data": {}
        },
        {
            "thing_id": "xxxxx",
            "messageType": "setProperty",
            "data": {}
        }
    ]
}


class MsgType(str, Enum):
    set_property = 'setProperty'
    request_action = 'requestAction'
    run_scene = 'runScene'


class TopicMsg(BaseModel):
    topic: constr(regex=r'^things|scenes\/[0-9a-zA-Z\_\-\:]+$')
    messageType: MsgType
    data: typing.Dict[str, typing.Any]


class SceneInput(BaseModel):
    name: str
    data: typing.List[TopicMsg]


class Scene(BaseModel):
    id: str
    name: str
    data: typing.List[TopicMsg]


class SceneMsg(BaseModel):
    topic: constr(regex=r'^scenes\/[0-9a-zA-Z\_\-\:]+$')
    name: str
    data: typing.List[TopicMsg]


async def run_scene_by_id(scene_data: SceneMsg):
    scene_id = scene_data.topic.split("/")[1]
    SceneModel = Query()
    logger.debug(scene_id)
    scene = table.get(SceneModel.id == scene_id)
    logger.debug(scene)
    if scene:
        try:
            scene = Scene(**scene)
            for msg in scene.data:
                logger.debug(msg)
                ee.emit(msg.topic, msg)
        except ValidationError as e:
            logger.error(str(e))


@router.get("/scenes")
async def get_scenes():
    data = table.all()
    return UJSONResponse({"scenes": data})


@router.post("/scenes")
async def create_scene(scene: SceneInput):
    scene_data = scene.dict()
    scene_data.update({"id": str(uuid.uuid4())})
    logger.debug(scene_data)
    table.insert(scene_data)

    return UJSONResponse(scene_data)


@router.put("/scenes/{scene_id}")
async def update_scene(scene_id: str, scene_data: dict):
    SceneModel = Query()
    doc_ids = table.update(scene_data, SceneModel.id == scene_id)
    if doc_ids:
        rule = table.get(SceneModel.id == scene_id)

    return UJSONResponse(rule)


@router.post("/scenes/{scene_id}")
async def run_scene(scene_id: str):
    SceneModel = Query()
    scene = table.get(SceneModel.id == scene_id)
    logger.debug(scene)
    if scene:
        try:
            scene = Scene(**scene)
            for msg in scene.data:
                logger.debug(msg)
                ee.emit(msg.topic, msg)
            message = {
                "topic": f"scenes/{scene_id}",
                "messageType": "sceneStatus",
                "data": {}
            }
            logger.info(message)
            ee.emit(f"scenes/{scene_id}/state", message)
        except ValidationError as e:
            logger.error(str(e))

    return UJSONResponse({"msg": "success"})


@router.delete("/scenes/{scene_id}")
async def delete_scene(scene_id: str):
    SceneModel = Query()
    rule = table.get(SceneModel.id == scene_id)
    if rule:
        table.remove(SceneModel.id == scene_id)

    return UJSONResponse({"msg": "success"})

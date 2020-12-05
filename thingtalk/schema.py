import typing

from enum import Enum

from pydantic import BaseModel


class InputMsgType(str, Enum):
    subscribe = 'subscribe'
    set_property = 'setProperty'
    request_action = 'requestAction'


class InputMsg(BaseModel):
    topic: typing.Optional[str] = None
    messageType: InputMsgType
    data: typing.Dict[str, typing.Any]


class OutputMsgType(str, Enum):
    property_status = 'propertyStatus'
    action_status = 'actionStatus'
    scene_status = 'sceneStatus'
    cron_status = 'cronStatus'
    error = 'error'
    event = 'event'


class OutMsg(BaseModel):
    topic: str
    messageType: OutputMsgType
    data: typing.Dict[str, typing.Any]


class Question(BaseModel):
    op: str
    value: typing.Optional[typing.Any] = None

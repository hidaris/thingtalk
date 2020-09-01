import typing
import asyncio

from fastapi import Depends, APIRouter
from fastapi.exceptions import HTTPException
from fastapi.responses import UJSONResponse, Response

from ..dependencies import get_thing
from ..models.thing import Thing

router = APIRouter()


async def perform_action(action):
    """Perform an Action in a coroutine."""
    await action.start()


@router.get("/actions")
async def get_actions(thing: Thing = Depends(get_thing)) -> UJSONResponse:
    """
    Handle a request to /actions.
    :param thing-- the thing this request is for
    :return UJSONResponse
    """
    return UJSONResponse(await thing.get_action_descriptions())


@router.post("/actions")
async def revoke_actions(
        message: typing.Dict[str, typing.Any],
        thing: Thing = Depends(get_thing)) -> UJSONResponse:
    """
    Handle a POST request.
    :param thing -- the thing this request is for
    :param message -- the request body
    :return UJSONResponse
    """
    response = {}
    for action_name, action_params in message.items():
        input_ = None
        if "input" in action_params:
            input_ = action_params["input"]
        action = await thing.perform_action(action_name, input_)
        if action:
            response.update(await action.as_action_description())

            # Start the action
            asyncio.create_task(perform_action(action))

    return UJSONResponse(response, status_code=201)


@router.get("/actions/{action_name}")
async def get_action(
        action_name: str,
        thing: Thing = Depends(get_thing)) -> UJSONResponse:
    """
    Handle a request to /actions/<action_name>.
    :param thing -- the thing this request is for
    :param action_name -- name of the action from the URL path
    :return UJSONResponse
    """
    return UJSONResponse(
        await thing.get_action_descriptions(action_name=action_name)
    )


@router.post("/actions/{action_name}")
async def invoke_action(
        action_name: str,
        message: typing.Dict[str, typing.Any],
        thing: Thing = Depends(get_thing)) -> UJSONResponse:
    """
    Handle a POST request.
    :param thing -- the thing this request is for
    :param action_name -- name of the action from the URL path
    :param message -- the request body
    :return UJSONResponse
    """
    response = {}
    for name, action_params in message.items():
        if name != action_name:
            continue

        input_ = None
        if "input" in action_params:
            input_ = action_params["input"]

        action = await thing.perform_action(name, input_)
        if action:
            response.update(await action.as_action_description())

            # Start the action
            asyncio.create_task(perform_action(action))

    return UJSONResponse(response, status_code=201)


@router.get("/actions/{action_name}/{action_id}")
async def get_action_by_id(
        action_name: str,
        action_id: str,
        thing: Thing = Depends(get_thing)) -> UJSONResponse:
    """
    Handle a request to /actions/<action_name>/<action_id>.
    :param thing -- the thing this request is for
    :param action_name -- name of the action from the URL path
    :param action_id -- the action ID from the URL path
    :return UJSONResponse
    """
    action = await thing.get_action(action_name, action_id)
    if action is None:
        raise HTTPException(status_code=404)

    return UJSONResponse(await action.as_action_description())


@router.put("/actions/{action_name}/{action_id}")
async def update_action_by_id(
        action_name: str,
        action_id: str,
        thing: Thing = Depends(get_thing)) -> UJSONResponse:
    """
    Handle a PUT request.
    TODO: this is not yet defined in the spec
    :param thing -- the thing this request is for
    :param action_name -- name of the action from the URL path
    :param action_id -- the action ID from the URL path
    :return UJSONResponse
    """
    return UJSONResponse({"msg": "success"}, status_code=200)


@router.delete("/actions/{action_name}/{action_id}")
async def cancel_action_by_id(
        action_name: str,
        action_id: str,
        thing: Thing = Depends(get_thing)) -> Response:
    """
    Handle a DELETE request.
    :param thing -- the thing this request is for
    :param action_name -- name of the action from the URL path
    :param action_id -- the action ID from the URL path
    :return UJSONResponse
    """
    if await thing.remove_action(action_name, action_id):
        return Response(status_code=204)
    else:
        raise HTTPException(status_code=404)

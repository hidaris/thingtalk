import typing

from fastapi import Depends, APIRouter
from fastapi.exceptions import HTTPException
from fastapi.responses import UJSONResponse

from ..dependencies import get_thing, check_property_and_get_thing
from ..models.thing import ExposedThing
from ..models.errors import PropertyError

router = APIRouter()


@router.get("/properties")
async def get_properties(thing: ExposedThing = Depends(get_thing)) -> UJSONResponse:
    """
    Handle a request to /properties.
    :param thing -- the thing this request is for"
    :return: UJSONResponse
    """
    return UJSONResponse(await thing.get_properties())


@router.get("/properties/{property_name}")
async def get_property(
        property_name: str,
        thing: ExposedThing = Depends(check_property_and_get_thing)) -> UJSONResponse:
    """
    Handle a request to /properties/<property>.
    :param: thing-- the thing this request is for"
    :param: property_name -- name of the thing property this request is for
    :return: UJSONResponse
    """
    return UJSONResponse(
        {property_name: thing.get_property(property_name), }
    )


@router.put("/properties/{property_name}")
async def put_property(
        property_name: str,
        data: typing.Dict[str, typing.Any],
        thing: ExposedThing = Depends(get_thing)) -> UJSONResponse:
    """
    Handle a PUT request to /properties/<property>.
    :param property_name -- the name of the property from the URL path
    :param data -- data of this request put
    :param thing -- the thing this request is for
    :return: UJSONResponse
    """
    try:
        await thing.set_property(property_name, data[property_name])
    except PropertyError:
        raise HTTPException(status_code=400)

    return UJSONResponse(
        {property_name: thing.get_property(property_name), }
    )
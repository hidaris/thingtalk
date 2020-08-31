from fastapi import Depends, APIRouter
from fastapi.responses import UJSONResponse

from ..dependencies import get_thing
from ..models.thing import Thing

router = APIRouter()


@router.get("/events")
async def get_events(thing: Thing = Depends(get_thing)) -> UJSONResponse:
    """
    Handle a request to /events.
    :param thing -- the thing this request is for
    :return UJSONResponse
    """
    return UJSONResponse(await thing.get_event_descriptions())


@router.get("/events/{event_name}")
async def get_event(event_name: str, thing: Thing = Depends(get_thing)) -> UJSONResponse:
    """
    Handle a request to /events/<event_name>.
    :param thing -- the thing this request is for
    :param event_name -- name of the event from the URL path
    :return UJSONResponse
    """
    return UJSONResponse(await thing.get_event_descriptions(event_name=event_name))

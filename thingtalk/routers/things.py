import copy

from fastapi import APIRouter
from fastapi import Depends
from fastapi.requests import Request
from fastapi.responses import ORJSONResponse

from ..dependencies import get_thing
from ..models.thing import Thing
from ..utils import get_http_href, get_ws_href

router = APIRouter()


@router.get("/things")
async def get_things(request: Request) -> ORJSONResponse:
    """
    Handle a request to / when the server manages multiple things.
    Handle a GET request.
    :param request -- the request
    :return ORJSONResponse
    """
    things = request.app.state.things

    descriptions = []
    for idx, thing in tuple(await things.get_things()):
        description = thing.as_thing_description()
        description["href"] = thing.href
        description["links"].append({
            "rel": "alternate",
            "href": f"{get_ws_href(request)}{thing.href}",
        })
        description["base"] = f"{get_http_href(request)}{thing.href}"

        description["securityDefinitions"] = {
            "nosec_sc": {"scheme": "nosec", },
        }
        description["security"] = "nosec_sc"

        bak = copy.deepcopy(description)
        descriptions.append(bak)

    return ORJSONResponse(descriptions)


@router.get("/things/{thing_id}")
async def get_thing_by_id(
        request: Request,
        thing: Thing = Depends(get_thing)) -> ORJSONResponse:
    """
    Handle a GET request, including websocket requests.
    :param request: the request
    :param thing -- the thing this request is for
    :return ORJSONResponse
    """
    description = thing.as_thing_description()
    description["href"] = thing.href
    description["links"].append(
        {
            "rel": "alternate",
            "href": f"{get_ws_href(request)}{thing.href}",
        }
    )
    description["base"] = f"{get_http_href(request)}{thing.href}"
    description["securityDefinitions"] = {
        "nosec_sc": {"scheme": "nosec", },
    }
    description["security"] = "nosec_sc"

    return ORJSONResponse(description)

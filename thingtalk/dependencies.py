from fastapi.exceptions import HTTPException
from fastapi import Request, Depends


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


async def check_property_and_get_thing(property_name: str, thing=Depends(get_thing)):
    if not await thing.has_property(property_name):
        raise HTTPException(status_code=404)
    return thing

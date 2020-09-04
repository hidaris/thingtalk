"""High-level Subscriber base class implementation."""

from fastapi.websockets import WebSocket, WebSocketDisconnect
from websockets import ConnectionClosedOK


class Subscriber:
    """Abstract Subscriber class."""

    def __init__(self, websocket: WebSocket):
        self.active_connection = websocket

    async def update_property(self, property_, value_):
        """
        Send an update about a Property.
        :param property_: Property
        """
        message = {
            "messageType": "propertyStatus",
            "data": {property_.name: value_, },
        }

        await self.send_json(message)

    async def update_action(self, action):
        """
        Send an update about an Action.
        :param action: Action
        """
        message = {
            "messageType": "actionStatus",
            "data": await action.as_action_description(),
        }

        await self.send_json(message)

    async def update_event(self, event):
        """
        Send an update about an Event.
        :param event: Event
        """
        message = {
            "messageType": "event",
            "data": await event.as_event_description(),
        }

        await self.send_json(message)

    async def update_error(self, error_):
        """
        Send an update about an Error.
        :param error_: Error
        """
        message = {
            "messageType": "error",
            "data": {"status": "400 Bad Request", "message": str(error_), },
        }

        await self.send_json(message)

    async def send_json(self, message):
        try:
            await self.active_connection.send_json(message, mode="binary")
        except (WebSocketDisconnect, ConnectionClosedOK):
            pass

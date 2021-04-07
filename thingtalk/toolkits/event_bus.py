from pyee import AsyncIOEventEmitter
from loguru import logger


class MessageBus(AsyncIOEventEmitter):
    def on(self, event, f=None):
        logger.debug(f"on event {event}")
        return super().on(event, f=f)


mb = MessageBus()

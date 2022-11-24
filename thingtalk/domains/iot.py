from loguru import logger

from ..models.thing import Thing


class Device(Thing):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    async def subscribe_broadcast(self):
        if "Light" in self._type:
            topic = "broadcast/light"
            self.on(topic, self.dispatch)
            self.subscribe_topics.append(topic)
            logger.info("subscribe light broadcast")
        elif "OnOffSwitch" in self._type:
            topic = "broadcast/switch"
            self.on(topic, self.dispatch)
            self.subscribe_topics.append(topic)
            logger.info("subscribe switch broadcast")
        elif "Cover" in self._type:
            topic = "broadcast/cover"
            self.on(topic, self.dispatch)
            self.subscribe_topics.append(topic)
            logger.info("subscribe cover broadcast")

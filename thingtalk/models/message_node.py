import asyncio

import zmq
import zmq.asyncio

import ujson as json

from loguru import logger


class MessageNode:
    def __init__(self):
        self.zmq_context = zmq.asyncio.Context()

        self.subscriber = self.zmq_context.socket(zmq.SUB)
        connect_string = 'tcp://localhost:2001'
        logger.info(f"thing/{self.id} connect suber {connect_string}")
        self.subscriber.connect(connect_string)

        self.subscriber_list = []
        asyncio.create_task(self.receive_loop())

    def set_subscriber_topic(self, topic: str):
        if not type(topic) is str:
            raise TypeError('Subscriber topic must be string')
        self.subscriber_list.append(topic)

    async def send(self, topic, payload):
        """
        This method will publish a  payload and its associated topic
        :param payload: Protocol message to be published
        :param topic: A string value
        """
        logger.info(f"topic {topic} payload {payload}")
        payload_str = json.dumps(payload)
        await self.publisher.send_string(f"{topic} {payload_str}")

    async def receive_loop(self):
        # We can connect to several endpoints if we desire, and receive from all.
        logger.info("start receive loop")
        if self.subscriber_list:
            for topic in self.subscriber_list:
                self.subscriber.subscribe(topic)
                self.subscribed_topics.add(topic)
        self.subscriber.subscribe("get_things")
        try:
            while True:
                recv_str = await self.subscriber.recv_string()
                logger.info(recv_str)
                words = recv_str.split()
                topic = words[0]
                logger.info(f"topic: {topic}")
                payload_str = words[1]
                payload = json.loads(payload_str)
                logger.info(f"payload: {payload}")
                # topic: things/thing_id {"type": "set_property", "data": {"name": value}}
                thing_topic_and_id = topic.split("/")
                if len(thing_topic_and_id) == 2 and thing_topic_and_id[0] == "things":
                    thing_id = thing_topic_and_id[1]
                    type = payload.get("type")
                    data = payload.get("data")
                    thing = await self.app.state.things.get_thing(thing_id)
                    if type == 'set_property':
                        for property_name, property_value in data.items():
                            await thing.set_property(property_name, property_value)

        except asyncio.CancelledError:
            logger.info("cancel receive loop")

    async def clean_up(self):
        """
        Clean up before exiting.
        """
        logger.info("Clean up zmq before exiting.")
        await self.publisher.close()
        await self.subscriber.close()
        await self.zmq_context.term()

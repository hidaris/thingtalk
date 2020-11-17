import asyncio
import typing

from contextlib import AsyncExitStack

from loguru import logger
from asyncio_mqtt import Client, MqttError

from .event_bus import ee


class Mqtt:
    def __init__(self, host="127.0.0.1", username=None, password=None,
                 reconnect_interval=3, topic_filters=None):
        self.host: str = host
        self.username: str = username
        self.password: str = password
        self.reconnect_interval: int = reconnect_interval  # [seconds]
        self.started: bool = False
        self.client: typing.Optional[Client] = None
        self.task: typing.Optional[asyncio.Task] = None
        # You can create any number of topic filters
        self.topic_filters: typing.Optional[typing.Tuple[str]] = topic_filters

    def startup(self):
        logger.debug("mqtt service startup")
        ee.on("mqtt", self.publish)
        self.task = asyncio.create_task(self.connect())

    def shutdown(self):
        self.task.cancel()
        self.client = None
        ee.remove_listener("mqtt", self.publish)
        logger.debug("mqtt service shutdown")

    def set_filter_topics(self, topic_filters: typing.Tuple[str]):
        self.topic_filters = topic_filters

    async def mqtt_context_wrapper(self):
        # We 💛 context managers. Let's create a stack to help
        # us manage them.
        async with AsyncExitStack() as stack:
            # Keep track of the asyncio tasks that we create, so that
            # we can cancel them on exit
            tasks = set()
            stack.push_async_callback(self.cancel_tasks, tasks)

            # Connect to the MQTT broker
            self.client = Client(self.host, username=self.username, password=self.password)
            await stack.enter_async_context(self.client)

            for topic_filter in self.topic_filters:
                # Log all messages that matches the filter
                manager = self.client.filtered_messages(topic_filter)
                messages = await stack.enter_async_context(manager)
                # template = f'[topic_filter="{topic_filter}"] {{}}'
                task = asyncio.create_task(self.handle_msgs_wrapper(messages, topic_filter))
                tasks.add(task)

            # Messages that doesn't match a filter will get logged here
            # messages = await stack.enter_async_context(client.unfiltered_messages())
            # task = asyncio.create_task(handle_msgs(messages, "[unfiltered] {}"))
            # tasks.add(task)

            # Subscribe to topic(s)
            # 🤔 Note that we subscribe *after* starting the message
            # loggers. Otherwise, we may miss retained messages.
            await self.client.subscribe("zigbee2mqtt/#")

            # Wait for everything to complete (or fail due to, e.g., network
            # errors)
            await asyncio.gather(*tasks)

    async def publish(self, topic, message):
        # Publish a message
        if self.client:
            logger.info(f'[topic="{topic}"] Publishing message={message}')
            await self.client.publish(topic, message, qos=1)
        else:
            logger.error("mqtt client was shutdown")

    async def handle_msgs_wrapper(self, messages, _filter):
        try:
            await self.handle_msgs(messages, _filter)
        except Exception as e:
            logger.error(str(e))

    async def handle_msgs(self, messages, _filter):
        # 🤔 Note that we assume that the message paylod is an
        # UTF8-encoded string (hence the `bytes.decode` call).
        pass

    async def cancel_tasks(self, tasks):
        logger.info("cancel tasks")
        for task in tasks:
            if task.done():
                continue
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

    async def connect(self):
        # Run the advanced_example indefinitely. Reconnect automatically
        # if the connection is lost.
        while True:
            try:
                await self.mqtt_context_wrapper()
            except MqttError as error:
                self.client = None
                logger.error(f'Error "{error}". Reconnecting in {self.reconnect_interval} seconds.')
            finally:
                await asyncio.sleep(self.reconnect_interval)

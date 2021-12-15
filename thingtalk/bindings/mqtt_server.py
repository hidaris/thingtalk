from __future__ import annotations

import copy
import uuid
import asyncio

from typing import TYPE_CHECKING, Optional, Any

from gmqtt import Client
from loguru import logger

from thingtalk.models.errors import PropertyError
from thingtalk.utils import get_http_host, get_ws_host

if TYPE_CHECKING:
    from thingtalk.servient import Servient
    from thingtalk.models.thing import ExposedThing
from ..protocol_interfaces import ProtocolServer


class MqttServer(ProtocolServer):
    """
    A HTTP server that can be used to serve ThingTalk code.
    """

    def __init__(self, 
        host: str='localhost',
        port: str='8000',
        token: str='',
        username: str='',
        password: str='',
        path="",
        prefix="",
        **kwargs
    ):
        """
        Initialize the MQTT server.

        :param host: The hostname to bind to.
        :param port: The port to bind to.
        :param path: The path to serve ThingTalk code from.
        :param token: The token to use for authentication.
        :param username: The username to use for authentication.
        :param password: The password to use for authentication.
        """
        super().__init__(**kwargs)
        self.host = host
        self.port = port
        self.path = path
        self.prefix = prefix
        self.sub_client = Client(f"sub_client:{uuid.uuid4().hex}")
        self.pub_client = Client(f"pub_client:{uuid.uuid4().hex}")

        self.assign_callbacks_to_client(self.sub_client)
        self.assign_callbacks_to_client(self.pub_client)

        if token:
            self.sub_client.set_auth_credentials(token, None)
            self.pub_client.set_auth_credentials(token, None)
        if username and password:
            self.sub_client.set_auth_credentials(username, password)
            self.pub_client.set_auth_credentials(username, password)

    async def connect(self):
        await self.sub_client.connect(self.host, self.port)
        await self.pub_client.connect(self.host, self.port)

        self.sub_client.subscribe("things/#", qos=1, subscription_identifier=1, retain_as_published=True)

    async def set_app(self, app):
        # single or multiple thing
        @mb.on("register")
        def on_register(thing_id: str, des):
            logger.debug("register")
            mb.on(f"things/{thing_id}/td", partial(self._publish, f"things/{thing_id}/td", retain=True))
            mb.on(f"things/{thing_id}/event", partial(self._publish, f"things/{thing_id}/event"))
            mb.on(f"things/{thing_id}/values", partial(self._publish, f"things/{thing_id}/values"))
            mb.on(f"things/{thing_id}/actions", partial(self._publish, f"things/{thing_id}/actions"))
            mb.on(f"things/{thing_id}/error", partial(self._publish, f"things/{thing_id}/error"))

            @mb.on(f"things/{thing_id}/get")
            def get_property(property_names):
                thing = self.servient.getThing(thing_id)
                if thing:
                    for name in property_names:
                        value = thing.get_property(name)
                        mb.emit(f"things/{thing_id}/state", {name: value})

            mb.emit(f"things/{thing_id}/td", des)

        # gateway
        @mb.on("discover")
        def on_discover(thing_id: str, des):
            mb.on(f"things/{thing_id}/set", partial(self._publish, f"things/{thing_id}/set"))
            mb.on(f"things/{thing_id}/request_action", partial(self._publish, f"things/{thing_id}/error"))

            @mb.on(f"things/{thing_id}/get")
            def get_property(property_names):
                thing = self.servient.getThing(thing_id)
                if thing:
                    for name in property_names:
                        value = thing.get_property(name)
                        mb.emit(f"things/{thing_id}/state", {name: value})

            mb.emit(f"things/{thing_id}/td", des)

    async def _publish(self, topic: str, payload: dict, retain=False):
        logger.debug(retain)
        if 'values' in topic:
            payload = payload.get("data")
        await self.publish(topic, payload, retain=retain)

    async def publish(self, topic, payload, retain=False, qos=1, content_type='json',
                      message_expiry_interval=60, topic_alias=1, user_property=('time', str(time.time()))):
        # just another way to publish same message
        if retain:
            self.pub_client.publish(topic, payload, qos=qos, content_type=content_type,
                                    topic_alias=topic_alias, user_property=user_property, retain=retain)
        else:
            self.pub_client.publish(topic, payload, qos=qos, content_type=content_type,
                                    message_expiry_interval=message_expiry_interval, topic_alias=topic_alias,
                                    user_property=user_property, retain=retain)

    async def disconnect(self):
        await self.pub_client.disconnect()
        await self.sub_client.disconnect(session_expiry_interval=0)

    def assign_callbacks_to_client(self, client: Client):
        # helper function which sets up client's callbacks
        client.on_connect = self.on_connect
        client.on_message = self.on_message
        client.on_disconnect = self.on_disconnect
        client.on_subscribe = self.on_subscribe

    def on_connect(self, client: Client, flags, rc, properties):
        logger.info(f"[CONNECTED {client._client_id}]")

    async def on_message(self, client: Client, topic, payload, qos, properties):
        pass

    def on_disconnect(self, client: Client, packet, exc=None):
        logger.info(f"[DISCONNECTED {client._client_id}]")

    def on_subscribe(self, client: Client, mid, qos, properties):
        # in order to check if all the subscriptions were successful, we should first get all subscriptions with this
        # particular mid (from one subscription request)
        subscriptions = client.get_subscriptions_by_mid(mid)
        for subscription, granted_qos in zip(subscriptions, qos):
            # in case of bad suback code, we can resend  subscription
            if granted_qos >= gmqtt.constants.SubAckReasonCode.UNSPECIFIED_ERROR.value:
                logger.warning('[RETRYING SUB {}] mid {}, reason code: {}, properties {}'.format(
                    client._client_id, mid, granted_qos, properties))
                client.resubscribe(subscription)
            logger.info('[SUBSCRIBED {}] mid {}, QOS: {}, properties {}'.format(
                client._client_id, mid, granted_qos, properties))

    def start(self, servient: Servient):
        """
        Start the HTTP server.
        """
        self.servient = servient

    async def expose(self, thing: ExposedThing, tdTemplate) -> None:
        """
        Expose a ThingTalk thing to the HTTP server.
        """
        pass

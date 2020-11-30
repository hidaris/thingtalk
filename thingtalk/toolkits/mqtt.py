import uuid
import time

import gmqtt

from loguru import logger

from .event_bus import ee


class Mqtt:
    # create client instance, kwargs (session expiry interval and maximum packet size)
    # will be send as properties in connect packet
    def __init__(self,
                 broker_host,
                 broker_port,
                 token: str = '',
                 username: str = '',
                 password: str = ''):
        self.sub_client = gmqtt.Client(f"sub_client:{uuid.uuid4().hex}",
                                       session_expiry_interval=600,
                                       maximum_packet_size=65535)
        self.pub_client = gmqtt.Client(f"pub_client:{uuid.uuid4().hex}")

        self.assign_callbacks_to_client(self.sub_client)
        self.assign_callbacks_to_client(self.pub_client)

        if token:
            self.sub_client.set_auth_credentials(token, None)
            self.pub_client.set_auth_credentials(token, None)
        if username and password:
            self.sub_client.set_auth_credentials(username, password)
            self.pub_client.set_auth_credentials(username, password)

        self.broker_host = broker_host
        self.broker_port = broker_port

    async def connect(self):
        await self.sub_client.connect(self.broker_host, self.broker_port)
        await self.pub_client.connect(self.broker_host, self.broker_port)

    async def set_app(self, app):
        await self.sub_client.set_app(app)
        await self.pub_client.set_app(app)

    # two overlapping subscriptions with different subscription identifiers

    # this message received by sub_client will have two subscription identifiers
    async def publish(self, topic, payload):
        # just another way to publish same message
        self.pub_client.publish(topic, payload, qos=1, content_type='json',
                                message_expiry_interval=60, topic_alias=1, user_property=('time', str(time.time())))

    async def disconnect(self):
        await self.pub_client.disconnect()
        await self.sub_client.disconnect(session_expiry_interval=0)

    def assign_callbacks_to_client(self, client):
        # helper function which sets up client's callbacks
        client.on_connect = self.on_connect
        client.on_message = self.on_message
        client.on_disconnect = self.on_disconnect
        client.on_subscribe = self.on_subscribe

    def on_connect(self, client, flags, rc, properties):
        logger.info(f"[CONNECTED {client._client_id}]")

    async def on_message(self, client, topic, payload, qos, properties):
        logger.info(
            f"[RECV MSG {client._client_id}] TOPIC: {topic} PAYLOAD: {payload} QOS: {qos} PROPERTIES: {properties}")

    def on_disconnect(self, client, packet, exc=None):
        logger.info(f"[DISCONNECTED {client._client_id}]")

    def on_subscribe(self, client, mid, qos, properties):
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

import gmqtt

from loguru import logger
from config import settings
from ..toolkits.mqtt import Mqtt, Client
from ..models.thing import Thing
from ..models.action import Action


class MqttAction(Action):
    async def perform_action(self):
        await mqtt.publish(f"thingtalk/things/{self.thing.id}/action", self.input)


class MqttThing(Thing):
    async def property_action(self, property_):
        await mqtt.publish(f"thingtalk/things/{self.id}",
                           {property_.name: property_.value})


class ThingMqtt(Mqtt):
    def on_connect(self, client: Client, flags, rc, properties):
        logger.info(f"[CONNECTED {client._client_id}]")
        client_ids = client._client_id.split(":")
        if client_ids[0] == 'sub_client':
            client.subscribe('thingtalk/#', qos=1, subscription_identifier=1)

    async def on_message(self, client: Client, topic, payload, qos, properties):
        logger.info(
            f"[RECV MSG {client._client_id}] TOPIC: {topic} PAYLOAD: {payload} QOS: {qos} PROPERTIES: {properties}")
        topic_words = topic.split("/")

        if topic == 'thingtalk/bridge/state':
            logger.debug(payload)

        if client.app.state.mode == "gateway":
            logger.debug("gateway")
            if topic[2] == 'config':
                logger.debug(payload)

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


username = settings.MQTT_USERNAME
password = settings.MQTT_PASSWORD
host = settings.MQTT_HOST

mqtt = ThingMqtt(host, "1883", username=username, password=password)

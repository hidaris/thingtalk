import gmqtt
import ujson as json

from loguru import logger

# from config import settings
from ..toolkits.mqtt import Mqtt, Client
from ..models.thing import Thing
from ..models.property import Property
from ..models.action import Action


class MqttAction(Action):
    async def perform_action(self):
        await mqtt.publish(f"thingtalk/things/{self.thing.id}/action", self.input)


class MqttThing(Thing):
    async def property_action(self, property_):
        await mqtt.publish(
            f"thingtalk/things/{self.id}/state",
            {property_.name: await property_.get_value()},
        )


class ThingMqtt(Mqtt):
    def on_connect(self, client: Client, flags, rc, properties):
        logger.info(f"[CONNECTED {client._client_id}]")
        client_ids = client._client_id.split(":")
        if client_ids[0] == "sub_client":
            client.subscribe("things/#", qos=1, subscription_identifier=1)
            client.subscribe("thingtalk/#", qos=1, subscription_identifier=1)

    async def on_message(self, client: Client, topic: str, payload, qos, properties):
        """logger.info(
            f"[RECV MSG {client._client_id}] TOPIC: {topic} PAYLOAD: {payload} QOS: {qos} PROPERTIES: {properties}"
        )"""
        """ logger.debug(topic) """
        topic_words = topic.split("/")
        logger.debug(f"current mode {client.app.state.mode}")
        logger.debug(topic)
        logger.debug(payload)
        if topic == "thingtalk/bridge/state":
            logger.debug(payload)

        if client.app.state.mode == "gateway":
            """ logger.debug(topic_words) """
            if len(topic_words) == 3 and topic_words[2] == "config":
                payload = json.loads(payload)
                thing = MqttThing(
                    id_=payload.get("id"),
                    title=payload.get("title"),
                    type_=payload.get("type"),
                    description_=payload.get("description"),
                )
                for name, metadata in payload.get("properties").items():
                    del metadata["links"]
                    thing.add_property(
                        Property(
                            name,
                            metadata=metadata,
                        )
                    )
                for name, metadata in payload.get("actions").items():
                    del metadata["links"]
                    thing.add_available_mqtt_action(MqttAction, name, metadata)
                await client.app.state.things.add_thing(thing)

        if len(topic_words) == 4 and topic_words[3] == "state":
            payload = json.loads(payload)
            if client.app.state.mode == "single":
                thing = client.app.state.thing.get_thing()
                for name, value in payload.items():
                    await thing.sync_property(name, value)

    def on_disconnect(self, client: Client, packet, exc=None):
        logger.info(f"[DISCONNECTED {client._client_id}]")

    def on_subscribe(self, client: Client, mid, qos, properties):
        # in order to check if all the subscriptions were successful, we should first get all subscriptions with this
        # particular mid (from one subscription request)
        subscriptions = client.get_subscriptions_by_mid(mid)
        for subscription, granted_qos in zip(subscriptions, qos):
            # in case of bad suback code, we can resend  subscription
            if granted_qos >= gmqtt.constants.SubAckReasonCode.UNSPECIFIED_ERROR.value:
                logger.warning(
                    "[RETRYING SUB {}] mid {}, reason code: {}, properties {}".format(
                        client._client_id, mid, granted_qos, properties
                    )
                )
                client.resubscribe(subscription)
            logger.info(
                "[SUBSCRIBED {}] mid {}, QOS: {}, properties {}".format(
                    client._client_id, mid, granted_qos, properties
                )
            )


""" username = settings.MQTT_USERNAME
password = settings.MQTT_PASSWORD
host = settings.MQTT_HOST """
username = "longan"
password = "longan"
host = "127.0.0.1"

mqtt = ThingMqtt(host, "1883", username=username, password=password)

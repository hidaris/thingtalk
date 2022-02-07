from ..models.thing import ExposedThing
from ..models.property import Property
from ..models.action import Action
from ..models.event import Event


class MqttAction(Action):
    async def perform_action(self):
        self.thing.emit(
            f"things/{self.thing.id}/request_action",
            {"id": self.id, self.title: self.input},
        )


class MqttThing(ExposedThing):
    async def property_action(self, property_: Property):
        self.emit(
            f"things/{self.id}/set",
            {property_.name: property_.value},
        )

    # @staticmethod
    # def produce(des: dict) -> ExposedThing:
    #     thing = MqttThing(
    #         id=des.get("id"),
    #         title=des.get("title"),
    #         type_=des.get("@type"),
    #         description_=des.get("description"),
    #     )
    #     for name, metadata in des.get("properties").items():
    #         del metadata["links"]
    #         thing.add_property(
    #             Property(
    #                 name,
    #                 metadata=metadata,
    #             )
    #         )
    #     for name, metadata in des.get("actions").items():
    #         del metadata["links"]
    #         thing.add_available_mqtt_action(MqttAction, name, metadata)

    #     for name, metadata in des.get("events").items():
    #         del metadata["links"]

    #         class MqttEvent(Event):
    #             title = name
    #             schema = metadata

    #         thing.add_available_event(MqttEvent)
    #     thing.href_prefix = f"/things/{thing.id}"

    #     return thing
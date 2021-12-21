from loguru import logger

from thingtalk.servient import Servient
from thingtalk.bindings.mqtt_server import MqttServer


servient = Servient()
servient.addServer(
    MqttServer(
        port=1883
    )
)
# wot = WoTImpl(servient)

thing = servient.produce(
    {
        "@context": "https://www.w3.org/2019/wot/td/v1",
        "title": "MyCounter",
        "properties": {
            "count": {
                type: "integer",
            },
        },
    }
)

# logger.info("Produced " + thing.getThingDescription().title)
# thing.writeProperty("count", 0)

# await thing.expose()
# servient.start()
app = servient.app

# logger.info(thing.getThingDescription().title + " ready")
# logger.info("TD : " + json.dumps(thing.getThingDescription()))

# c = thing.readProperty("count")
# logger.info("cound is " + c)

# asyncio.run(main())

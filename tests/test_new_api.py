from loguru import logger

from thingtalk.servient import Servient
from thingtalk.bindings.http_server import HttpServer
from thingtalk.wot_impl import WoTImpl


servient = Servient()
# servient.addServer(
#     HttpServer(
#         port=8081
#     )
# )
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
servient.start()

# logger.info(thing.getThingDescription().title + " ready")
# logger.info("TD : " + json.dumps(thing.getThingDescription()))

# c = thing.readProperty("count")
# logger.info("cound is " + c)

# asyncio.run(main())

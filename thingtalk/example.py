from loguru import logger


servient = Servient()
servient.addServer(
    HttpServer({
        port: 8081
    })
)


wot = await servient.start()

thing = WoT.produce({
        "@context": "https://www.w3.org/2019/wot/td/v1",
        title: "MyCounter",
        properties: {
            count: {
                type: "integer",
            },
        },
    })

logger.info("Produced " + thing.getThingDescription().title)
thing.writeProperty("count", 0)

await thing.expose()
            
logger.info(thing.getThingDescription().title + " ready")
logger.info("TD : " + json.dumps(thing.getThingDescription()))
        
c = thing.readProperty("count")
logger.info("cound is " + c)

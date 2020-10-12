import ujson as json


async def get_rules():
    pass


{
    "name": "这是一条联动",
    "premise_type": "And",
    "premise": [
        {
            "thing_id": "xxxxxxxxxxx",
            "type": "propertyStatus",
            "name": "",
            "value": "",
        },
        {
            "thing_id": "xxxxxxxxxxx",
            "type": "propertyStatus",
            "name": "",
            "value": "",
        }
    ],
    "conclusion": [
        {
            "thing_id": "xxxxxxxxx",
            "type": "setProperty",
            "name": "open",
            "value": ""
        }
    ]
}

from .dependencies import ee

mmm = {
    "thing_id": ""
}


async def compute_rule(msg):
    if


ee.on("xxx/state", compute_rule)
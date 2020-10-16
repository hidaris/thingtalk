import ujson as json


async def get_rules():
    pass


{
    "scene_id": "xxxxx",
    "name": "这是一个场景",
    "timeout": 0,
    "data": [
        {
            "thing_id": "xxxxx",
            "messageType": "setProperty",
            "data": {}
        },
        {
            "thing_id": "xxxxx",
            "messageType": "setProperty",
            "data": {}
        },
        {
            "thing_id": "xxxxx",
            "messageType": "setProperty",
            "data": {}
        }
    ]
}


class And:
    def __init__(self, *args, conclusion=None):
        self.args = args
        self.ans = None
        self.conclusion = conclusion

    def compute(self, _question_table):
        ans_lst = [_question_table[question]["should_be"] == question_table[question]["last_seen"] for question in
                   self.args]
        print(ans_lst)
        self.ans = len(set(ans_lst)) == 1 and (True in ans_lst)
        print(self.conclusion)
        if self.ans:
            for conclusion in self.conclusion:
                ee.emit(conclusion.get("thing_id"), conclusion)


class Or:
    def __init__(self, *args, conclusion=None):
        self.args = args
        self.ans = None
        self.conclusion = conclusion

    def compute(self, _question_table):
        ans_lst = [_question_table[question]["should_be"] == question_table[question]["last_seen"] for question in
                   self.args]
        self.ans = (True in ans_lst)
        if self.ans:
            ee.emit(self.conclusion.get("thing_id"), self.conclusion)


def generate_key(thing_id, property_name):
    return f"things_{thing_id}_{property_name}"


question_table = {
    "things_xxxx_state": {"should_be": "ON", "last_seen": "OFF"},
    "things_xxxx_brightness": {"should_be": 100, "last_seen": 50}
}

rule_table = {
    "things_xxxx_state": [And("things_xxxx_state", "things_xxxx_brightness"), ],
    "things_xxxx_brightness": [And("things_xxxx_state", "things_xxxx_brightness")]
}

{
    "name": "这是一条联动",
    "premise_type": "And",
    "premise": [
        {
            "thing_id": "xxxxxxxxxxx",
            "type": "propertyStatus",
            "name": "state",
            "value": "ON",
        },
        {
            "thing_id": "xxxxxxxxxxx",
            "type": "propertyStatus",
            "name": "brightness",
            "value": 100,
        }
    ],
    "conclusion": [
        {
            "thing_id": "xxxxxxxxx",
            "type": "setProperty",
            "data": {"open": ""}
        }
    ]
}

from .dependencies import ee


async def compute_rule(msg):
    if msg.get("messageType") == "propertyStatus":
        for property_name, value in msg.get("data").items():
            question_key = generate_key(msg.get("thing_id"), property_name)
            print(question_key)
            print(question_table)
            question_ans = question_table.get(question_key)
            if question_ans:
                question_ans["last_seen"] = value
                print(question_table)
                rule_lst = rule_table.get(question_key)
                for rule in rule_lst:
                    rule.compute(question_table)


async def load_rule(rules):
    for rule in rules:
        key_lst = []
        for pre in rule.get("premise"):
            key = generate_key(pre.get("thing_id"), pre.get("name"))
            key_lst.append(key)
            question_table.update({
                key: {"should_be": pre.get("value"), "last_seen": None}})

        for pre in rule.get("premise"):
            key = generate_key(pre.get("thing_id"), pre.get("name"))
            rule_lst = rule_table.get(key, [])
            rule_lst.append(And(*key_lst, conclusion=rule.get("conclusion")))
            rule_table.update({
                key: rule_lst
            })
            ee.on(f"{pre.get('thing_id')}/state", compute_rule)
    print(question_table)
    print(rule_table)


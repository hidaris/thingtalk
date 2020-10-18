from loguru import logger


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


# class Singleton:
#     def __init__(self, question, conclusion=None):
#         self.question = question
#         self.conclusion = conclusion
#
#     def compute(self, _question_env):
#         ans = (_question_env[self.question_key] == question_env[self.question_key]["last_seen"])
#         if ans:
#             logger.info(f"conclusions {self.conclusion}")
#             for conclusion in self.conclusion:
#                 ee.emit(conclusion.get("thing_id"), conclusion)


class And:
    def __init__(self, questions: dict, conclusion=None):
        self.questions = questions
        self.conclusion = conclusion

    def compute(self, _question_env):
        ans_lst = [_question_env[question_key] == should_value for question_key, should_value in
                   tuple(self.questions.items())]
        logger.debug(ans_lst)
        if len(set(ans_lst)) == 1 and (True in ans_lst):
            for conclusion in self.conclusion:
                ee.emit(conclusion.get("thing_id"), conclusion)
            for question_key, should_value in tuple(self.questions.items()):
                _question_env[question_key] = None
                logger.debug(_question_env)


class Or:
    def __init__(self, *question_keys, conclusion=None):
        self.question_keys = question_keys
        self.conclusion = conclusion

    def compute(self, _question_env):
        ans_lst = [_question_env[question_key] == should_value for question_key, should_value in
                   tuple(self.questions.items())]
        logger.debug(ans_lst)
        if True in ans_lst:
            ee.emit(self.conclusion.get("thing_id"), self.conclusion)


def generate_question_key(thing_id, property_name):
    return f"things_{thing_id}_{property_name}"


def generate_rule_id(thing_id, property_name, property_value):
    return f"things_{thing_id}_{property_name}_{property_value}"


question_env = {}

rule_env = {
    "things_xxxx_state_on": [
        And({"things_xxxx_state": "ON", "things_xxxx_brightness": 100}), ],
}

from .dependencies import ee


async def compute_rule(msg):
    if msg.get("messageType") == "propertyStatus":
        for property_name, value in msg.get("data").items():
            rule_key = generate_rule_id(msg.get("thing_id"), property_name, value)
            question_key = generate_question_key(msg.get("thing_id"), property_name)
            logger.info(f"compute rule: key {rule_key}")
            logger.debug(f"old question table {question_env}")
            question_env[question_key] = value
            logger.debug(f"new question table {question_env}")
            for rule in rule_env.get(rule_key, []):
                rule.compute(question_env)


async def load_rule(rules):
    for rule in rules:
        questions = {}
        # 更新 question env，以及当前 rule 需要查询的 question_keys
        for pre in rule.get("premise"):
            question_key = generate_question_key(pre.get("thing_id"), pre.get("name"))

            questions.update({question_key: pre.get("value")})
            question_env.update({question_key: None})

        for pre in rule.get("premise"):
            question_key = generate_question_key(pre.get("thing_id"), pre.get("name"))
            rule_key = generate_rule_id(pre.get("thing_id"), pre.get("name"), pre.get("value"))
            rule_lst = rule_env.get(question_key, [])
            if rule.get("premise_type") == "Singleton":
                question = {question_key: pre.get("value")}
                rule_lst.append(And(question, conclusion=rule.get("conclusion")))
            elif rule.get("premise_type") == "And":
                rule_lst.append(And(questions, conclusion=rule.get("conclusion")))
            elif rule.get("premise_type") == "Or":
                rule_lst.append(Or(questions, conclusion=rule.get("conclusion")))
            print(rule_lst)
            rule_env.update({
                rule_key: rule_lst
            })
            ee.on(f"{pre.get('thing_id')}/state", compute_rule)
    logger.info(f"load question env: {question_env}")
    logger.info(f"load rule env: {rule_env}")


async def disable_rule(topic):
    ee.remove_listener(topic, compute_rule)
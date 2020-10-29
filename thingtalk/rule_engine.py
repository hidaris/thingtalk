import typing

from enum import Enum

from loguru import logger
from pydantic import BaseModel, constr


class PremiseType(str, Enum):
    psingleton: str = "Singleton"
    pand: str = "And"
    por: str = "Or"


class ThingPremise(BaseModel):
    topic: constr(regex=r'^things\/[0-9a-zA-Z\_\-\:]+$')
    messageType: str
    name: str
    op: str
    value: typing.Any


class ScenePremise(BaseModel):
    topic: constr(regex=r'^scenes\/[0-9a-zA-Z\_\-\:]+$')
    messageType: str
    data: typing.Dict[str, typing.Any]


class Conclusion(BaseModel):
    topic: constr(regex=r'^things|scenes\/[0-9a-zA-Z\_\-\:]+$')
    messageType: str
    data: typing.Dict[str, typing.Any]


class RuleInput(BaseModel):
    enabled: bool
    name: str
    premise_type: PremiseType
    premise: typing.List[typing.Union[ThingPremise, ScenePremise]]
    conclusion: typing.List[Conclusion]


class Rule(BaseModel):
    id: str
    enabled: bool
    name: str
    premise_type: PremiseType
    premise: typing.List[typing.Union[ThingPremise, ScenePremise]]
    conclusion: typing.List[Conclusion]


class And:
    def __init__(self, questions: dict, enabled=True, conclusion=None):
        self.questions = questions
        self.enabled = enabled
        self.conclusion = conclusion

    async def compute(self, _question_env):
        ans = True
        for question_key, question in tuple(self.questions.items()):
            logger.debug(question)
            if question.get("op") == "eq":
                _res = _question_env[question_key] == question.get("value")
            elif question.get("op") == "gt":
                _res = _question_env[question_key] > question.get("value")
            elif question.get("op") == "lt":
                _res = _question_env[question_key] < question.get("value")
            elif question.get("op") == "run/scene":
                _res = _question_env[question_key] is True
            else:
                _res = False
            logger.debug(ans)
            logger.debug(_res)
            ans = ans and _res
        if ans:
            # logger.debug(self.conclusion)
            for conclusion in self.conclusion:
                ee.emit(conclusion.topic, conclusion)
            for question_key, should_value in tuple(self.questions.items()):
                _question_env[question_key] = None
                # logger.debug(_question_env)


class Or:
    def __init__(self, *question_keys, enabled=True, conclusion=None):
        self.question_keys = question_keys
        self.enabled = enabled
        self.conclusion = conclusion

    async def compute(self, _question_env):
        ans = False
        for question_key, question in tuple(self.questions.items()):
            logger.debug(question)
            if question.get("op") == "eq":
                _res = _question_env[question_key] == question.get("value")
            elif question.get("op") == "gt":
                _res = _question_env[question_key] > question.get("value")
            elif question.get("op") == "lt":
                _res = _question_env[question_key] < question.get("value")
            elif question.get("op") == "run/scene":
                _res = _question_env[question_key] is True
            else:
                _res = False
            ans = ans or _res
        if ans:
            for conclusion in self.conclusion:
                ee.emit(conclusion.topic, conclusion)
            for question_key, should_value in tuple(self.questions.items()):
                _question_env[question_key] = None


def generate_question_key(topic, property_name):
    topic_words = topic.split("/")
    return f"things_{topic_words[1]}_{property_name}"


def generate_scenes_key(topic):
    topic_words = topic.split("/")
    return f"scenes_{topic_words[1]}"


def generate_rule_id(topic, property_name, property_value):
    topic_words = topic.split("/")
    return f"things_{topic_words[1]}_{property_name}_{property_value}"


question_env = {}

# "things_xxxx_state_on": {
#     "xxxx": And({"things_xxxx_state": {"op": "eq", "value": "ON"},
#                  "things_xxxx_brightness": {"op": "lt", "value": 100}}, enabled=True)
# },
rule_env = {}

from .dependencies import ee


async def compute_rule(msg):
    if msg.get("messageType") == "propertyStatus":
        for property_name, value in msg.get("data").items():
            rule_key = generate_rule_id(msg.get("topic"), property_name, value)
            question_key = generate_question_key(msg.get("topic"), property_name)
            # logger.debug(f"old question table {question_env}")
            question_env[question_key] = value
            # question_env[question_key] = str(value)
            # logger.debug(f"new question table {question_env}")
            # if rule_env.get(rule_key):
            for rule_id, rule in tuple(rule_env.get(rule_key, {}).items()):
                logger.info(f"compute rule: key {rule_key} enabled {rule.enabled}")
                if rule.enabled:
                    await rule.compute(question_env)
    if msg.get("messageType") == "SceneStatus":
        rule_key = generate_scenes_key(msg.get("topic"))
        question_key = generate_scenes_key(msg.get("topic"))
        question_env[question_key] = True
        # if rule_env.get(rule_key):
        logger.info(f"compute rule: key {rule_key}")
        for rule_id, rule in tuple(rule_env.get(rule_key, {}).items()):
            logger.info(f"compute rule: key {rule_key} enabled {rule.enabled}")
            if rule.enabled:
                await rule.compute(question_env)


async def load_rules(rules: typing.List[typing.Optional[Rule]]):
    for rule in rules:
        await load_rule(rule)
    logger.info(f"load question env: {question_env}")
    logger.info(f"load rule env: {rule_env}")


async def load_rule(rule: Rule):
    questions = {}
    # 更新 question env，以及当前 rule 需要查询的 question_keys
    for pre in rule.premise:
        if "things" in pre.topic:
            question_key = generate_question_key(pre.topic, pre.name)
            questions.update({question_key: {"op": pre.op, "value": pre.value}})
            question_env.update({question_key: None})
        elif "scenes" in pre.topic:
            question_key = generate_scenes_key(pre.topic)
            questions.update({question_key: {"op": "run/scene"}})
            question_env.update({question_key: None})

    for pre in rule.premise:
        if "things" in pre.topic:
            rule_key = generate_rule_id(pre.topic, pre.name, pre.value)
        elif "scenes" in pre.topic:
            rule_key = generate_scenes_key(pre.topic)
        rule_id_map = rule_env.get(rule_key, {})
        logger.debug(rule_id_map)
        if rule.premise_type in ["And", "Singleton"]:
            rule_id_map.update({
                rule.id: And(questions, enabled=rule.enabled, conclusion=rule.conclusion)
            })
        elif rule.premise_type == "Or":
            rule_id_map.update({
                rule.id: Or(questions, enabled=rule.enabled, conclusion=rule.conclusion)
            })
        logger.info(f"add rule: key {rule_key}")
        rule_env.update({
            rule_key: rule_id_map
        })
        ee.on(f"{pre.topic}/state", compute_rule)
    logger.info(f"load rule env: {rule_env}")


logger.info(f"load question env: {question_env}")
logger.info(f"load rule env: {rule_env}")


async def disable_rule(rule_key, rule_db_id):
    logger.info(rule_env)
    logger.debug(rule_key)
    rule_bind = rule_env.get(rule_key)
    if rule_bind:
        if rule_bind.get(rule_db_id):
            del rule_bind[rule_db_id]
    logger.info(rule_env)

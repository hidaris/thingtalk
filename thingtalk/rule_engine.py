import typing
import uuid

from enum import Enum

from async_cron.job import CronJob
from async_cron.schedule import Scheduler
from loguru import logger
from pydantic import (
    BaseModel, constr, ValidationError,
    StrictInt, StrictBool, StrictFloat, StrictStr
)

from .toolkits.event_bus import ee
from .schema import OutMsg, Question


msh = Scheduler(locale="zh_CN")


class PremiseType(str, Enum):
    _singleton: str = "Singleton"
    _and: str = "And"
    _or: str = "Or"


class ThingPremise(BaseModel):
    topic: constr(regex=r'^things\/[0-9a-zA-Z\_\-\:]+$')
    messageType: str
    name: str
    op: str
    value: typing.Union[StrictInt, StrictBool, StrictFloat, StrictStr]


class ScenePremise(BaseModel):
    topic: constr(regex=r'^scenes\/[0-9a-zA-Z\_\-\:]+$')
    messageType: str
    data: typing.Dict[str, typing.Any]


class CronPremise(BaseModel):
    topic: constr(regex=r'^cron\/[0-9a-zA-Z\_\-\:]+$')
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
    premise: typing.List[typing.Union[ThingPremise, ScenePremise, CronPremise]]
    conclusion: typing.List[Conclusion]


class Rule(RuleInput):
    id: str


class And:
    def __init__(self, questions: typing.Dict[str, Question], enabled=True, conclusion=None):
        self.questions = questions
        self.enabled = enabled
        self.conclusion = conclusion

    def __repr__(self):
        return f"And({self.questions}...)"


class Or:
    def __init__(self, *question_keys, enabled=True, conclusion=None):
        self.question_keys = question_keys
        self.enabled = enabled
        self.conclusion = conclusion

    def __repr__(self):
        return f"Or({self.questions}...)"


Operation = typing.Union[And, Or]


class OperationFunctor:
    """
    An abstract visitor defined over Logic Operation.
    Defines the default dispatch over expressions, and
    implements memoization.
    """

    def __init__(self):
        self.memo_map = {}

    # pylint: disable=no-else-return
    async def visit(self, expr: Operation):
        """Apply the visitor to an expression."""
        if expr in self.memo_map:
            return self.memo_map[expr]

        if isinstance(expr, And):
            res = await self.visit_and(expr)
        elif isinstance(expr, Or):
            res = await self.visit_or(expr)
        else:
            raise Exception(f"warning unhandled case: {type(expr)}")

        self.memo_map[expr] = res

        return res

    async def visit_and(self, _: And):
        raise NotImplementedError()

    async def visit_or(self, _: Or):
        raise NotImplementedError()


class RuleComputeVisitor(OperationFunctor):
    def __init__(self, _question_env):
        self._question_env = _question_env
        super().__init__()

    async def visit_and(self, _and: And):
        ans = True
        for question_key, question in tuple(_and.questions.items()):
            logger.debug(question)
            if question.op == "eq":
                _res = self._question_env[question_key] == question.value
            elif question.op == "gt":
                _res = self._question_env[question_key] > question.value
            elif question.op == "lt":
                _res = self._question_env[question_key] < question.value
            elif question.op in ["run/scene", "run/cron"]:
                _res = self._question_env[question_key] is True
                logger.debug(_res)
            else:
                _res = False
            ans = ans and _res
        if ans:
            # logger.debug(self.conclusion)
            for conclusion in _and.conclusion:
                ee.emit(conclusion.topic, conclusion)
            for question_key, should_value in tuple(_and.questions.items()):
                self._question_env[question_key] = None

    async def visit_or(self, _or: Or):
        ans = False
        for question_key, question in tuple(_or.questions.items()):
            logger.debug(question)
            if question.op == "eq":
                _res = self._question_env[question_key] == question.value
            elif question.op == "gt":
                _res = self._question_env[question_key] > question.value
            elif question.op == "lt":
                _res = self._question_env[question_key] < question.value
            elif question.op in ["run/scene", "run/cron"]:
                _res = self._question_env[question_key] is True
            else:
                _res = False
            ans = ans or _res
        if ans:
            for conclusion in _or.conclusion:
                ee.emit(conclusion.topic, conclusion)
            for question_key, should_value in tuple(_or.questions.items()):
                self._question_env[question_key] = None


def generate_question_id(topic: str, property_name: str):
    topic_words = topic.split("/")
    return f"things_{topic_words[1]}_{property_name}"


def generate_scenes_id(topic: str):
    topic_words = topic.split("/")
    return f"scenes_{topic_words[1]}"


def generate_cron_id(topic: str):
    return f"cron/{uuid.uuid4().hex}"


def generate_rule_id(topic: str, property_name: str, property_value: typing.Any):
    topic_words = topic.split("/")
    return f"things_{topic_words[1]}_{property_name}_{property_value}"


class RuleEngine:
    def __init__(self):
        self.question_env = {}

        # "things_xxxx_state_on": {
        #     "xxxx": And({"things_xxxx_state": {"op": "eq", "value": "ON"},
        #                  "things_xxxx_brightness": {"op": "lt", "value": 100}}, enabled=True)
        # },
        self.rule_env = {}

    def __repr__(self):
        return f"RuleEngine({self.question_env}...)"

    def update_question_env(self, question_key: str, value: typing.Any):
        self.question_env[question_key] = value

    async def compute_rule(self, msg: OutMsg):
        if msg.messageType == "propertyStatus":
            for property_name, value in msg.data.items():
                rule_id = generate_rule_id(msg.topic, property_name, value)
                question_id = generate_question_id(msg.topic, property_name)
                self.update_question_env(question_id, value)
                for rule_id, rule in tuple(self.rule_env.get(rule_id, {}).items()):
                    logger.info(f"compute rule: key {rule_id} enabled {rule.enabled}")
                    if rule.enabled:
                        await RuleComputeVisitor(self.question_env).visit(rule)

        if msg.messageType == "sceneStatus":
            rule_id = generate_scenes_id(msg.topic)
            question_id = generate_scenes_id(msg.topic)
            self.update_question_env(question_id, True)
            for rule_id, rule in tuple(self.rule_env.get(rule_id, {}).items()):
                logger.info(f"compute rule: key {rule_id} enabled {rule.enabled}")
                if rule.enabled:
                    await RuleComputeVisitor(self.question_env).visit(rule)

        if msg.messageType == "cronStatus":
            rule_id = msg.topic
            question_id = msg.topic
            logger.debug(question_id)
            self.update_question_env(question_id, True)
            logger.debug(self.rule_env)
            logger.debug(self.question_env)
            logger.debug(tuple(self.rule_env.get(rule_id, {}).items()))
            for rule_id, rule in tuple(self.rule_env.get(rule_id, {}).items()):
                logger.info(f"compute rule: key {rule_id} enabled {rule.enabled}")
                if rule.enabled:
                    await RuleComputeVisitor(self.question_env).visit(rule)

    async def load_rules(self, rules: typing.List[typing.Optional[Rule]]):
        for rule in rules:
            await self.load_rule(rule)
        logger.info(f"load question env: {self.question_env}")
        logger.info(f"load rule env: {self.rule_env}")

    async def load_rule(self, rule: Rule):
        questions = {}
        cron_keys = {}
        # 更新 questions，以及当前 rule 需要查询的 question_keys
        for pre in rule.premise:
            try:
                if "things" in pre.topic:
                    question_key = generate_question_id(pre.topic, pre.name)
                    question = Question(**{"op": pre.op, "value": pre.value})
                    questions.update({question_key: question})
                    self.update_question_env(question_key, None)
                elif "scenes" in pre.topic:
                    question_key = generate_scenes_id(pre.topic)
                    question = Question(**{"op": "run/scene"})
                    questions.update({question_key: question})
                    self.update_question_env(question_key, None)
                elif "cron" in pre.topic:
                    question_key = generate_cron_id(pre.topic)
                    cron_keys.update({rule.id: question_key})
                    question = Question(**{"op": "run/cron"})
                    questions.update({question_key: question})
                    self.update_question_env(question_key, None)

                    async def post2re():
                        print(question_key)
                        message = {
                            "topic": question_key,
                            "messageType": "cronStatus",
                            "data": {}
                        }
                        from .schema import InputMsg, OutMsg
                        message = OutMsg(**message)
                        ee.emit(f"{question_key}/state", message)
                    if pre.messageType == "everyday":
                        job = CronJob(name=question_key).every().day.at("11:22").go(post2re)
                        msh.add_job(job)
                    elif pre.messageType == "interval":
                        job = CronJob(name=question_key).every(
                            pre.data.get("second")).second.go(post2re)
                        msh.add_job(job)
                    elif pre.messageType == "date":
                        job = CronJob(name=question_key, tolerance=100).at("2019-01-15 16:12").go(post2re)
                        msh.add_job(job)
                    elif pre.messageType == "weekday":
                        time = pre.data.get("time")
                        logger.debug(time)
                        for i in range(0, 5):
                            job = CronJob(name=question_key).weekday(i).at(time).go(post2re)
                            msh.add_job(job)
                    elif pre.messageType == "weekend":
                        time = pre.data.get("time")
                        for i in range(5, 7):
                            job = CronJob(name=question_key).weekday(i).at(time).go(post2re)
                            msh.add_job(job)
                    ee.on(f"{question_key}/state", self.compute_rule)
                else:
                    raise Exception("不会执行这里")
            except ValidationError as e:
                logger.error(str(e))

        for pre in rule.premise:
            if "things" in pre.topic:
                rule_id = generate_rule_id(pre.topic, pre.name, pre.value)
            elif "scenes" in pre.topic:
                rule_id = generate_scenes_id(pre.topic)
            elif "cron" in pre.topic:
                rule_id = cron_keys.get(rule.id)
            rule_id_map = self.rule_env.get(rule_id, {})
            logger.debug(rule_id_map)
            if rule.premise_type in ["And", "Singleton"]:
                rule_id_map.update({
                    rule.id: And(questions, enabled=rule.enabled, conclusion=rule.conclusion)
                })
            elif rule.premise_type == "Or":
                rule_id_map.update({
                    rule.id: Or(questions, enabled=rule.enabled, conclusion=rule.conclusion)
                })
            logger.info(f"add rule: key {rule_id}")
            logger.debug({
                rule_id: rule_id_map
            })
            self.rule_env.update({
                rule_id: rule_id_map
            })
            logger.debug(self.rule_env)
            if "things" in pre.topic or "scenes" in pre.topic:
                ee.on(f"{pre.topic}/state", self.compute_rule)
        logger.info(f"load rule env: {self.rule_env}")

    async def disable_rule(self, rule_key, rule_db_id):
        logger.info(self.rule_env)
        logger.debug(rule_key)
        rule_bind = self.rule_env.get(rule_key)
        if rule_bind:
            if rule_bind.get(rule_db_id):
                del rule_bind[rule_db_id]
        logger.info(self.rule_env)

# logger.info(f"load question env: {question_env}")
# logger.info(f"load rule env: {rule_env}")

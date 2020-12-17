import typing

from enum import Enum

from async_cron.job import CronJob

from loguru import logger
from pydantic import (
    BaseModel, constr, ValidationError,
    StrictInt, StrictBool, StrictFloat, StrictStr
)

from .toolkits.event_bus import ee
from .toolkits.scheduler import Scheduler
from .schema import OutMsg, Question

msh = Scheduler(locale="zh_CN")


class PremiseType(str, Enum):
    _singleton: str = "Singleton"
    _and: str = "And"
    _or: str = "Or"


class ThingPremiseMessageType(str, Enum):
    property_status = 'propertyStatus'
    action_status = 'actionStatus'


class ThingPremise(BaseModel):
    topic: constr(regex=r'^things\/[0-9a-zA-Z\_\-\:]+$')
    messageType: ThingPremiseMessageType
    name: str
    op: str
    value: typing.Union[StrictInt, StrictBool, StrictFloat, StrictStr]


class ScenePremise(BaseModel):
    topic: constr(regex=r'^scenes\/[0-9a-zA-Z\_\-\:]+$')
    messageType: str = 'sceneStatus'
    data: typing.Dict[str, typing.Any]


class CronPremise(BaseModel):
    topic: constr(regex=r'^cron\/[0-9a-zA-Z\_\-\:]+$')
    messageType: str = 'cronStatus'
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


class Operation:
    def __init__(self,
                 questions: typing.Dict[str, Question],
                 enabled=True,
                 conclusion=None):
        self.questions = questions
        self.enabled = enabled
        self.conclusion = conclusion


class And(Operation):

    def __repr__(self):
        return f"And({self.questions}...)"


class Or(Operation):

    def __repr__(self):
        return f"Or({self.questions}...)"


class OperationFunctor:
    """
    An abstract visitor defined over Logic Operation.
    Defines the default dispatch over expressions, and
    implements memoization.
    """

    def __init__(self):
        self.memo_map = {}

    # pylint: disable=no-else-return
    async def visit(self, expr: Operation) -> bool:
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

    async def visit_and(self, _: And) -> bool:
        raise NotImplementedError()

    async def visit_or(self, _: Or) -> bool:
        raise NotImplementedError()


class RuleComputeVisitor(OperationFunctor):

    def compute_question(self, question_key: str, question: Question) -> bool:
        logger.debug(f"{question_env[question_key]} {question.value}")
        if question.op == "eq":
            res = question_env[question_key] == question.value
        elif question.op == "gt":
            res = question_env[question_key] > question.value
        elif question.op == "lt":
            res = question_env[question_key] < question.value
        elif question.op in ["run/scene", "run/cron"]:
            res = question_env[question_key] is True
            logger.debug(res)
        else:
            res = False
        return res

    async def run_conclusion(self, _operation: Operation) -> None:
        for conclusion in _operation.conclusion:
            logger.debug(conclusion.topic)
            ee.emit(conclusion.topic, conclusion)
        for question_key, should_value in tuple(_operation.questions.items()):
            question_env[question_key] = None

    async def visit_and(self, _and: And) -> bool:
        ans = True
        for question_key, question in tuple(_and.questions.items()):
            logger.debug(f"Question: {question}")
            res = self.compute_question(question_key, question)
            ans = ans and res
        logger.debug(ans)
        if ans:
            logger.debug(_and.conclusion)
            await self.run_conclusion(_and)

    async def visit_or(self, _or: Or) -> bool:
        ans = False
        for question_key, question in tuple(_or.questions.items()):
            logger.debug(f"Question: {question}")
            res = self.compute_question(question_key, question)
            ans = ans or res
        if ans:
            await self.run_conclusion(_or)


def generate_question_id(topic: str, property_name: str) -> bool:
    topic_words = topic.split("/")
    return f"things_{topic_words[1]}_{property_name}"


def generate_scenes_id(topic: str) -> bool:
    topic_words = topic.split("/")
    return f"scenes_{topic_words[1]}"


def generate_cron_id(rule_id, messageType, time) -> bool:
    return f"cron_{rule_id}_{messageType}_{time}"


def generate_rule_id(topic: str, property_name: str, property_value: typing.Any) -> bool:
    topic_words = topic.split("/")
    return f"things_{topic_words[1]}_{property_name}_{property_value}"


async def report_cron_status(question_key) -> None:
    message = {
        "topic": question_key,
        "messageType": "cronStatus",
        "data": {}
    }

    message = OutMsg(**message)
    ee.emit(f"{question_key}/state", message)


question_env = {}


class RuleEngine:
    def __init__(self):

        # "things_xxxx_state_on": {
        #     "xxxx": And({"things_xxxx_state": {"op": "eq", "value": "ON"},
        #                  "things_xxxx_brightness": {"op": "lt", "value": 100}}, enabled=True)
        # },
        self.rule_env = {}

    def update_question_env(self, question_key: str, value: typing.Any):
        question_env[question_key] = value

    async def add_cron_job(self, pre, question_key):
        if pre.messageType == "everyday":
            time = pre.data.get("time")
            time_array = time.split(":")
            time = f"{time_array[0]}:{time_array[1]}"
            job = CronJob(name=question_key).every().day.at(time).go(report_cron_status, question_key)
            msh.add_job(job)
        elif pre.messageType == "interval":
            job = CronJob(name=question_key).every(
                pre.data.get("second")).second.go(report_cron_status, question_key)
            msh.add_job(job)
        elif pre.messageType == "date":
            job = CronJob(name=question_key, tolerance=100).at("2019-01-15 16:12").go(report_cron_status, question_key)
            msh.add_job(job)
        elif pre.messageType == "weekday":
            time = pre.data.get("time")
            time_array = time.split(":")
            time = f"{time_array[0]}:{time_array[1]}"
            logger.debug(time)
            for i in range(0, 5):
                job = CronJob(name=question_key).weekday(i).at(time).go(report_cron_status, question_key)
                msh.add_job(job)
        elif pre.messageType == "weekend":
            time = pre.data.get("time")
            time_array = time.split(":")
            time = f"{time_array[0]}:{time_array[1]}"
            for i in range(5, 7):
                job = CronJob(name=question_key).weekday(i).at(time).go(report_cron_status, question_key)
                msh.add_job(job)
        elif pre.messageType == "custom":
            dates = pre.data.get("date")
            time = pre.data.get("time")
            time_array = time.split(":")
            time = f"{time_array[0]}:{time_array[1]}"
            for i in dates:
                job = CronJob(name=question_key).weekday(i).at(time).go(report_cron_status, question_key)
                msh.add_job(job)
        ee.on(f"{question_key}/state", self.handle_status)

    async def compute_rule(self, rule_id):
        for rule_pk, rule in tuple(self.rule_env.get(rule_id, {}).items()):
            logger.debug(f"compute rule: key {rule_pk} enabled {rule.enabled}")
            if rule.enabled:
                await RuleComputeVisitor().visit(rule)

    async def handle_status(self, msg: OutMsg):
        assert isinstance(msg, OutMsg)

        if msg.messageType == "propertyStatus":
            for property_name, value in msg.data.items():
                rule_id = generate_rule_id(msg.topic, property_name, value)
                question_key = generate_question_id(msg.topic, property_name)
                self.update_question_env(question_key, value)
                # logger.debug(question_env)
                await self.compute_rule(rule_id)

        if msg.messageType == "sceneStatus":
            rule_id = generate_scenes_id(msg.topic)
            question_key = generate_scenes_id(msg.topic)
            self.update_question_env(question_key, True)
            await self.compute_rule(rule_id)

        if msg.messageType == "cronStatus":
            rule_id = msg.topic
            question_key = msg.topic
            self.update_question_env(question_key, True)
            # logger.debug(question_env)
            await self.compute_rule(rule_id)

    async def load_rules(self, rules: typing.List[typing.Optional[Rule]]):
        for rule in rules:
            await self.load_rule(rule)
        logger.info(f"load question env: {self.question_env}")
        logger.info(f"load rule env: {self.rule_env}")

    async def preload(self, pre: typing.Union[ThingPremise, ScenePremise, CronPremise], rule_id: str):
        if "things" in pre.topic:
            topic_words = pre.topic.split("/")
            return f"things_{topic_words[1]}_{pre.name}", {"op": pre.op, "value": pre.value}
        elif "scenes" in pre.topic:
            topic_words = pre.topic.split("/")
            return f"scenes_{topic_words[1]}", {"op": "run/scene"}
        elif "cron" in pre.topic:
            question_key = f"cron_{rule_id}_{pre.messageType}_{pre.data.get('time')}"
            await self.add_cron_job(pre, question_key=question_key)
            return question_key, {"op": "run/cron"}
        else:
            raise Exception("不会执行这一条")

    def generate_rule_id(self, pre: typing.Union[ThingPremise, ScenePremise, CronPremise], rule_id: str):
        if "things" in pre.topic:
            topic_words = pre.topic.split("/")
            return f"things_{topic_words[1]}_{pre.name}_{pre.value}"
        elif "scenes" in pre.topic:
            topic_words = pre.topic.split("/")
            return f"scenes_{topic_words[1]}"
        elif "cron" in pre.topic:
            return f"cron_{rule_id}_{pre.messageType}_{pre.data.get('time')}"

    async def load_rule(self, rule: Rule):
        assert isinstance(rule, Rule)
        questions = {}
        # 更新 questions，以及当前 rule 需要查询的 question_keys
        for pre in rule.premise:
            question_key, question_data = await self.preload(pre, rule.id)
            question = Question(**question_data)
            questions.update({question_key: question})
            self.update_question_env(question_key, None)

        for pre in rule.premise:
            rule_pk = rule.id
            rule_id = self.generate_rule_id(pre, rule_pk)
            rule_map = self.rule_env.get(rule_id, {})
            logger.debug(rule_map)
            if rule.premise_type in ["And", "Singleton"]:
                rule_map.update({
                    rule_pk: And(questions, enabled=rule.enabled, conclusion=rule.conclusion)
                })
            elif rule.premise_type == "Or":
                rule_map.update({
                    rule_pk: Or(questions, enabled=rule.enabled, conclusion=rule.conclusion)
                })
            logger.info(f"add rule: key {rule_id}")
            logger.debug({
                rule_id: rule_map
            })
            self.rule_env.update({
                rule_id: rule_map
            })
            logger.debug(self.rule_env)
            if "things" in pre.topic or "scenes" in pre.topic:
                ee.on(f"{pre.topic}/state", self.handle_status)
        logger.info(f"load rule env: {self.rule_env}")

    async def disable_rule(self, pre, rule):
        # logger.info(self.rule_env)
        rule_pk = rule.id.hex
        rule_id = self.generate_rule_id(pre, rule_pk)
        # if "things" in pre.topic:
        #     rule_id = generate_rule_id(pre.topic, pre.name, pre.value)
        # elif "scenes" in pre.topic:
        #     rule_id = generate_scenes_id(pre.topic)
        # elif "cron" in pre.topic:
        #     logger.debug(f"cron keys {self.cron_keys}")
        #     logger.debug(rule.id.hex)
        #     rule_id = self.cron_keys.get(rule.id.hex)
        logger.debug(f"disable rule {rule_id}")
        rule_map = self.rule_env.get(rule_id)
        if rule_map:
            if rule_map.get(rule_pk):
                del rule_map[rule_pk]
        msh.del_job(rule_id)
        # logger.info(self.rule_env)

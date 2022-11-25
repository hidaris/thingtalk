import os
import uuid
import typing

from loguru import logger
from pydantic import ValidationError

from fastapi import Depends, APIRouter
from fastapi.exceptions import HTTPException
from fastapi.responses import ORJSONResponse

from tinydb import TinyDB, Query

from ..rule_engine import RuleEngine, RuleInput, Rule

router = APIRouter()


data_ref = os.environ.get("TINY_DB", '/data/db.json')
# data_ref = os.environ.get("TINY_DB", '/tmp/db.json')
db = TinyDB(data_ref)

table = db.table("rules")
re = RuleEngine()


@router.post("/rules/bulk")
async def create_rules(rules: typing.List[typing.Optional[RuleInput]]):
    for rule in rules:
        rule_data = rule.dict()
        rule_data.update({"id": str(uuid.uuid4())})
        table.insert(rule_data)
        await re.load_rule(rule_data)

    data = table.all()

    return ORJSONResponse({"rules": data})


@router.get("/rules")
async def get_rules():
    data = table.all()
    return ORJSONResponse({"rules": data})


@router.post("/rules")
async def create_rule(rule: RuleInput):
    rule_data = rule.dict()
    rule_data.update({"id": str(uuid.uuid4())})
    try:
        logger.debug(rule_data)
        rule = Rule(**rule_data)
        table.insert(rule_data)
        await re.load_rule(rule)
    except ValidationError as e:
        logger.error(str(e))
        return ORJSONResponse(e.json(), status_code=422)

    return ORJSONResponse(rule_data)


@router.put("/rules/{rule_id}")
async def update_rule(rule_id: str, rule_data: dict):
    RuleModel = Query()
    rule = table.get(RuleModel.id == rule_id)

    if rule:
        for pre in rule.get("premise"):
            await re.disable_rule(f"things_{pre.get('topic').split('/')[1]}_{pre.get('name')}_{pre.get('value')}", rule_id)

    doc_ids = table.update(rule_data, RuleModel.id == rule_id)
    if doc_ids:
        rule = table.get(RuleModel.id == rule_id)
        try:
            rule = Rule(**rule)
            await re.load_rule(rule)
        except ValidationError as e:
            logger.error(str(e))

    return ORJSONResponse(rule.dict())


@router.delete("/rules/{rule_id}")
async def delete_rule(rule_id: str):
    RuleModel = Query()
    rule = table.get(RuleModel.id == rule_id)
    if rule:
        for pre in rule.get("premise"):
            await re.disable_rule(f"things_{pre.get('topic').split('/')[1]}_{pre.get('name')}_{pre.get('value')}", rule_id)
        table.remove(RuleModel.id == rule_id)

    return ORJSONResponse({"msg": "success"})

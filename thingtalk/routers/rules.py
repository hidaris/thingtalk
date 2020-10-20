import uuid
import typing

from enum import Enum

from fastapi import Depends, APIRouter
from fastapi.exceptions import HTTPException
from fastapi.responses import UJSONResponse

from pydantic import BaseModel
from tinydb import TinyDB, Query

from ..rule_engine import load_rule, disable_rule

router = APIRouter()


db = TinyDB('/tmp/db.json')

table = db.table("rules")


class PremiseType(str, Enum):
    psingleton: str = "Singleton"
    pand: str = "And"
    por: str = "Or"


class Rule(BaseModel):
    enabled: bool
    name: str
    premise_type: PremiseType
    premise: typing.List[typing.Dict[str, typing.Union[str, dict]]]
    conclusion: typing.List[typing.Dict[str, typing.Union[str, dict]]]


@router.post("/rules/bulk")
async def create_rules(rules: typing.List[typing.Optional[Rule]]):
    for rule in rules:
        rule_data = rule.dict()
        rule_data.update({"id": str(uuid.uuid4())})
        table.insert(rule_data)
        await load_rule(rule_data)

    data = table.all()

    return UJSONResponse({"rules": data})


@router.post("/rules")
async def create_rule(rule: Rule):
    rule_data = rule.dict()
    rule_data.update({"id": str(uuid.uuid4())})
    table.insert(rule_data)
    await load_rule(rule_data)

    return UJSONResponse(rule_data)


@router.delete("/rules/{rule_id}")
async def delete_rule(rule_id: str):
    RuleModel = Query()
    rule = table.get(RuleModel.id == rule_id)
    if rule:
        for pre in rule.get("premise"):
            await disable_rule(f"things_{pre.get('thing_id')}_{pre.get('name')}_{pre.get('value')}", rule_id)
        table.remove(RuleModel.id == rule_id)

    return UJSONResponse({"msg": "success"})


@router.get("/rules")
async def get_rules():
    data = table.all()
    return UJSONResponse({"rules": data})

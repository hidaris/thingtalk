import pytest

from pydantic import ValidationError

from ..thingtalk.rule_engine import (
    RuleEngine, Rule, And, Conclusion, Question
)
from ..thingtalk.toolkits.event_bus import ee
from ..thingtalk.schema import OutMsg

re = RuleEngine()


@pytest.mark.asyncio
async def test_load_rule():
    rule = {"enabled": True,
            "name": "规则 2020/11/13 11:33",
            "premise_type": "Singleton",
            "premise": [
                {"topic": "things/0x00158d0005483fc1", "messageType": "propertyStatus", "name": "action", "op": "eq",
                 "value": "shake"}],
            "conclusion": [
                {"topic": "things/urn:thingtalk:broadcast:light", "messageType": "requestAction",
                 "data": {"random_rgb": {"input": {}}}}],
            "id": "0687b69d-ea9d-403d-87d7-7fe213ad8640"}

    try:
        rule = Rule(**rule)
        await re.load_rule(rule)
        assert re.question_env == {"things_0x00158d0005483fc1_action": None}
        assert re.rule_env == {
            "things_0x00158d0005483fc1_action_shake": {
                "0687b69d-ea9d-403d-87d7-7fe213ad8640": And(
                    Question(**{"things_0x00158d0005483fc1_action": {"op": "eq", "value": "shake"}}),
                    enabled=True,
                    conclusion=[
                        Conclusion(**{"topic": "things/urn:thingtalk:broadcast:light", "messageType": "requestAction",
                                      "data": {"random_rgb": {"input": {}}}})]),
            }
        }
    except ValidationError as e:
        pass


@pytest.mark.asyncio
async def test_compute_rule():
    msg = {
        "topic": "things/0x00158d0005483fc1",
        "messageType": "propertyStatus",
        "data": {
            "action": "shake"
        }
    }
    assert ee.listeners("things/0x00158d0005483fc1/state") == [re.compute_rule]
    try:
        msg = OutMsg(**msg)
        ee.emit("things/0x00158d0005483fc1/state", msg)
    except ValidationError as e:
        pass
    await re.compute_rule(msg)
    assert re.question_env == {"things_0x00158d0005483fc1_action": "shake"}

import uuid
import time

from webthing import Thing, Action, background_thread_loop, WebThingServer
import openadk
from openadk.rest import ApiException
from pprint import pprint

configuration = openadk.Configuration()
configuration.host = 'http://10.1.1.87:9090/v1'


class Motions(Action):
    name = "motions"

    async def perform_action(self):
        # create an instance of the API class
        api_instance = openadk.MotionsApi(openadk.ApiClient(configuration))
        if self.input["name"] == "raise":
            motion = openadk.MotionsParameter(name=self.input["name"], direction='both')
        else:
            motion = openadk.MotionsParameter(name=self.input["name"])
        timestamp = int(time.time())
        body = openadk.MotionsOperation(motion=motion,
                                        timestamp=timestamp)  # MotionsOperation | Motion control parameters
        try:
            # Update the motions
            api_response = api_instance.put_motions(body)
            pprint(api_response)
        except ApiException as e:
            print("Exception when calling MotionsApi->put_motions: %s\n" % e)


class YanShee(Thing):
    type = []
    description = "YanShee Robot Web Thing"

    def __init__(self):
        super().__init__(uuid.uuid4().hex, "yanshee robot")

    async def build(self):
        await self.add_available_action(
            {
                "title": "set_motion",
                "description": "切换运动状态",
                "input": {
                    "type": "object",
                    "required": ["name", ],
                    "properties": {
                        "name": {"type": "string", "enum": ['ShootRight',
                                                            'WakaWaka',
                                                            'GetUp',
                                                            'ResetWithoutHead',
                                                            'GetupRear',
                                                            'TurnLeft',
                                                            'CombinationOfSongs',
                                                            'Stop',
                                                            'SiegeOfTroy',
                                                            'Reset',
                                                            'LeftHit',
                                                            'LeftAlt',
                                                            'GoalKeeper2',
                                                            'LeftTackle',
                                                            'OneStepForward',
                                                            'GoalKeeper1',
                                                            'WakaWakaX4',
                                                            'OneStepMoveRight',
                                                            'TurnLeftSlowly',
                                                            'SorrySorry',
                                                            'PushUp',
                                                            'Forward',
                                                            'StraightRight',
                                                            'OneStepMoveLeft',
                                                            'GangnamStyle',
                                                            'TurnRightSlowly',
                                                            'OneStepTurnRight',
                                                            'Calibration',
                                                            'RightTackle',
                                                            'Rightward',
                                                            'Leftward',
                                                            'ActionAging1',
                                                            'SweetAndSour',
                                                            'HappyBirthday',
                                                            'LittleApple',
                                                            'Shutdown',
                                                            'LeftSidePunch',
                                                            'WeAreTakingOff',
                                                            'LeftHitForward',
                                                            'Backward',
                                                            'RightHitForward',
                                                            'OneStepTurnLeft',
                                                            'OneStepBackward',
                                                            'GetupFront',
                                                            'Victory',
                                                            'StraightLeft',
                                                            'TurnRight',
                                                            'ActionAging',
                                                            'RightSidePunch',
                                                            'RightHit',
                                                            'ShootLeft',
                                                            'Hug',
                                                            'raise', 'crouch', 'stretch', 'come',
                                                            'on', 'wave', 'bend', 'walk', 'turn',
                                                            'around', 'head', 'bow'
                                                            ], },
                    },
                },
            },
            Motions,
        )

        return self


with background_thread_loop() as loop:
    app = WebThingServer(loop, YanShee).create()

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


class PutVoices(Action):
    name = "txt2speech"

    async def perform_action(self):
        # create an instance of the API class
        api_instance = openadk.VoiceApi(openadk.ApiClient(configuration))
        timestamp = int(time.time())
        body = openadk.VoiceTTSStr(tts=self.input["text"], timestamp=timestamp)  # VoiceTTSStr |
        try:
            # Update the motions
            api_response = api_instance.put_voice_tts(body)
            pprint(api_response)
        except ApiException as e:
            print("Exception when calling MotionsApi->put_motions: %s\n" % e)


class AutoTransform(Action):
    name = "auto_transform"

    async def perform_action(self):
        # create an instance of the API class
        api_instance = openadk.VoiceApi(openadk.ApiClient(configuration))
        body = openadk.VoiceIatRequest()  # VoiceIatRequest |  (optional)

        try:
            # Start auto transform
            api_response = api_instance.put_voice_iat(body=body)
            pprint(api_response)
            import asyncio
            await asyncio.sleep(4)
            api_response = api_instance.get_voice_iat()
            pprint(api_response)
            import ujson as json
            new_res = api_response.data.replace("\x00", "")
            n = json.loads(new_res)
            cmd = ""
            for i in n['text']['ws']:
                cmd += i['cw'][0]['w']
            await self.thing.set_property("cmd", cmd)
            import httpx
            async with httpx.AsyncClient() as c:
                if "开" in cmd and "灯" in cmd:
                    state = True
                    timestamp = int(time.time())
                    body = openadk.VoiceTTSStr(tts="正在为您打开灯", timestamp=timestamp)  # VoiceTTSStr |
                    # Update the motions
                    api_response = api_instance.put_voice_tts(body)
                    pprint(api_response)
                if "关" in cmd and "灯" in cmd:
                    state = False
                    timestamp = int(time.time())
                    body = openadk.VoiceTTSStr(tts="正在为您关闭灯", timestamp=timestamp)  # VoiceTTSStr |
                    # Update the motions
                    api_response = api_instance.put_voice_tts(body)
                    pprint(api_response)
                await c.put("http://127.0.0.1:5000/things/0x00158d0003fa5646/properties/state", json={'state': state})

        except ApiException as e:
            print("Exception when calling VoiceApi->put_voice_iat: %s\n" % e)


class YanShee(Thing):

    type = []
    description = "YanShee Robot Web Thing"

    def __init__(self):
        super().__init__(uuid.uuid4().hex, "yanshee robot")
        # create an instance of the API class
        api_instance = openadk.VisionsApi(openadk.ApiClient(configuration))
        body = openadk.VisionsStream()  # VisionsStream |  (optional)
        body2 = openadk.VisionsPhoto()  # VisionsPhoto | Photo resolution (optional)

        try:
            # Turn on the web stream for the camera
            api_response = api_instance.post_visions_streams(body=body)
            # api_response2 = api_instance.post_vision_photo(body=body2)
            pprint(api_response)
        except ApiException as e:
            print("Exception when calling VisionsApi->post_visions_streams: %s\n" % e)

    async def build(self):
        from webthing import Property, Value
        p = Property(
                "video",
                Value(""),
                metadata={
                    "@type": "VideoProperty",
                    "title": "设备视频流",
                    "type": "null",
                    "description": "[机器人]设备视频流",
                },
            )
        await p.set_media_type("video/mp4")
        await p.set_href("http://10.1.1.87:8000")
        await self.add_property(p)

        await self.add_property(Property(
            "cmd",
            Value(""),
            metadata={
                "@type": "StateProperty",
                "title": "设备控制",
                "type": "string",
                "description": "[灯泡]设备控制",
            },
        ))

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

        await self.add_available_action({
            "title": "txt2speech",
            "description": "文字转语音",
            "input": {
                "type": "object",
                "required": ["text", ],
                "properties": {
                    "text": {"type": "string"},
                },
            }},
            PutVoices)

        await self.add_available_action({
            "title": "auto_transform",
            "description": "语音识别",
            "input": {
                "type": "object",
                "required": [],
                "properties": {
                },
            }},
            AutoTransform)

        return self


with background_thread_loop() as loop:
    app = WebThingServer(loop, YanShee).create()

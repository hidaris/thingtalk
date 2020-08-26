"""Starts a fake fan, lightbulb, garage door and a TemperatureSensor
"""
import logging
import signal
import random
import socket
import asyncio
import httpx
import websockets
import ujson as json

from fnvhash import fnv1a_32
from rgbxy import Converter
from pyhap.accessory import Accessory, Bridge
from pyhap.accessory_driver import AccessoryDriver
from pyhap.const import (CATEGORY_FAN,
                         CATEGORY_LIGHTBULB,
                         CATEGORY_GARAGE_DOOR_OPENER,
                         CATEGORY_SENSOR,
                         CATEGORY_SWITCH,
                         CATEGORY_WINDOW_COVERING)

logging.basicConfig(level=logging.INFO, format="[%(module)s] %(message)s")


class WebthingAccessory(Accessory):

    async def run(self):
        """Called when the Accessory should start doing its thing.
        Called when HAP server is running, advertising is set, etc.
        Can be overridden with a normal or async method.
        """

        uri = f"ws://127.0.0.1:8000/things/{self.thing_id}"
        print(f"{self.category}:{self.thing_id}")
        self.sleep_time = 5
        while True:
            # outer loop restarted every time the connection fails
            print(f"Creating new connection to {uri}")
            try:
                async with websockets.connect(uri) as ws:
                    while True:
                        try:
                            rep = await ws.recv()
                        except websockets.exceptions.ConnectionClosed:
                            print(f"Ping error - retrying connection in {self.sleep_time} sec (Ctrl-C to quit)")
                            await asyncio.sleep(self.sleep_time)
                            break
                        recv_data = json.loads(rep)
                        if recv_data.get("messageType") == "propertyStatus":
                            value = recv_data.get("data")
                            if value.get('contact') is not None and hasattr(self, 'char_contact'):
                                self.char_contact.set_value(value.get('contact'))

                            if value.get('temperature') and hasattr(self, 'char_temp'):
                                self.char_temp.set_value(value.get('temperature'))

                            if value.get('state') is not None and hasattr(self, 'char_on'):
                                self.char_on.set_value(True if value.get('state') == 1 else False)
                            if value.get('brightness') and hasattr(self, 'char_brightness'):
                                self.char_brightness.set_value(int((value.get('brightness') / 254) * 100))
                            if value.get('color') and hasattr(self, 'char_brightness') and hasattr(self, 'char_saturation'):
                                x = value.get('color').get('x')
                                y = value.get('color').get('y')
                                converter = Converter()
                                print(value)
                                rgb = converter.xy_to_rgb(x, y, value.get('brightness'))
                                import colorsys
                                hsv = colorsys.rgb_to_hsv(rgb[0], rgb[1], rgb[2])
                                self.char_on.set_value(hsv[0]*60)
                                self.char_saturation.set_value(hsv[1]*100)
                                self.char_brightness.set_value(hsv[2]*100)

                            print(f"data push from ws:{value}")
            except socket.gaierror:
                print(
                    f"Socket error - retrying connection in {self.sleep_time} sec (Ctrl-C to quit)")
                await asyncio.sleep(self.sleep_time)
                continue
            except (websockets.exceptions.InvalidStatusCode, ConnectionRefusedError):
                print('Nobody seems to listen to this endpoint. Please check the URL.')
                print(f"Retrying connection in {self.sleep_time} sec (Ctrl-C to quit)")
                await asyncio.sleep(self.sleep_time)
                continue


class ContactSensor(WebthingAccessory):
    """Webthing ContactSensor, measuring every 3 seconds."""

    category = CATEGORY_SENSOR

    def __init__(self, *args, **kwargs):
        super().__init__(*args, aid=kwargs.get('aid'))

        self.thing_id = kwargs.get('thing_id')
        serv_temp = self.add_preload_service('ContactSensor', chars=['ContactSensorState'])
        self.char_contact = serv_temp.configure_char('ContactSensorState')


class Switch(WebthingAccessory):
    """Webthing ContactSensor, measuring every 3 seconds."""

    category = CATEGORY_SWITCH

    def __init__(self, *args, **kwargs):
        super().__init__(*args, aid=kwargs.get('aid'))

        self.thing_id = kwargs.get('thing_id')
        serv_switch = self.add_preload_service('Switch', chars=['On'])
        self.char_on = serv_switch.configure_char(
            'On', setter_callback=self.set_bulb_on)

    def set_bulb_on(self, value):
        logging.info("Bulb value: %s", value)
        value = True if value == 1 else False
        httpx.put(f"http://127.0.0.1:8000/things/{self.thing_id}/properties/state", json={"state": value})


class TemperatureSensor(WebthingAccessory):
    """Webthing Temperature sensor, measuring every 3 seconds."""

    category = CATEGORY_SENSOR

    def __init__(self, *args, **kwargs):
        super().__init__(*args, aid=kwargs.get('aid'))

        self.thing_id = kwargs.get('thing_id')
        serv_temp = self.add_preload_service('TemperatureSensor')
        self.char_temp = serv_temp.configure_char('CurrentTemperature')


class FakeFan(WebthingAccessory):
    """Webthing Fan, only logs whatever the client set."""

    category = CATEGORY_FAN

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Add the fan service. Also add optional characteristics to it.
        serv_fan = self.add_preload_service(
            'Fan', chars=['RotationSpeed', 'RotationDirection'])

        self.char_rotation_speed = serv_fan.configure_char(
            'RotationSpeed', setter_callback=self.set_rotation_speed)
        self.char_rotation_direction = serv_fan.configure_char(
            'RotationDirection', setter_callback=self.set_rotation_direction)

    def set_rotation_speed(self, value):
        logging.debug("Rotation speed changed: %s", value)

    def set_rotation_direction(self, value):
        logging.debug("Rotation direction changed: %s", value)


class LightBulb(WebthingAccessory):
    """Webthing lightbulb, logs what the client sets."""

    category = CATEGORY_LIGHTBULB

    def __init__(self, *args, **kwargs):
        super().__init__(*args, aid=kwargs.get('aid'))

        self.thing_id = kwargs.get('thing_id')
        serv_light = self.add_preload_service('Lightbulb', chars=['On', 'Brightness', 'Hue', 'Saturation'])
        self.char_on = serv_light.configure_char(
            'On', setter_callback=self.set_bulb_on)
        self.char_brightness = serv_light.configure_char(
            'Brightness', setter_callback=self.set_bulb_brightness)
        self.char_hue = serv_light.configure_char(
            'Hue', setter_callback=self.set_hue)
        self.char_saturation = serv_light.configure_char(
            'Saturation', setter_callback=self.set_saturation)

        self.accessory_state = 0  # State of the neo light On/Off
        self.hue = 0  # Hue Value 0 - 360 Homekit API
        self.saturation = 100  # Saturation Values 0 - 100 Homekit API
        self.brightness = 100  # Brightness value 0 - 100 Homekit API

    def set_bulb_on(self, value):
        logging.info("Bulb value: %s", value)
        self.accessory_state = value
        if value == 1:  # On
            self.set_hue(self.hue)
        value = True if value == 1 else False
        httpx.put(f"http://127.0.0.1:8000/things/{self.thing_id}/properties/state", json={"state": value})
        self.set_hue(self.hue)

    def set_bulb_brightness(self, value):
        logging.info("Bulb value: %s", value)
        self.brightness = value
        value = int((value / 100) * 254)
        httpx.put(f"http://127.0.0.1:8000/things/{self.thing_id}/properties/brightness", json={"brightness": value})
        self.set_hue(self.hue)

    def set_hue(self, value):
        logging.info("Bulb hue value: %s", value)
        if self.accessory_state == 1:
            self.hue = value
            converter = Converter()
            rgb_tuple = self.hsv_to_rgb(
                self.hue, self.saturation, self.brightness)
            if len(rgb_tuple) == 3:
                xy = converter.rgb_to_xy(rgb_tuple[0], rgb_tuple[1], rgb_tuple[2])
                httpx.put(f"http://127.0.0.1:8000/things/{self.thing_id}/properties/color",
                          json={"color": {"x": xy[0], "y": xy[1]}})
        else:
            self.hue = value

    def set_saturation(self, value):
        logging.info("Bulb saturation value: %s", value)
        self.saturation = value
        self.set_hue(self.hue)

    def hsv_to_rgb(self, h, s, v):
        """
        This function takes
         h - 0 - 360 Deg
         s - 0 - 100 %
         v - 0 - 100 %
        """

        hPri = h / 60
        s = s / 100
        v = v / 100

        if s <= 0.0:
            return int(0), int(0), int(0)

        C = v * s  # Chroma
        X = C * (1 - abs(hPri % 2 - 1))

        RGB_Pri = [0.0, 0.0, 0.0]

        if 0 <= hPri <= 1:
            RGB_Pri = [C, X, 0]
        elif 1 <= hPri <= 2:
            RGB_Pri = [X, C, 0]
        elif 2 <= hPri <= 3:
            RGB_Pri = [0, C, X]
        elif 3 <= hPri <= 4:
            RGB_Pri = [0, X, C]
        elif 4 <= hPri <= 5:
            RGB_Pri = [X, 0, C]
        elif 5 <= hPri <= 6:
            RGB_Pri = [C, 0, X]
        else:
            RGB_Pri = [0, 0, 0]

        m = v - C

        return int((RGB_Pri[0] + m) * 255), int((RGB_Pri[1] + m) * 255), int((RGB_Pri[2] + m) * 255)


class GarageDoor(WebthingAccessory):
    """Fake garage door."""

    category = CATEGORY_GARAGE_DOOR_OPENER

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.add_preload_service('GarageDoorOpener') \
            .configure_char(
            'TargetDoorState', setter_callback=self.change_state)

    def change_state(self, value):
        logging.info("Bulb value: %s", value)
        self.get_service('GarageDoorOpener') \
            .get_characteristic('CurrentDoorState') \
            .set_value(value)


class WindowCovering(WebthingAccessory):
    """Webthing WindowCovering."""

    category = CATEGORY_WINDOW_COVERING

    def __init__(self, *args, **kwargs):
        super().__init__(*args, aid=kwargs.get('aid'))

        '''
        self.add_preload_service('WindowCovering')\
            .configure_char(
                'TargetPosition', setter_callback=self.change_state)

        self.char_cur = self.configure_char('CurrentPosition')
        self.char_cur = self.configure_char('PositionState')
        '''

        # Add the fan service. Also add optional characteristics to it.
        serv_cover = self.add_preload_service(
            'WindowCovering', chars=['CurrentPosition', 'TargetPosition', 'PositionState'])

        self.char_rotation_speed = serv_cover.configure_char(
            'TargetPosition', setter_callback=self.set_target_position)

        self.char_state = serv_cover.configure_char(
            'PositionState', setter_callback=self.set_position_state)

        self.char_rotation_direction = serv_cover.configure_char(
            'CurrentPosition', setter_callback=self.set_current_position)

    '''
    def change_state(self, value):
        logging.info("WindowCovering CurrentPosition value: %s", value)
        self.get_service('WindowCovering')\
            .get_characteristic('CurrentPosition')\
            .set_value(value)
    '''

    def set_target_position(self, value):
        logging.info("WindowCovering TargetPosition value: %s", value)
        self.get_service('WindowCovering') \
            .get_characteristic('TargetPosition') \
            .set_value(value)

    # The value property of PositionState must be one of the following:
    # Characteristic.PositionState.DECREASING = 0;
    # Characteristic.PositionState.INCREASING = 1;
    # Characteristic.PositionState.STOPPED = 2;
    def set_position_state(self, value):
        logging.info("WindowCovering PositionState value: %s", value)
        self.get_service('PositionState') \
            .get_characteristic('PositionState') \
            .set_value(value)

    def set_current_position(self, value):
        logging.info("WindowCovering CurrentPosition value: %s", value)
        self.get_service('WindowCovering') \
            .get_characteristic('CurrentPosition') \
            .set_value(value)


class WebthingBridge(Bridge):

    async def run(self):
        """Schedule tasks for each of the accessories' run method."""
        for acc in self.accessories.values():
            self.driver.async_add_job(acc.run)

        async with websockets.connect("ws://127.0.0.1:8000/things/urn:thingtalk:server") as websocket:
            await websocket.send(json.dumps({
                "messageType": "addEventSubscription",
                "data": {
                    "device_pairing": {}
                }
            }))
            while True:
                recv_json = json.loads(await websocket.recv())
                if recv_json.get("messageType") == "event":
                    data = recv_json['data']
                    event = data['device_pairing']
                    data = event['data']

                    if 'OnOffSwitch' in data['@type'] and 'Light' not in data['@type']:
                        self.add_accessory(
                            Switch(
                                self.driver,
                                data['title'],
                                aid=fnv1a_32(bytes(data['id'], encoding='utf-8')),
                                thing_id=data['id']
                            ))
                        for acc in self.accessories.values():
                            self.driver.async_add_job(acc.run)

                        self.driver.config_changed()

                    break


def get_bridge(driver):
    bridge = WebthingBridge(driver, 'Bridge')

    res = httpx.get('http://127.0.0.1:8000/things')
    data = res.json()
    # print(data)
    for i in data:
        if 'TemperatureSensor' in i['@type'] and len(i['@type']) == 2:
            bridge.add_accessory(
                TemperatureSensor(driver, i['title'], aid=fnv1a_32(bytes(i['id'], encoding='utf-8')), thing_id=i['id']))
        if 'DoorSensor' in i['@type']:
            bridge.add_accessory(
                ContactSensor(driver, i['title'], aid=fnv1a_32(bytes(i['id'], encoding='utf-8')), thing_id=i['id']))
        if 'Light' in i['@type']:
            bridge.add_accessory(
                LightBulb(driver, i['title'], aid=fnv1a_32(bytes(i['id'], encoding='utf-8')), thing_id=i['id']))

        if 'OnOffSwitch' in i['@type'] and 'Light' not in i['@type']:
            bridge.add_accessory(
                Switch(
                    driver,
                    i['title'],
                    aid=fnv1a_32(bytes(i['id'], encoding='utf-8')),
                    thing_id=i['id']
                ))

    # bridge.add_accessory(FakeFan(driver, 'Big Fan'))
    # bridge.add_accessory(GarageDoor(driver, 'Garage'))
    return bridge


driver = AccessoryDriver(port=51826, persist_file='busy_home.state')
driver.add_accessory(accessory=get_bridge(driver))
signal.signal(signal.SIGTERM, driver.signal_handler)
driver.start()

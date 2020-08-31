<h1 align="center">Project ThingTalk</h1>

<h2 align="center">Thing as a Service</h2>

[![pypi-v](https://img.shields.io/pypi/v/thingtalk.svg)](https://pypi.python.org/pypi/thingtalk)
[![python](https://img.shields.io/pypi/pyversions/thingtalk.svg)](https://github.com/hidaris/thingtalk)

## What is `thingtalk` ?
`thingtalk` is a library for the Web of Things protocol in Python Asyncio. This library is derived of webthing-python project (supporting Tornado) but adapted for fastapi (based on Uvicorn for better performance).

### additional features
1. additional_routes -- list of additional routes add to the server
2. additional_middlewares -- list of additional middlewares add to the server
3. additional_on_startup -- list of additional starup event handlers add to the server
4. additional_on_shutdown -- list of additional shutdown event handlers add to the server
5. thing.sync_property -- Sync a property value from cloud or mqtt broker etc, property set value with no action disclaim.
6. thing.property_action -- addional action sync the property change to device. 
6. property.set_value(value, with_action=True) -- if with_action is True, Value instance should emit `update`, else `sync`
7. Add the property change observer to notify the Thing about a property change or do some additional action:

```python
self.value.on("update", lambda _: self.thing.property_notify(self))
self.value.on("sync", lambda _: self.thing.property_notify(self))
self.value.on("update", lambda _: self.thing.property_action(self))
```
   


## Installation
thingtalk can be installed via pip, as such:

`$ pip install thingtalk`

## Running the Sample
`$ wget
https://raw.githubusercontent.com/hidaris/thingtalk/master/example/test.py`

`$ uvicorn test:app --reload`

This starts a server and lets you search for it from your gateway through mDNS. To add it to your gateway, navigate to the Things page in the gateway's UI and click the + icon at the bottom right. If both are on the same network, the example thing will automatically appear.

## Example Implementation
In this code-walkthrough we will set up a dimmable light and a humidity sensor (both using fake data, of course). Both working examples can be found in here.

Dimmable Light
Imagine you have a dimmable light that you want to expose via the web of things API. The light can be turned on/off and the brightness can be set from 0% to 100%. Besides the name, description, and type, a Light is required to expose two properties:

on: the state of the light, whether it is turned on or off
Setting this property via a PUT {"on": true/false} call to the REST API toggles
the light.

brightness: the brightness level of the light from 0-100%
Setting this property via a PUT call to the REST API sets the brightness level of this light.
First we create a new Thing:

``` python
from thingtalk import Thing, Property, Value


class Light(Thing):
    type = ['OnOffSwitch', 'Light'],
    description = 'A web connected lamp'
    
    super().__init__(
        'urn:dev:ops:my-lamp-1234',
        'My Lamp',
    )
```
Now we can add the required properties.

The on property reports and sets the on/off state of the light. For this, we need to have a Value object which holds the actual state and also a method to turn the light on/off. For our purposes, we just want to log the new state if the light is switched on/off.

``` python
async def build(self):
    on = Property(
            'on',
            Value(True, lambda v: print('On-State is now', v)),
            metadata={
                '@type': 'OnOffProperty',
                'title': 'On/Off',
                'type': 'boolean',
                'description': 'Whether the lamp is turned on',
        })
    await self.add_property(on)
```

The brightness property reports the brightness level of the light and sets the level. Like before, instead of actually setting the level of a light, we just log the level.

``` python
brightness = Property(
         'brightness',
        Value(50, lambda v: print('Brightness is now', v)),
        metadata={
            '@type': 'BrightnessProperty',
            'title': 'Brightness',
            'type': 'number',
            'description': 'The level of light from 0-100',
            'minimum': 0,
            'maximum': 100,
            'unit': 'percent',
        })
await self.add_property(brightness)
```

Now we can add our newly created thing to the server and start it:

``` python
# If adding more than one thing, use MultipleThings() with a name.
# In the single thing case, the thing's name will be broadcast.
with background_thread_loop() as loop:
    app = WebThingServer(loop, Light).create()
```

This will start the server, making the light available via the WoT REST API and announcing it as a discoverable resource on your local network via mDNS.

Sensor
Let's now also connect a humidity sensor to the server we set up for our light.

A MultiLevelSensor (a sensor that returns a level instead of just on/off) has one required property (besides the name, type, and optional description): level. We want to monitor this property and get notified if the value changes.

First we create a new Thing:

```python
from thingtalk import Thing, Property, Value

class Light(Thing):
    type = ['MultiLevelSensor'],
    description = 'A web connected humidity sensor'
    
    super().__init__(
        'urn:dev:ops:my-humidity-sensor-1234',
        'My Humidity Sensor',
    )
```

Then we create and add the appropriate property:

level: tells us what the sensor is actually reading

Contrary to the light, the value cannot be set via an API call, as it wouldn't make much sense, to SET what a sensor is reading. Therefore, we are creating a readOnly property.

```python
async def build(self): 
    await self.add_property(
        Property(
            'level',
            Value(0.0),
            metadata={
                '@type': 'LevelProperty',
                'title': 'Humidity',
                'type': 'number',
                'description': 'The current humidity in %',
                'minimum': 0,
                'maximum': 100,
                'unit': 'percent',
                'readOnly': True,
            }))
    return self
```


Now we have a sensor that constantly reports 0%. To make it usable, we need a thread or some kind of input when the sensor has a new reading available. For this purpose we start a thread that queries the physical sensor every few seconds. For our purposes, it just calls a fake method.

```python
self.sensor_update_task = \
    get_event_loop().create_task(self.update_level())

async def update_level(self):
    try:
        while True:
            await sleep(3)
            new_level = self.read_from_gpio()
            logging.debug('setting new humidity level: %s', new_level)
            await self.level.notify_of_external_update(new_level)
    except CancelledError:
        pass
```

This will update our Value object with the sensor readings via the self.level.notify_of_external_update(read_from_gpio()) call. The Value object now notifies the property and the thing that the value has changed, which in turn notifies all websocket listeners.

<h1 align="center">Project thingTalk</h1>

<h2 align="center">Thing as a Service</h2>

[![pypi-v](https://img.shields.io/pypi/v/thingtalk.svg)](https://pypi.python.org/pypi/thingtalk)
[![python](https://img.shields.io/pypi/pyversions/thingtalk.svg)](https://github.com/hidaris/thingtalk)

## What is `thingTalk`?
`thingTalk` is a web of things implementation, currently supporting a dialect protocol called webthings.

## Project Vision:
To provide a communication layer for spatial computing, and make iot interoperable with xr.

### The key features are:
* Layered design -- Provide services such as rule engines on top of the core protocol layer.
* Scalability -- Can be based on MQTT to achieve distributed deployment.
* Standards-based -- Compatibility with community standards[WoT].
* Fast: Very high performance, on par with NodeJS and Go (thanks to FastAPI).
* Robust: Get production-ready code. With automatic interactive documentation.
* Fast to code: Increase the speed to develop features by about 200% to 300%. *

## Architecture
```
+-----------+ +----------------------------------------------------------------+  +------------+
|           | |   Application service                                          |  |            |
|  Security | | +--------------+ +------------------+ +---------------------+  |  | Management |
|           | | |              | |                  | |                     |  |  |            |
| +-------+ | | |   Http Rest  | |    Websocket     | |        MQTT         |  |  |            |
| |TLS/SSL| | | |              | |                  | |                     |  |  | +--------+ |
| |       | | | |              | |                  | |                     |  |  | |        | |
| +-------+ | | +--------------+ +------------------+ +---------------------+  |  | |Registry| |
|           | |                                                                |  | |        | |
|           | +----------------------------------------------------------------+  | |        | |
|           |                                                                     | +--------+ |
|           | +----------------------------------------------------------------+  |            |
| +-------+ | |  supporting service                                            |  |            |
| |       | | |                                                                |  |            |
| |encryption |  +---------------------+    +-------------------------+        |  |            |
| |       | | |  |   Rules Engine      |    |   Additionnal Service   |        |  |            |
| +-------+ | |  |                     |    |                         |        |  |            |
|           | |  +---------------------+    +-------------------------+        |  |            |
|           | |                                                                |  | +-------+  |
|           | +----------------------------------------------------------------+  | |       |  |
|           |                                                                     | |       |  |
|           | +-----------------------------------------------------------------+ | |Scheduler |
| +-------+ | |  core service                                                   | | |       |  |
| |       | | |  +-----------------------------------------------------------+  | | |       |  |
| Authentication |  All MicroServices Innercommunicate via MQTT API          |  | | +-------+  |
| |       | | |  |  +----------+   +-------------+  +---------------+        |  | |            |
| +-------+ | |  |  |  Thing   |   |  Gateway    |  |    Cloud      |        |  | |            |
|           | |  |  |          |   |             |  |               |        |  | |            |    Authorization
|           | |  |  +----------+   +-------------+  +---------------+        |  | |            |
|           | |  |                                                           |  | |            |
|           | |  +-----------------------------------------------------------+  | |            |
|           | |                                                                 | |            |
+-----------+ +-----------------------------------------------------------------+ +------------+

 +-------------------------------------------------------------------------------------------+
 |                                                                                           |
 |  +---------+ +---------+ +---------+ +----------+ +---------+ +-----------+ +-----------+ |
 |  |         | |         | |         | |          | |         | |           | |           | |
 |  | Zigbee  | |  BLE    | |  Rest   | |  Modbus  | | Virtual | |   MQTT    | | Additional| |
 |  |         | |         | |         | |          | |         | |           | |           | |
 |  +---------+ +---------+ +---------+ +----------+ +---------+ +-----------+ +-----------+ |
 |                                                                                           |
 +-------------------------------------------------------------------------------------------+
```

## Design
```
                                          +----------------------+
                                          |                      |
                                          |       GateWay        |
                                          |                      |
                                          +----+---------^-------+
                                                 |           |
                                                 |           |
                                                 |           |
                                                 |           |
                                        sub /things/#        |  pub /things/#/{td|values|action|event}
                                                 |           |
                                                 |           |
                                                 |           |
                                                 |           |
                                          +---------v----------+------+
                                          |                           |
                                          |       MQTT   Broker       |
                                          |                           |<--------------------------------+
                   +--------------------->+---------------^-----------+                                 |
                   |                                       |                                            |
sub /things/things1/{set|get|request_action}               |sub /things/thing2/{set|get|request_action} |
pub /things/things1/{td|values|action|event}               |pub /things/thing2/{td|values|action|event} |
                   |                                       |                                            |
            +------+---------------+        +------+-----------------+        +----------------+------------+
            |                      |        |                        |        |                             |
            |      Thing1          |        |       Thing2           |        |       Multiple Thing        |
            |                      |        |                        |        |                             |
            +----------------------+        +------------------------+        +-----------------------------+
```

## Installation
thingtalk can be installed via pip, as such:

`$ pip install thingtalk`

# Thanks
<a href="https://www.jetbrains.com/?from=thingTalk"><img src="https://github.com/hidaris/thingtalk/blob/master/docs/images/jetbrains.png" height="120" alt="JetBrains"/></a>

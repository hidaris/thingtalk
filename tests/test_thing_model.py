import ujson as json
import re
import socket
import time
from fastapi.testclient import TestClient
from ..example.test_light import app

_TIME_REGEX = r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[+-]\d{2}:\d{2}$"
_PROTO = "http"
_BASE_URL = "localhost:8000"
_PATH_PREFIX = "/things/urn:dev:ops:my-lamp-1234"
_AUTHORIZATION_HEADER = None
_DEBUG = False
_SKIP_ACTIONS_EVENTS = False
_SKIP_WEBSOCKET = False
ws_href = None


def get_ip():
    """
    Get the default local IP address.

    From: https://stackoverflow.com/a/28950776
    """
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("10.255.255.255", 1))
        ip = s.getsockname()[0]
    except (socket.error, IndexError):
        ip = "127.0.0.1"
    finally:
        s.close()

    return ip


client = TestClient(app)


def http_request(method, path, data=None):
    """
    Send an HTTP request to the server.

    method -- request method, i.e. 'GET'
    path -- request path
    data -- optional data to include
    """
    url = _PROTO + "://" + _BASE_URL + _PATH_PREFIX + path
    url = url.rstrip("/")
    print(url)

    fake_host = "localhost"
    if ":" in _BASE_URL:
        fake_host += ":" + _BASE_URL.split(":")[1]

    headers = {
        "Host": fake_host,
        "Accept": "application/json",
    }

    proxies = {
        "http": None,
        "https": None,
    }

    if _DEBUG:
        if data is None:
            print("Request:  {} {}".format(method, url))
        else:
            print("Request:  {} {}\n          {}".format(method, url, data))

    if _AUTHORIZATION_HEADER is not None:
        headers["Authorization"] = _AUTHORIZATION_HEADER

    if data is None:
        response = client.request(method, url, headers=headers, proxies=proxies)
    else:
        headers["Content-Type"] = "application/json"
        response = client.request(
            method, url, json=data, headers=headers, proxies=proxies
        )

    if response.content:
        if _DEBUG:
            print(
                "Response: {} {}\n".format(
                    response.status_code, response.content.decode()
                )
            )

        return response.status_code, json.loads(response.content.decode())
    else:
        if _DEBUG:
            print("Response: {}\n".format(response.status_code))

        return response.status_code, None


def test_thing_description():
    # Test thing description
    code, body = http_request("get", "/")
    assert code == 200
    assert body["id"] == "urn:dev:ops:my-lamp-1234"
    assert body["title"] == "My Lamp"
    assert body["security"] == "nosec_sc"
    assert body["securityDefinitions"]["nosec_sc"]["scheme"] == "nosec"
    assert body["@context"] == "https://iot.mozilla.org/schemas"
    assert lists_equal(body["@type"], ["OnOffSwitch", "Light"])
    assert body["description"] == "A web connected lamp"
    assert body["properties"]["on"]["@type"] == "OnOffProperty"
    assert body["properties"]["on"]["title"] == "On/Off"
    assert body["properties"]["on"]["type"] == "boolean"
    assert body["properties"]["on"]["description"] == "Whether the lamp is turned on"
    assert len(body["properties"]["on"]["links"]) == 1
    assert (
        body["properties"]["on"]["links"][0]["href"] == _PATH_PREFIX + "/properties/on"
    )
    assert body["properties"]["brightness"]["@type"] == "BrightnessProperty"
    assert body["properties"]["brightness"]["title"] == "Brightness"
    assert body["properties"]["brightness"]["type"] == "integer"
    assert (
        body["properties"]["brightness"]["description"]
        == "The level of light from 0-100"
    )
    assert body["properties"]["brightness"]["minimum"] == 0
    assert body["properties"]["brightness"]["maximum"] == 100
    assert body["properties"]["brightness"]["unit"] == "percent"
    assert len(body["properties"]["brightness"]["links"]) == 1
    assert (
        body["properties"]["brightness"]["links"][0]["href"]
        == _PATH_PREFIX + "/properties/brightness"
    )

    if not _SKIP_ACTIONS_EVENTS:
        assert body["actions"]["fade"]["title"] == "Fade"
        assert (
            body["actions"]["fade"]["description"] == "Fade the lamp to a given level"
        )
        assert body["actions"]["fade"]["input"]["type"] == "object"
        assert (
            body["actions"]["fade"]["input"]["properties"]["brightness"]["type"]
            == "integer"
        )
        assert (
            body["actions"]["fade"]["input"]["properties"]["brightness"]["minimum"] == 0
        )
        assert (
            body["actions"]["fade"]["input"]["properties"]["brightness"]["maximum"]
            == 100
        )
        assert (
            body["actions"]["fade"]["input"]["properties"]["brightness"]["unit"]
            == "percent"
        )
        assert (
            body["actions"]["fade"]["input"]["properties"]["duration"]["type"]
            == "integer"
        )
        assert (
            body["actions"]["fade"]["input"]["properties"]["duration"]["minimum"] == 1
        )
        assert (
            body["actions"]["fade"]["input"]["properties"]["duration"]["unit"]
            == "milliseconds"
        )
        assert len(body["actions"]["fade"]["links"]) == 1
        assert (
            body["actions"]["fade"]["links"][0]["href"]
            == _PATH_PREFIX + "/actions/fade"
        )
        assert body["events"]["overheated"]["type"] == "number"
        assert body["events"]["overheated"]["unit"] == "degree celsius"
        assert (
            body["events"]["overheated"]["description"]
            == "The lamp has exceeded its safe operating temperature"
        )
        assert len(body["events"]["overheated"]["links"]) == 1
        assert (
            body["events"]["overheated"]["links"][0]["href"]
            == _PATH_PREFIX + "/events/overheated"
        )

    if _SKIP_ACTIONS_EVENTS:
        assert len(body["links"]) >= 1
        assert body["links"][0]["rel"] == "properties"
        assert body["links"][0]["href"] == _PATH_PREFIX + "/properties"
        remaining_links = body["links"][1:]
    else:
        assert len(body["links"]) >= 3
        assert body["links"][0]["rel"] == "properties"
        assert body["links"][0]["href"] == _PATH_PREFIX + "/properties"
        assert body["links"][1]["rel"] == "actions"
        assert body["links"][1]["href"] == _PATH_PREFIX + "/actions"
        assert body["links"][2]["rel"] == "events"
        assert body["links"][2]["href"] == _PATH_PREFIX + "/events"
        remaining_links = body["links"][3:]

    if not _SKIP_WEBSOCKET:
        assert len(remaining_links) >= 1

        global ws_href
        for link in remaining_links:
            if link["rel"] != "alternate":
                continue

            if "mediaType" in link:
                assert link["mediaType"] == "text/html"
                assert link["href"] == _PATH_PREFIX
            else:
                proto = "wss" if _PROTO == "https" else "ws"
                print(link["href"])
                print(_PATH_PREFIX)
                # TODO failed
                assert re.match(proto + r"://[^/]+" + _PATH_PREFIX, link["href"])
                ws_href = link["href"]

        assert ws_href is not None


def lists_equal(a, b):
    if len(a) != len(b):
        return False

    intersection = set(a) & set(b)
    return len(intersection) == len(a)


def test_properties():
    # Test properties
    code, body = http_request("GET", "/properties")
    assert code == 200
    assert body["brightness"] == 50
    assert body["on"]

    code, body = http_request("GET", "/properties/brightness")
    assert code == 200
    assert body["brightness"] == 50

    code, body = http_request("PUT", "/properties/brightness", {"brightness": 25})

    assert code == 200
    assert body["brightness"] == 25

    code, body = http_request("GET", "/properties/brightness")
    assert code == 200
    assert body["brightness"] == 25


def test_events():
    # Test events
    code, body = http_request("GET", "/events")
    assert code == 200
    assert len(body) == 0


def test_actions():
    # Test actions
    code, body = http_request("GET", "/actions")
    assert code == 200
    assert len(body) == 0

    code, body = http_request(
        "POST",
        "/actions",
        {
            "fade": {
                "input": {
                    "brightness": 50,
                    "duration": 2000,
                },
            },
        },
    )
    assert code == 201
    assert body["fade"]["input"]["brightness"] == 50
    assert body["fade"]["input"]["duration"] == 2000
    assert body["fade"]["href"].startswith(_PATH_PREFIX + "/actions/fade/")
    assert body["fade"]["status"] == "created"
    action_id = body["fade"]["href"].split("/")[-1]

    # Wait for the action to complete
    time.sleep(2.5)

    code, body = http_request("GET", "/actions")
    assert code == 200
    assert len(body) == 1
    assert len(body[0].keys()) == 1
    assert body[0]["fade"]["input"]["brightness"] == 50
    assert body[0]["fade"]["input"]["duration"] == 2000
    assert body[0]["fade"]["href"] == _PATH_PREFIX + "/actions/fade/" + action_id
    assert re.match(_TIME_REGEX, body[0]["fade"]["timeRequested"]) is not None
    assert re.match(_TIME_REGEX, body[0]["fade"]["timeCompleted"]) is not None
    assert body[0]["fade"]["status"] == "completed"

    code, body = http_request("GET", "/actions/fade")
    assert code == 200
    assert len(body) == 1
    assert len(body[0].keys()) == 1
    assert body[0]["fade"]["input"]["brightness"] == 50
    assert body[0]["fade"]["input"]["duration"] == 2000
    assert body[0]["fade"]["href"] == _PATH_PREFIX + "/actions/fade/" + action_id
    assert re.match(_TIME_REGEX, body[0]["fade"]["timeRequested"]) is not None
    assert re.match(_TIME_REGEX, body[0]["fade"]["timeCompleted"]) is not None
    assert body[0]["fade"]["status"] == "completed"

    code, body = http_request("DELETE", "/actions/fade/" + action_id)
    assert code == 204
    assert body is None

    # The action above generates an event, so check it.
    code, body = http_request("GET", "/events")
    assert code == 200
    assert len(body) == 1
    assert len(body[0].keys()) == 1
    assert body[0]["overheated"]["data"] == 102
    assert re.match(_TIME_REGEX, body[0]["overheated"]["timestamp"]) is not None

    code, body = http_request("GET", "/events/overheated")
    assert code == 200
    assert len(body) == 1
    assert len(body[0].keys()) == 1
    assert body[0]["overheated"]["data"] == 102
    assert re.match(_TIME_REGEX, body[0]["overheated"]["timestamp"]) is not None

    code, body = http_request(
        "POST",
        "/actions/fade",
        {
            "fade": {
                "input": {
                    "brightness": 50,
                    "duration": 2000,
                },
            },
        },
    )
    assert code == 201
    assert body["fade"]["input"]["brightness"] == 50
    assert body["fade"]["input"]["duration"] == 2000
    assert body["fade"]["href"].startswith(_PATH_PREFIX + "/actions/fade/")
    assert body["fade"]["status"] == "created"
    action_id = body["fade"]["href"].split("/")[-1]

    # Wait for the action to complete
    time.sleep(2.5)

    code, body = http_request("GET", "/actions")
    assert code == 200
    assert len(body) == 1
    assert len(body[0].keys()) == 1
    assert body[0]["fade"]["input"]["brightness"] == 50
    assert body[0]["fade"]["input"]["duration"] == 2000
    assert body[0]["fade"]["href"] == _PATH_PREFIX + "/actions/fade/" + action_id
    assert re.match(_TIME_REGEX, body[0]["fade"]["timeRequested"]) is not None
    assert re.match(_TIME_REGEX, body[0]["fade"]["timeCompleted"]) is not None
    assert body[0]["fade"]["status"] == "completed"

    code, body = http_request("GET", "/actions/fade")
    assert code == 200
    assert len(body) == 1
    assert len(body[0].keys()) == 1
    assert body[0]["fade"]["input"]["brightness"] == 50
    assert body[0]["fade"]["input"]["duration"] == 2000
    assert body[0]["fade"]["href"] == _PATH_PREFIX + "/actions/fade/" + action_id
    assert re.match(_TIME_REGEX, body[0]["fade"]["timeRequested"]) is not None
    assert re.match(_TIME_REGEX, body[0]["fade"]["timeCompleted"]) is not None
    assert body[0]["fade"]["status"] == "completed"

    code, body = http_request("DELETE", "/actions/fade/" + action_id)
    assert code == 204
    assert body is None


def test_websocket():
    # Test setting property through websocket
    ws_href = "ws://localhost:8000/channel"
    if _AUTHORIZATION_HEADER is not None:
        ws_href += "?jwt=" + _AUTHORIZATION_HEADER.split(" ")[1]
    with client.websocket_connect(ws_href) as websocket:
        websocket.send_json(
            {
                "messageType": "subscribe",
                "data": {"thing_ids": ["urn:dev:ops:my-lamp-1234"]},
            }
        )
        websocket.send_json(
            {
                "topic": "things/urn:dev:ops:my-lamp-1234",
                "messageType": "setProperty",
                "data": {
                    "brightness": 10,
                },
            }
        )
        message = websocket.receive_json(mode="binary")
        assert message["topic"] == "things/urn:dev:ops:my-lamp-1234"
        assert message["messageType"] == "propertyStatus"
        assert message["data"]["brightness"] == 10
        code, body = http_request("GET", "/properties/brightness")
        assert code == 200
        assert body["brightness"] == 10

        # Test requesting action through websocket
        websocket.send_json(
            {
                "topic": "things/urn:dev:ops:my-lamp-1234",
                "messageType": "requestAction",
                "data": {
                    "fade": {
                        "input": {
                            "brightness": 90,
                            "duration": 1000,
                        },
                    },
                },
            }
        )

        # Handle any extra propertyStatus message first
        while True:
            message = websocket.receive_json(mode="binary")
            if message["messageType"] == "propertyStatus":
                continue

            break
        assert message["topic"] == "things/urn:dev:ops:my-lamp-1234"
        assert message["messageType"] == "actionStatus"
        assert message["data"]["fade"]["input"]["brightness"] == 90
        assert message["data"]["fade"]["input"]["duration"] == 1000
        assert message["data"]["fade"]["href"].startswith(
            _PATH_PREFIX + "/actions/fade/"
        )
        assert message["data"]["fade"]["status"] == "created"
        message = websocket.receive_json(mode="binary")
        assert message["topic"] == "things/urn:dev:ops:my-lamp-1234"
        assert message["messageType"] == "actionStatus"
        assert message["data"]["fade"]["input"]["brightness"] == 90
        assert message["data"]["fade"]["input"]["duration"] == 1000
        assert message["data"]["fade"]["href"].startswith(
            _PATH_PREFIX + "/actions/fade/"
        )
        assert message["data"]["fade"]["status"] == "pending"

        # These may come out of order
        action_id = None
        received = [False, False, False]
        for _ in range(0, 3):
            message = websocket.receive_json(mode="binary")
            if message["topic"] != "things/urn:dev:ops:my-lamp-1234":
                continue

            if message["messageType"] == "propertyStatus":
                assert message["data"]["brightness"] == 90
                received[0] = True

            elif message["messageType"] == "actionStatus":
                assert message["data"]["fade"]["input"]["brightness"] == 90
                assert message["data"]["fade"]["input"]["duration"] == 1000
                assert message["data"]["fade"]["href"].startswith(
                    _PATH_PREFIX + "/actions/fade/"
                )
                assert message["data"]["fade"]["status"] == "completed"
                action_id = message["data"]["fade"]["href"].split("/")[-1]
                received[1] = True
            elif message["messageType"] == "event":
                assert message["data"]["overheated"]["data"] == 102
                assert (
                    re.match(_TIME_REGEX, message["data"]["overheated"]["timestamp"])
                    is not None
                )
                received[2] = True
            else:
                raise ValueError("Wrong message: {}".format(message["messageType"]))

        for r in received:
            assert r

        code, body = http_request("GET", "/actions")
        assert code == 200
        assert len(body) == 1
        assert len(body[0].keys()) == 1
        assert body[0]["fade"]["input"]["brightness"] == 90
        assert body[0]["fade"]["input"]["duration"] == 1000
        assert body[0]["fade"]["href"] == _PATH_PREFIX + "/actions/fade/" + action_id
        assert re.match(_TIME_REGEX, body[0]["fade"]["timeRequested"]) is not None
        assert re.match(_TIME_REGEX, body[0]["fade"]["timeCompleted"]) is not None
        assert body[0]["fade"]["status"] == "completed"

        code, body = http_request("GET", "/actions/fade/" + action_id)
        assert code == 200
        assert len(body.keys()) == 1
        assert body["fade"]["href"] == _PATH_PREFIX + "/actions/fade/" + action_id
        assert body["fade"]["href"] == _PATH_PREFIX + "/actions/fade/" + action_id
        assert re.match(_TIME_REGEX, body["fade"]["timeRequested"]) is not None
        assert re.match(_TIME_REGEX, body["fade"]["timeCompleted"]) is not None
        assert body["fade"]["status"] == "completed"

        code, body = http_request("GET", "/events")
        assert code == 200
        assert len(body) == 3
        assert len(body[2].keys()) == 1
        assert body[2]["overheated"]["data"] == 102
        assert re.match(_TIME_REGEX, body[2]["overheated"]["timestamp"]) is not None

        websocket.send_json(
            {
                "topic": "things/urn:dev:ops:my-lamp-1234",
                "messageType": "requestAction",
                "data": {
                    "fade": {
                        "input": {
                            "brightness": 100,
                            "duration": 500,
                        },
                    },
                },
            }
        )
        message = websocket.receive_json(mode="binary")
        assert message["topic"] == "things/urn:dev:ops:my-lamp-1234"
        assert message["messageType"] == "actionStatus"
        assert message["data"]["fade"]["input"]["brightness"] == 100
        assert message["data"]["fade"]["input"]["duration"] == 500
        assert message["data"]["fade"]["href"].startswith(
            _PATH_PREFIX + "/actions/fade/"
        )
        assert message["data"]["fade"]["status"] == "created"
        assert (
            re.match(_TIME_REGEX, message["data"]["fade"]["timeRequested"]) is not None
        )
        message = websocket.receive_json(mode="binary")
        assert message["topic"] == "things/urn:dev:ops:my-lamp-1234"
        assert message["messageType"] == "actionStatus"
        assert message["data"]["fade"]["input"]["brightness"] == 100
        assert message["data"]["fade"]["input"]["duration"] == 500
        assert message["data"]["fade"]["href"].startswith(
            _PATH_PREFIX + "/actions/fade/"
        )
        assert message["data"]["fade"]["status"] == "pending"
        assert (
            re.match(_TIME_REGEX, message["data"]["fade"]["timeRequested"]) is not None
        )

        # These may come out of order
        received = [False, False, False]
        for _ in range(0, 3):
            message = websocket.receive_json(mode="binary")
            if message["topic"] != "things/urn:dev:ops:my-lamp-1234":
                continue

            if message["messageType"] == "propertyStatus":
                assert message["data"]["brightness"] == 100
                received[0] = True
            elif message["messageType"] == "event":
                assert message["data"]["overheated"]["data"] == 102
                assert (
                    re.match(_TIME_REGEX, message["data"]["overheated"]["timestamp"])
                    is not None
                )
                received[1] = True
            elif message["messageType"] == "actionStatus":
                assert message["data"]["fade"]["input"]["brightness"] == 100
                assert message["data"]["fade"]["input"]["duration"] == 500
                assert message["data"]["fade"]["href"].startswith(
                    _PATH_PREFIX + "/actions/fade/"
                )
                assert message["data"]["fade"]["status"] == "completed"
                assert (
                    re.match(_TIME_REGEX, message["data"]["fade"]["timeRequested"])
                    is not None
                )
                assert (
                    re.match(_TIME_REGEX, message["data"]["fade"]["timeCompleted"])
                    is not None
                )
                received[2] = True

        for r in received:
            assert r

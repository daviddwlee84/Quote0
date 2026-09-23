import copy
import json
import unittest
from unittest.mock import patch

import requests
from pydantic import ValidationError
from quote0 import DotClient, Quote0, CanvasApiRequest, DeviceSettingsRequest

CARD = {
    "data": {"title": "Hello"},
    "windowData": {
        "default": [{"type": "div", "props": {"children": '{{get inputData "title"}}'}}]
    },
}


def response(body, status=200):
    result = requests.Response()
    result.status_code = status
    result._content = json.dumps(body).encode()
    return result


class OpenApiTests(unittest.TestCase):
    @patch("quote0.client.requests.get")
    def test_account_lists_parse_arrays_and_use_no_device_id(self, get):
        get.return_value = response(
            [{"id": "A", "alias": None, "model": "quote_0", "futureField": 1}]
        )
        client = DotClient("key")
        result = client.list_devices()
        self.assertTrue(result.success)
        self.assertEqual(result.response[0].id, "A")
        self.assertEqual(result.response[0].model_dump()["futureField"], 1)
        get.assert_called_once_with(
            "https://dot.mindreset.tech/api/authV2/open/devices",
            headers={"Authorization": "Bearer key", "Content-Type": "application/json"},
            timeout=30,
        )
        get.return_value = response([])
        self.assertEqual(client.list_devices().response, [])
        get.return_value = response({})
        self.assertFalse(client.list_devices().success)
        get.return_value = response([{"alias": "No ID"}])
        self.assertFalse(client.list_devices().success)

    @patch("quote0.client.requests.get")
    def test_device_queries_and_task_type_validation(self, get):
        client = Quote0("key", "a/b")
        get.return_value = response(
            [{"type": "CANVAS_API", "key": "slot-2", "taskAlias": "Quota"}]
        )
        result = client.list_tasks("fixed")
        self.assertEqual(result.response[0].key, "slot-2")
        self.assertTrue(get.call_args.args[0].endswith("/device/a%2Fb/fixed/list"))
        with self.assertRaises(ValueError):
            client.list_tasks("../settings")
        self.assertEqual(get.call_count, 1)
        get.return_value = response(
            {"deviceId": "a/b", "status": {"battery": "85%", "wifi": "Online"}}
        )
        self.assertEqual(client.get_status().response.status["battery"], "85%")
        get.return_value = response(
            {
                "deviceId": "a/b",
                "timezone": "Asia/Shanghai",
                "interval": {"batteryMs": 60000},
                "sleep": None,
                "alias": None,
                "location": None,
            }
        )
        self.assertEqual(client.get_settings().response.interval.batteryMs, 60000)

    @patch("quote0.client.requests.get")
    def test_get_failures_do_not_retry(self, get):
        client = DotClient("key")
        get.side_effect = requests.Timeout("timed out")
        self.assertFalse(client.list_devices().success)
        get.assert_called_once()
        get.side_effect = None
        get.return_value = response({"message": "Denied"}, 401)
        self.assertEqual(client.list_devices().error, "HTTP 401: Denied")
        get.return_value = response({"message": "Slow down"}, 429)
        self.assertEqual(client.list_devices().status_code, 429)

    @patch("quote0.client.requests.post")
    def test_alias_omit_clear_numeric_and_task_selection(self, post):
        post.return_value = response({"message": "Done"})
        client = Quote0("key", "device")
        for send in (
            lambda **kw: client.send_text(message="hi", **kw),
            lambda **kw: client.send_image(image="https://example.com/a.png", **kw),
            lambda **kw: client.send_canvas(CARD["windowData"], **kw),
        ):
            send()
            self.assertNotIn("taskAlias", post.call_args.kwargs["json"])
            for alias in (None, "", "Quota", 42):
                send(task_key="slot", task_alias=alias)
                self.assertEqual(post.call_args.kwargs["json"]["taskAlias"], alias)
                self.assertEqual(post.call_args.kwargs["json"]["taskKey"], "slot")
            with self.assertRaises(ValueError):
                send(task_alias="x" * 101)

    @patch("quote0.client.requests.post")
    def test_styles_canvas_and_next_wire_payloads(self, post):
        post.return_value = response({"message": "Done"})
        client = Quote0("key", "device")
        client.send_text(
            styles={
                "message": {
                    "fontFamily": "FusionPixel12",
                    "fontSize": 12,
                    "lineHeight": 1.2,
                }
            }
        )
        self.assertEqual(
            post.call_args.kwargs["json"]["styles"]["message"]["fontSize"], 12
        )
        with self.assertRaises(ValueError):
            client.send_text(styles={"title": {"lineHeight": 1.2}})
        client.send_canvas(
            CARD["windowData"],
            data=CARD["data"],
            layout_full={"style": {"padding": 0}},
            refresh_now=False,
            border=1,
        )
        payload = post.call_args.kwargs["json"]
        self.assertTrue(post.call_args.args[0].endswith("/canvas"))
        self.assertEqual(payload["data"], CARD["data"])
        self.assertFalse(payload["refreshNow"])
        self.assertEqual(payload["border"], 1)
        self.assertNotIn("deviceId", payload)
        client.next_content()
        self.assertTrue(post.call_args.args[0].endswith("/next"))
        with self.assertRaises(ValueError):
            client.send_image("base64", image="url")

    @patch("quote0.client.requests.post")
    @patch("quote0.client.requests.get")
    def test_partial_settings_clear_and_timezone_validation(self, get, post):
        client = Quote0("key", "device")
        post.return_value = response({"message": "Saved"})
        client.update_settings({"alias": None, "interval": {"batteryMs": 60000}})
        self.assertEqual(
            post.call_args.kwargs["json"],
            {"alias": None, "interval": {"batteryMs": 60000}},
        )
        get.assert_not_called()
        get.return_value = response(
            [
                {
                    "key": "Asia/Shanghai",
                    "name": "Shanghai",
                    "utcOffsetMinutes": 480,
                    "utcOffsetLabel": "UTC+8",
                }
            ]
        )
        client.update_settings({"timezone": "Asia/Shanghai"})
        self.assertTrue(get.call_args.args[0].endswith("/open/timezones"))
        post.reset_mock()
        with self.assertRaisesRegex(ValueError, "Unsupported timezone"):
            client.update_settings({"timezone": "Invalid/Zone"})
        post.assert_not_called()
        get.return_value = response({"message": "Unavailable"}, 503)
        self.assertFalse(client.update_settings({"timezone": "Asia/Shanghai"}).success)
        post.assert_not_called()

    def test_settings_boundaries(self):
        for ms in (60000, 43200000):
            DeviceSettingsRequest.model_validate({"interval": {"powerMs": ms}})
        for value in (
            {},
            {"interval": {}},
            {"interval": None},
            {"timezone": None},
            {"interval": {"powerMs": 60001}},
            {"interval": {"batteryMs": 0}},
            {"interval": {"powerMs": 43260000}},
            {"interval": {"powerMs": True}},
            {"sleep": None},
            {"sleep": {"enabled": False}},
            {"sleep": {"enabled": True, "start": "23:00", "end": "23:00"}},
            {"sleep": {"enabled": True, "start": "24:00", "end": "07:00"}},
            {"unknown": "value"},
        ):
            with self.subTest(value=value), self.assertRaises(ValueError):
                DeviceSettingsRequest.model_validate(value)
        DeviceSettingsRequest.model_validate(
            {"sleep": {"enabled": True, "start": "23:00", "end": "07:00"}}
        )


class CanvasValidationTests(unittest.TestCase):
    def test_lists_conditions_and_images(self):
        card = {
            "windowData": {
                "default": [
                    {
                        "$ifAny": ["inputData.items"],
                        "$then": {
                            "type": "div",
                            "props": {
                                "$for": {
                                    "items": "inputData.items",
                                    "as": "item",
                                    "index": "i",
                                    "limit": 3,
                                },
                                "$empty": {
                                    "type": "span",
                                    "props": {"children": "Empty"},
                                },
                                "children": [
                                    {
                                        "type": "img",
                                        "props": {"src": '{{get item "image"}}'},
                                    },
                                    {
                                        "type": "span",
                                        "props": {"children": '{{get item "name"}}'},
                                    },
                                ],
                            },
                        },
                        "$else": None,
                    }
                ]
            }
        }
        CanvasApiRequest.model_validate(card)
        self.assertEqual(
            CanvasApiRequest.model_validate(CARD).windowData, CARD["windowData"]
        )

    def test_invalid_paths_and_reserved_keys(self):
        cases = [
            ({"windowData": {}}, "windowData.default"),
            (
                {"windowData": {"default": [{"type": "button", "props": {}}]}},
                "default[0].type",
            ),
            (
                {
                    "windowData": {
                        "default": [{"type": "div", "props": {"onClick": "x"}}]
                    }
                },
                "onClick",
            ),
            (
                {
                    "windowData": {
                        "default": [{"type": "img", "props": {"src": "file:///tmp/a"}}]
                    }
                },
                "src",
            ),
            (
                {
                    "windowData": {
                        "default": [{"type": "div", "props": {"$for": {"items": []}}}]
                    }
                },
                "$for.items",
            ),
            ({**CARD, "data": {"taskAlias": "bad"}}, "data.taskAlias"),
            ({**CARD, "data": {"nested": {"__proto__": {}}}}, "data.nested.__proto__"),
            ({**CARD, "layoutFull": {"tw": 42}}, "layoutFull.tw"),
        ]
        for payload, message in cases:
            with self.subTest(message=message), self.assertRaises(ValueError) as caught:
                CanvasApiRequest.model_validate(payload)
            self.assertIn(message, str(caught.exception))

    def test_size_count_and_depth_limits(self):
        leaf = {"type": "span", "props": {"children": "x"}}
        for card in (
            {"windowData": {"default": [leaf] * 81}},
            {
                "windowData": {
                    "default": [{"type": "span", "props": {"children": "x" * 4001}}]
                }
            },
            {**CARD, "data": {"large": "x" * 65536}},
        ):
            with self.assertRaises(ValueError):
                CanvasApiRequest.model_validate(card)
        tree = copy.deepcopy(leaf)
        for _ in range(17):
            tree = {"type": "div", "props": {"children": tree}}
        with self.assertRaises(ValueError):
            CanvasApiRequest.model_validate({"windowData": {"default": [tree]}})


if __name__ == "__main__":
    unittest.main()

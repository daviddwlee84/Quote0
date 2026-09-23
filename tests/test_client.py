import json
import unittest
from unittest.mock import patch

import requests

from quote0 import BorderColor, ImageApiRequest, Quote0, TextApiRequest


class ClientTests(unittest.TestCase):
    def setUp(self):
        self.client = Quote0("test-key", "test-device")

    @staticmethod
    def response(body=None, status=200, raw=None):
        response = requests.Response()
        response.status_code = status
        response._content = raw if raw is not None else json.dumps(body).encode()
        return response

    @patch("quote0.client.requests.post")
    def test_image_uses_v2_route_and_preserves_all_options(self, post):
        body = {"message": "Image accepted"}
        post.return_value = self.response(body)
        result = self.client.send_image(
            "png-data",
            border=BorderColor.BLACK,
            refresh_now=False,
            link="https://example.com/image",
            dither_type="DIFFUSION",
            dither_kernel="ATKINSON",
        )
        self.assertTrue(result.success)
        self.assertEqual(result.message, "Image accepted")
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.response, body)
        post.assert_called_once_with(
            "https://dot.mindreset.tech/api/authV2/open/device/test-device/image",
            json={
                "refreshNow": False,
                "image": "png-data",
                "border": 1,
                "link": "https://example.com/image",
                "ditherType": "DIFFUSION",
                "ditherKernel": "ATKINSON",
            },
            headers={
                "Authorization": "Bearer test-key",
                "Content-Type": "application/json",
            },
            timeout=30,
        )

    @patch("quote0.client.requests.post")
    def test_text_uses_v2_route_and_preserves_all_options(self, post):
        post.return_value = self.response({"message": "accepted"})
        result = self.client.send_text(
            refresh_now=False,
            title="Title",
            message="Hello",
            signature="Signature",
            icon="png-icon",
            link="https://example.com/text",
        )
        self.assertTrue(result.success)
        self.assertEqual(result.message, "accepted")
        self.assertEqual(result.response, {"message": "accepted"})
        post.assert_called_once_with(
            "https://dot.mindreset.tech/api/authV2/open/device/test-device/text",
            json={
                "refreshNow": False,
                "title": "Title",
                "message": "Hello",
                "signature": "Signature",
                "icon": "png-icon",
                "link": "https://example.com/text",
            },
            headers={
                "Authorization": "Bearer test-key",
                "Content-Type": "application/json",
            },
            timeout=30,
        )

    @patch("quote0.client.requests.post")
    def test_default_payloads_omit_device_id_and_unused_options(self, post):
        post.return_value = self.response({})
        image_result = self.client.send_image("png")
        self.assertEqual(
            post.call_args.kwargs["json"],
            {"refreshNow": True, "image": "png", "border": 0},
        )
        self.assertEqual(image_result.message, "Image sent successfully!")
        text_result = self.client.send_text(message="Hello")
        self.assertEqual(
            post.call_args.kwargs["json"], {"refreshNow": True, "message": "Hello"}
        )
        self.assertEqual(text_result.message, "Text sent successfully!")

    @patch("quote0.client.requests.post")
    def test_device_id_is_encoded_as_one_url_segment(self, post):
        post.return_value = self.response({})
        client = Quote0("test-key", "device/with space?#%")
        for endpoint, send in (
            ("text", client.send_text),
            ("image", lambda: client.send_image("png")),
        ):
            with self.subTest(endpoint=endpoint):
                send()
                self.assertEqual(
                    post.call_args.args[0],
                    "https://dot.mindreset.tech/api/authV2/open/device/"
                    f"device%2Fwith%20space%3F%23%25/{endpoint}",
                )

    def test_exported_request_models_retain_device_id(self):
        for request in (
            ImageApiRequest(deviceId="test-device", image="png"),
            TextApiRequest(deviceId="test-device", message="Hello"),
        ):
            with self.subTest(model=type(request).__name__):
                self.assertEqual(request.deviceId, "test-device")
                self.assertEqual(request.model_dump()["deviceId"], "test-device")

    @patch("quote0.client.requests.post")
    def test_empty_response_remains_successful(self, post):
        post.return_value = self.response(status=204, raw=b"")
        result = self.client.send_text(message="Hello")
        self.assertTrue(result.success)
        self.assertEqual(result.status_code, 204)
        self.assertEqual(result.response, {})
        self.assertEqual(result.message, "Text sent successfully!")

    @patch("quote0.client.requests.post")
    def test_missing_or_unusable_server_message_uses_fallback(self, post):
        for message in (None, "", "  ", 200, {}):
            with self.subTest(message=message):
                post.return_value = self.response({"message": message})
                result = self.client.send_text()
                self.assertTrue(result.success)
                self.assertEqual(result.message, "Text sent successfully!")

    @patch("quote0.client.requests.post")
    def test_transport_failures_return_failure_without_response(self, post):
        for error in (
            requests.exceptions.ConnectionError("connection failed"),
            requests.exceptions.Timeout("request timed out"),
        ):
            for send in (self.client.send_text, lambda: self.client.send_image("png")):
                with self.subTest(error=type(error).__name__, send=send):
                    post.side_effect = error
                    result = send()
                    self.assertFalse(result.success)
                    self.assertIsNone(result.status_code)
                    self.assertIn(str(error), result.error)

    @patch("quote0.client.requests.post")
    def test_http_json_error_preserves_server_details(self, post):
        body = {
            "message": "Device or image content not found",
            "details": {"id": "missing"},
        }
        post.return_value = self.response(body, status=404)
        result = self.client.send_image("png")
        self.assertFalse(result.success)
        self.assertEqual(result.status_code, 404)
        self.assertEqual(result.response, body)
        self.assertIn("HTTP 404", result.error)
        self.assertIn(body["message"], result.error)
        self.assertIn(body["message"], result.message)
        post.assert_called_once()

    @patch("quote0.client.requests.post")
    def test_http_text_error_includes_status_and_body(self, post):
        post.return_value = self.response(status=503, raw=b"Service unavailable")
        result = self.client.send_image("png")
        self.assertFalse(result.success)
        self.assertEqual(result.status_code, 503)
        self.assertEqual(result.error, "HTTP 503: Service unavailable")
        self.assertIsNone(result.response)

    @patch("quote0.client.requests.post")
    def test_http_html_error_limits_body_excerpt(self, post):
        raw = "<html>" + "upstream failure " * 100 + "</html>"
        post.return_value = self.response(status=502, raw=raw.encode())
        result = self.client.send_text()
        self.assertFalse(result.success)
        self.assertEqual(result.error, "HTTP 502: " + raw[:500] + "...")

    @patch("quote0.client.requests.post")
    def test_http_empty_error_preserves_status(self, post):
        post.return_value = self.response(status=404, raw=b"")
        result = self.client.send_text()
        self.assertFalse(result.success)
        self.assertEqual(result.status_code, 404)
        self.assertEqual(result.response, {})
        self.assertEqual(result.error, "HTTP 404")

    @patch("quote0.client.requests.post")
    def test_http_non_object_error_preserves_status(self, post):
        post.return_value = self.response(["device missing"], status=404)
        result = self.client.send_text()
        self.assertFalse(result.success)
        self.assertEqual(result.status_code, 404)
        self.assertIn("device missing", result.error)
        self.assertIsNone(result.response)

    @patch("quote0.client.requests.post")
    def test_invalid_json_returns_failure(self, post):
        post.return_value = self.response(raw=b"<html>upstream error</html>")
        result = self.client.send_text()
        self.assertFalse(result.success)
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.error, "Invalid JSON response")

    @patch("quote0.client.requests.post")
    def test_non_object_json_returns_failure(self, post):
        for body in (None, [], 200, "ok"):
            with self.subTest(body=body):
                post.return_value = self.response(body)
                result = self.client.send_text()
                self.assertFalse(result.success)
                self.assertEqual(result.error, "Expected a JSON object response")

    @patch("quote0.client.requests.post")
    def test_http_status_controls_success_without_legacy_code_logic(self, post):
        for status, code, success in (
            (200, 500, True),
            (404, 200, False),
            (302, 200, False),
        ):
            with self.subTest(status=status, code=code):
                body = {"code": code, "message": "Server response"}
                post.return_value = self.response(body, status=status)
                result = self.client.send_image("png")
                self.assertEqual(result.success, success)
                self.assertEqual(result.status_code, status)
                self.assertEqual(result.response, body)


if __name__ == "__main__":
    unittest.main()

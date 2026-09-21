import json
import unittest
from unittest.mock import patch

import requests

from quote0 import BorderColor, Quote0


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
    def test_successful_image_preserves_payload_and_sets_timeout(self, post):
        post.return_value = self.response({"code": 200, "result": {}})
        result = self.client.send_image(
            "png-data", border=BorderColor.BLACK, refresh_now=False, dither_type="NONE"
        )
        self.assertTrue(result.success)
        self.assertEqual(result.message, "Image sent successfully!")
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.response, {"code": 200, "result": {}})
        post.assert_called_once_with(
            "https://dot.mindreset.tech/api/open/image",
            json={
                "refreshNow": False,
                "deviceId": "test-device",
                "image": "png-data",
                "border": 1,
                "ditherType": "NONE",
            },
            headers={
                "Authorization": "Bearer test-key",
                "Content-Type": "application/json",
            },
            timeout=30,
        )

    @patch("quote0.client.requests.post")
    def test_text_without_business_code_remains_successful(self, post):
        post.return_value = self.response({"message": "accepted"})
        result = self.client.send_text(message="Hello")
        self.assertTrue(result.success)
        self.assertEqual(result.message, "Text sent successfully!")
        self.assertEqual(result.response, {"message": "accepted"})
        self.assertEqual(
            post.call_args.args[0], "https://dot.mindreset.tech/api/open/text"
        )
        self.assertEqual(
            post.call_args.kwargs["json"],
            {"refreshNow": True, "deviceId": "test-device", "message": "Hello"},
        )
        self.assertEqual(post.call_args.kwargs["timeout"], 30)

    @patch("quote0.client.requests.post")
    def test_empty_response_remains_successful(self, post):
        post.return_value = self.response(status=204, raw=b"")
        result = self.client.send_text(message="Hello")
        self.assertTrue(result.success)
        self.assertEqual(result.status_code, 204)
        self.assertEqual(result.response, {})

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
    def test_http_failure_includes_status(self, post):
        post.return_value = self.response(status=503, raw=b"Service unavailable")
        result = self.client.send_image("png")
        self.assertFalse(result.success)
        self.assertEqual(result.status_code, 503)
        self.assertIn("503", result.error)

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
    def test_business_failure_with_http_success(self, post):
        for code in (400, 403, 404, 500):
            with self.subTest(code=code):
                body = {"code": code, "message": "device rejected", "result": {}}
                post.return_value = self.response(body)
                result = self.client.send_image("png")
                self.assertFalse(result.success)
                self.assertEqual(result.status_code, 200)
                self.assertEqual(result.response, body)
                self.assertIn(str(code), result.error)
                self.assertIn("device rejected", result.error)


if __name__ == "__main__":
    unittest.main()

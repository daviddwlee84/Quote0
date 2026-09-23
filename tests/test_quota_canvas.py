import json
import unittest
from datetime import datetime, timedelta, timezone

from quote0.apps.quota import ProviderQuota, QuotaWindow, _footer
from quote0.apps.quota_canvas import render_quota_canvas
from quote0.models import CanvasApiRequest


class QuotaCanvasTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 9, 23, 12, 0, tzinfo=timezone.utc)

    def quota(self, name="codex", remaining=50):
        return ProviderQuota(
            name,
            (
                QuotaWindow("primary", "5h", remaining, self.now + timedelta(hours=2)),
                QuotaWindow("secondary", "7d", 100, self.now + timedelta(days=2)),
                QuotaWindow("tertiary", "30d", None),
            ),
            updated_at=self.now - timedelta(minutes=3),
        )

    def test_all_densities_are_json_safe_and_within_canvas_limits(self):
        for count in range(1, 7):
            quotas = [self.quota("service-" + str(i)) for i in range(count)]
            payload = render_quota_canvas(quotas, now=self.now)
            CanvasApiRequest.model_validate(
                json.loads(json.dumps(payload, allow_nan=False))
            )
            self.assertEqual(len(payload["data"]["providers"]), count)
            self.assertEqual(payload["data"]["footer"], _footer(quotas, self.now))
            self.assertEqual(
                payload["windowData"]["default"][0]["props"]["style"]["width"], 296
            )
            self.assertEqual(
                payload["windowData"]["default"][0]["props"]["style"]["height"], 152
            )
            self.assertNotIn("data:image", json.dumps(payload))
            self.assertNotIn("api_key", json.dumps(payload))

    def test_zero_unknown_and_full_values(self):
        quotas = [
            self.quota("zero", 0),
            self.quota("unknown", None),
            self.quota("full", 100),
        ]
        data = render_quota_canvas(quotas, now=self.now)["data"]["providers"]
        self.assertEqual(
            [row["windows"][0]["percent"] for row in data], ["0%", "--", "100%"]
        )
        self.assertEqual([row["windows"][0]["barWidth"] for row in data], [0, 0, 280])
        self.assertEqual(data[0]["windows"][0]["reset"], "reset 2h")

    def test_cursor_counts_and_long_names(self):
        quota = ProviderQuota(
            "cursor",
            (
                QuotaWindow(
                    "primary", "Req", 95, self.now + timedelta(minutes=5), (25, 500)
                ),
            ),
            updated_at=self.now,
        )
        for quotas in ([quota], [quota, self.quota("long-provider-name-" * 4)]):
            payload = render_quota_canvas(quotas, now=self.now)
            row = payload["data"]["providers"][0]
            self.assertEqual(row["first"], "475/500")
            self.assertEqual(row["second"], "left 95%")
            self.assertEqual(row["windows"][0]["detail"], "25/500 used")
            self.assertIn("ellipsis", json.dumps(payload))

    def test_errors_empty_windows_and_footer(self):
        failed = ProviderQuota("codex", error="timeout")
        payload = render_quota_canvas([failed], now=self.now)
        self.assertTrue(payload["data"]["providers"][0]["failed"])
        self.assertIn("Checked", payload["data"]["footer"])
        self.assertIn("ERR  Unavailable", json.dumps(payload))
        empty = render_quota_canvas([ProviderQuota("codex")], now=self.now)
        self.assertTrue(empty["data"]["providers"][0]["failed"])
        mixed = render_quota_canvas([failed, self.quota("claude")], now=self.now)
        self.assertEqual(mixed["data"]["footer"], "Updated 09-23 11:57")


if __name__ == "__main__":
    unittest.main()

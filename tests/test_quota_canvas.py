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

    def test_cards_keep_all_densities_within_canvas_limits(self):
        for count in range(1, 7):
            with self.subTest(count=count):
                quotas = [self.quota("service-" + str(i)) for i in range(count)]
                compact = render_quota_canvas(quotas, now=self.now)
                cards = render_quota_canvas(quotas, now=self.now, style="cards")
                CanvasApiRequest.model_validate(json.loads(json.dumps(cards)))
                self.assertEqual(cards["data"]["footer"], compact["data"]["footer"])
                for before, after in zip(
                    compact["data"]["providers"], cards["data"]["providers"]
                ):
                    for key in (
                        "name",
                        "windows",
                        "first",
                        "second",
                        "resets",
                        "failed",
                    ):
                        self.assertEqual(before[key], after[key])

    def test_three_cards_are_horizontal_and_ordered(self):
        quotas = [
            self.quota("codex", 0),
            self.quota("claude", 71),
            self.quota("gemini", 100),
        ]
        payload = render_quota_canvas(quotas, now=self.now, style="cards")
        root = payload["windowData"]["default"][0]["props"]
        body = root["children"][1]["props"]
        self.assertIn("flex-row", body["tw"])
        cards = body["children"]
        self.assertEqual(len(cards), 3)
        widths = [card["props"]["style"]["width"] for card in cards]
        self.assertEqual(widths, [92, 92, 92])
        self.assertEqual(sum(widths) + 2 * body["style"]["gap"], 288)
        for index, card in enumerate(cards):
            self.assertIn(f"providers.{index}.name", json.dumps(card))
        self.assertEqual(
            [p["primary"]["percent"] for p in payload["data"]["providers"]],
            ["0%", "71%", "100%"],
        )

    def test_cards_do_not_substitute_secondary_for_missing_primary(self):
        quota = ProviderQuota("codex", (QuotaWindow("secondary", "7d", 80),))
        provider = render_quota_canvas([quota], now=self.now, style="cards")["data"][
            "providers"
        ][0]
        self.assertEqual(provider["primary"]["percent"], "--")
        self.assertEqual(provider["secondary"]["percent"], "80%")
        failed = render_quota_canvas(
            [ProviderQuota("codex", error="timeout"), self.quota("claude")],
            now=self.now,
            style="cards",
        )
        self.assertTrue(failed["data"]["providers"][0]["failed"])
        self.assertIn("ERR", json.dumps(failed["windowData"]))
        with self.assertRaises(ValueError):
            render_quota_canvas([quota], style="unknown")

    def test_cards_preserve_request_counts(self):
        quota = ProviderQuota(
            "cursor", (QuotaWindow("primary", "Req", 95, self.now, (25, 500)),)
        )
        for quotas in ([quota], [quota, self.quota("codex"), self.quota("claude")]):
            provider = render_quota_canvas(quotas, now=self.now, style="cards")["data"][
                "providers"
            ][0]
            self.assertEqual(provider["primary"]["percent"], "95%")
            self.assertEqual(provider["cardSecondary"], "25/500 used")

    def test_card_themes_keep_text_legible_and_data_unchanged(self):
        def inspect(node, background, card_colors):
            if isinstance(node, list):
                for child in node:
                    inspect(child, background, card_colors)
                return
            if not isinstance(node, dict):
                return
            props = node.get("props", {})
            style = props.get("style", {})
            background = style.get("backgroundColor", background)
            if node.get("type") == "span":
                self.assertIn(style.get("color"), ("black", "white"))
                self.assertNotEqual(style["color"], background)
            if style.get("borderRadius") == 7:
                card_colors.append(background)
            inspect(props.get("children"), background, card_colors)

        for count in range(1, 7):
            quotas = [self.quota("service-" + str(i)) for i in range(count)]
            for failed in (False, True):
                current = list(quotas)
                if failed:
                    current[0] = ProviderQuota(current[0].provider, error="timeout")
                reference = render_quota_canvas(current, now=self.now, style="cards")
                for theme in ("light", "dark", "alternating"):
                    with self.subTest(count=count, failed=failed, theme=theme):
                        payload = render_quota_canvas(
                            current, now=self.now, style="cards", card_theme=theme
                        )
                        CanvasApiRequest.model_validate(payload)
                        self.assertEqual(payload["data"], reference["data"])
                        self.assertEqual(payload["border"], 1 if theme == "dark" else 0)
                        card_colors = []
                        inspect(payload["windowData"]["default"], None, card_colors)
                        self.assertTrue(card_colors)
                        if theme != "alternating":
                            self.assertEqual(
                                set(card_colors),
                                {"white" if theme == "light" else "black"},
                            )
                        else:
                            self.assertEqual(payload, reference)

    def test_non_card_layout_rejects_theme_options(self):
        for theme in ("light", "dark", "invalid"):
            with self.subTest(theme=theme), self.assertRaises(ValueError):
                render_quota_canvas([self.quota()], now=self.now, card_theme=theme)


if __name__ == "__main__":
    unittest.main()

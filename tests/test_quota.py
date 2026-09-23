import json
import subprocess
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from PIL import ImageDraw

from quote0.apps.quota import (
    ProviderQuota,
    QuotaWindow,
    fetch_quotas,
    render_quota,
    validate_providers,
)


NOW = datetime(2026, 9, 22, 12, 0, tzinfo=timezone.utc)


def snapshot(provider="codex", **usage):
    fields = {
        "primary": {
            "usedPercent": 28,
            "windowMinutes": 300,
            "resetsAt": "2026-09-22T14:30:00Z",
        },
        "secondary": {"usedPercent": 59, "windowMinutes": 10080},
        "updatedAt": "2026-09-22T11:59:00Z",
    }
    fields.update(usage)
    return {"provider": provider, "source": "oauth", "usage": fields}


def result(rows, code=0):
    return subprocess.CompletedProcess([], code, json.dumps(rows), "")


class FetchQuotaTests(unittest.TestCase):
    def test_provider_validation(self):
        validate_providers(["codex", "claude", "azure-openai"])
        for providers in (
            [],
            ["codex"] * 2,
            ["x" + str(i) for i in range(7)],
            ["all"],
            ["both"],
            ["--source"],
            ["Claude"],
            "codex",
        ):
            with self.subTest(providers=providers), self.assertRaises(ValueError):
                validate_providers(providers)

    @patch("quote0.apps.quota.subprocess.run")
    def test_order_current_accounts_and_remaining_windows(self, run):
        run.side_effect = [result([snapshot("claude")]), result([snapshot()])]
        rows = fetch_quotas(["claude", "codex"])
        self.assertEqual([row.provider for row in rows], ["claude", "codex"])
        self.assertEqual(rows[0].windows[0].remaining_percent, 72)
        self.assertEqual(rows[0].windows[0].label, "5h")
        self.assertEqual(rows[0].windows[1].label, "7d")
        self.assertEqual(rows[0].source, "oauth")
        self.assertEqual(rows[0].updated_at, NOW - timedelta(minutes=1))
        self.assertEqual(rows[0].windows[0].resets_at, NOW + timedelta(minutes=150))
        self.assertFalse(any(row.error for row in rows))
        self.assertEqual(
            run.call_args_list[0].args[0],
            ["codexbar", "usage", "--provider", "claude", "--json", "--json-only"],
        )
        self.assertEqual(run.call_args.kwargs["timeout"], 120)

    @patch("quote0.apps.quota.subprocess.run")
    def test_custom_timeout_and_invalid_limits(self, run):
        run.return_value = result([snapshot()])
        fetch_quotas(["codex"], timeout=90)
        self.assertEqual(run.call_args.kwargs["timeout"], 90)
        run.reset_mock()
        for timeout in (0, -1, float("inf"), float("nan"), True, "120"):
            with (
                self.subTest(timeout=timeout),
                self.assertRaisesRegex(ValueError, "timeout"),
            ):
                fetch_quotas(["codex"], timeout=timeout)
        run.assert_not_called()

    @patch("quote0.apps.quota.subprocess.run")
    def test_partial_failure_does_not_discard_other_provider(self, run):
        run.side_effect = [
            result([{"provider": "claude", "error": {"message": "Sign in again"}}], 1),
            result([snapshot()]),
        ]
        rows = fetch_quotas(["claude", "codex"])
        self.assertEqual(rows[0].error, "Sign in again")
        self.assertIsNone(rows[1].error)
        self.assertEqual(rows[1].windows[0].remaining_percent, 72)

    @patch("quote0.apps.quota.subprocess.run")
    def test_nonzero_output_is_still_parsed(self, run):
        run.return_value = result([snapshot()], 4)
        row = fetch_quotas(["codex"])[0]
        self.assertIn("status 4", row.error)
        self.assertEqual(row.windows[0].remaining_percent, 72)

    @patch("quote0.apps.quota.subprocess.run")
    def test_timeout_invalid_json_and_success_are_separate(self, run):
        run.side_effect = [
            subprocess.TimeoutExpired("codexbar", 30),
            subprocess.CompletedProcess([], 1, "not JSON", "diagnostic"),
            result([snapshot("gemini")]),
        ]
        rows = fetch_quotas(["codex", "claude", "gemini"], timeout=30)
        self.assertIn("30s", rows[0].error)
        self.assertIn("invalid JSON", rows[1].error)
        self.assertIsNone(rows[2].error)
        self.assertIn("--timeout", rows[0].error)

    @patch("quote0.apps.quota.subprocess.run")
    def test_cursor_legacy_request_quota(self, run):
        run.return_value = result(
            [
                snapshot(
                    "cursor",
                    primary={
                        "usedPercent": 5,
                        "windowMinutes": 43200,
                        "resetDescription": "25 / 500 requests",
                        "resetsAt": "2026-10-11T03:26:36Z",
                    },
                    secondary=None,
                )
            ]
        )
        row = fetch_quotas(["cursor"])[0]
        self.assertIsNone(row.error)
        self.assertEqual(len(row.windows), 1)
        window = row.windows[0]
        self.assertEqual(window.label, "Req")
        self.assertEqual(window.request_usage, (25, 500))
        self.assertEqual(window.remaining_percent, 95)
        self.assertEqual(
            window.resets_at, datetime(2026, 10, 11, 3, 26, 36, tzinfo=timezone.utc)
        )

    @patch("quote0.apps.quota.subprocess.run")
    def test_cursor_request_details_fallback_and_exhaustion(self, run):
        for used, limit, remaining in (
            (25, 500, 95),
            (600, 500, 0),
            (0, 500, 100),
            (1250, 5000, 75),
        ):
            with self.subTest(used=used):
                run.return_value = result(
                    [
                        snapshot(
                            "cursor",
                            primary={},
                            secondary=None,
                            details=[
                                {
                                    "rows": [
                                        {
                                            "label": "Request quota",
                                            "value": f"{used:,} / {limit:,}",
                                        }
                                    ]
                                }
                            ],
                        )
                    ]
                )
                window = fetch_quotas(["cursor"])[0].windows[0]
                self.assertEqual(window.request_usage, (used, limit))
                self.assertEqual(window.remaining_percent, remaining)

    @patch("quote0.apps.quota.subprocess.run")
    def test_request_counts_are_not_invented_for_other_plans(self, run):
        for description in (
            None,
            "25 / unlimited requests",
            "25 / 0 requests",
            "-1 / 500 requests",
            "resets in 3 days",
            "12.5 / 500 requests",
        ):
            with self.subTest(description=description):
                run.return_value = result(
                    [
                        snapshot(
                            "cursor",
                            primary={
                                "usedPercent": 5,
                                "windowMinutes": 43200,
                                "resetDescription": description,
                            },
                            details={"rows": []},
                        )
                    ]
                )
                window = fetch_quotas(["cursor"])[0].windows[0]
                self.assertIsNone(window.request_usage)
                self.assertEqual(window.remaining_percent, 95)
                self.assertEqual(window.label, "30d")
        run.return_value = result(
            [
                snapshot(
                    primary={"usedPercent": 5, "resetDescription": "25 / 500 requests"}
                )
            ]
        )
        self.assertIsNone(fetch_quotas(["codex"])[0].windows[0].request_usage)

    @patch("quote0.apps.quota.subprocess.run")
    def test_missing_fields_invalid_numbers_and_clamping(self, run):
        run.return_value = result(
            [
                snapshot(
                    primary={"usedPercent": -20},
                    secondary={"usedPercent": 150, "resetsAt": "broken"},
                    tertiary={"usedPercent": True},
                    updatedAt=None,
                )
            ]
        )
        row = fetch_quotas(["codex"])[0]
        self.assertEqual([w.remaining_percent for w in row.windows], [100, 0, None])
        self.assertEqual([w.label for w in row.windows], ["P", "S", "T"])
        self.assertIsNone(row.updated_at)
        self.assertIsNone(row.windows[1].resets_at)
        for used in ("30", None, float("nan"), float("inf")):
            run.return_value = result([snapshot(primary={"usedPercent": used})])
            self.assertIsNone(fetch_quotas(["codex"])[0].windows[0].remaining_percent)

    @patch("quote0.apps.quota.subprocess.run")
    def test_missing_ambiguous_or_unexpected_snapshot_is_error(self, run):
        for payload in (
            snapshot(),
            [],
            [snapshot("claude")],
            [snapshot(), snapshot()],
            [{"provider": "codex"}],
            [snapshot(primary=None, secondary=None)],
        ):
            with self.subTest(payload=payload):
                run.return_value = result(payload)
                self.assertTrue(fetch_quotas(["codex"])[0].error)

    @patch("quote0.apps.quota.subprocess.run", side_effect=FileNotFoundError)
    def test_missing_executable_has_actionable_error(self, run):
        with self.assertRaisesRegex(FileNotFoundError, "Install codexbar"):
            fetch_quotas(["codex"])


class RenderQuotaTests(unittest.TestCase):
    def rows(self, count):
        return [
            ProviderQuota(
                provider="provider" + str(index),
                windows=(
                    QuotaWindow("primary", "5h", 72, NOW + timedelta(hours=2)),
                    QuotaWindow("secondary", "7d", 41),
                    QuotaWindow("tertiary", "T", None),
                ),
                updated_at=NOW - timedelta(minutes=index + 1),
            )
            for index in range(count)
        ]

    def capture(self, rows):
        original = ImageDraw.ImageDraw.text
        with patch.object(
            ImageDraw.ImageDraw, "text", autospec=True, side_effect=original
        ) as drawing:
            image = render_quota(rows, now=NOW)
        return image, [
            (call.args[1], call.args[2], call.kwargs["font"])
            for call in drawing.call_args_list
        ]

    def test_all_layouts_fit_and_use_readable_fonts(self):
        for count in range(1, 7):
            with self.subTest(count=count):
                image, texts = self.capture(self.rows(count))
                self.assertEqual(image.size, (296, 152))
                self.assertEqual(image.mode, "1")
                self.assertEqual(set(image.getdata()), {0, 1})
                for (x, y), text, font in texts:
                    self.assertGreaterEqual(font.size, 10 if y == 139 else 12)
                    self.assertLessEqual(x + font.getlength(text), 290)
                    self.assertLess(
                        y + font.getbbox(text)[3] - font.getbbox(text)[1], 152
                    )
                self.assertEqual(
                    texts[-1][1], "Updated 09-22 11:{:02d}".format(60 - count)
                )

    def test_tertiary_reset_unknown_and_density_semantics(self):
        _, single = self.capture(self.rows(1))
        self.assertIn("--", [text for _, text, _ in single])
        self.assertIn("reset 2h", [text for _, text, _ in single])
        _, medium = self.capture(self.rows(3))
        self.assertTrue(any("reset P 2h" in text for _, text, _ in medium))
        _, dense = self.capture(self.rows(6))
        self.assertFalse(any("reset" in text for _, text, _ in dense))

    def test_all_failures_show_checked_time_and_no_fabricated_percent(self):
        _, texts = self.capture([ProviderQuota("codex", error="login failed")])
        strings = [text for _, text, _ in texts]
        self.assertIn("Checked 09-22 12:00", strings)
        self.assertFalse(any("%" in text for text in strings))
        self.assertTrue(any("Unavailable" in text for text in strings))

    def test_long_provider_name_is_measured_and_truncated(self):
        rows = self.rows(6)
        rows[0] = ProviderQuota("an-extremely-long-provider-name", error="failed")
        _, texts = self.capture(rows)
        self.assertTrue(any("…" in text for _, text, _ in texts))

    def test_request_quota_is_readable_in_all_layouts(self):
        for count in range(1, 7):
            with self.subTest(count=count):
                rows = self.rows(count)
                rows[0] = ProviderQuota(
                    "cursor",
                    (
                        QuotaWindow(
                            "primary", "Req", 95, NOW + timedelta(days=17), (25, 500)
                        ),
                    ),
                )
                _, texts = self.capture(rows)
                strings = [text for _, text, _ in texts]
                if count == 1:
                    self.assertIn("25/500 used", strings)
                    self.assertIn("95%", strings)
                    self.assertIn("reset 17d", strings)
                else:
                    self.assertIn("475/500", strings)
                    self.assertIn("left 95%", strings)
                    if count <= 3:
                        self.assertIn("Req 25/500 used · reset 17d", strings)
                for (x, y), text, font in texts:
                    self.assertLessEqual(x + font.getlength(text), 290)
                    self.assertLess(
                        y + font.getbbox(text)[3] - font.getbbox(text)[1], 152
                    )


if __name__ == "__main__":
    unittest.main()

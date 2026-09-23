import json
import unittest
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from PIL import ImageDraw

from quote0.apps.quota import ProviderQuota, QuotaWindow, _parse, render_quota
from quote0.apps.quota_pace import (
    QuotaPace,
    display_pair,
    display_windows,
    long_window,
    pace_hint,
    parse_pace,
)
from quote0.apps.quota_canvas import render_quota_canvas
from quote0.models import CanvasApiRequest

NOW = datetime(2026, 9, 23, 12, 0, tzinfo=timezone.utc)


def pace_payload(delta=13, expected=33, stage="farAhead", **extra):
    return dict(
        stage=stage,
        deltaPercent=delta,
        expectedUsedPercent=expected,
        willLastToReset=False,
        etaSeconds=235800,
        **extra,
    )


def provider(name="codex", **overrides):
    weekly = QuotaWindow(
        "secondary",
        "7d",
        54,
        NOW + timedelta(days=4),
        None,
        10080,
        parse_pace(pace_payload(), 54, NOW),
    )
    values = dict(
        provider=name,
        windows=(
            QuotaWindow("primary", "5h", 100, NOW + timedelta(hours=5), None, 300),
            weekly,
        ),
        updated_at=NOW,
    )
    values.update(overrides)
    return ProviderQuota(**values)


class PaceParsingTests(unittest.TestCase):
    def parse(self, paces=None, **usage_overrides):
        usage = dict(
            primary={"usedPercent": 0, "windowMinutes": 300},
            secondary={
                "usedPercent": 46,
                "windowMinutes": 10080,
                "resetsAt": (NOW + timedelta(days=4)).isoformat(),
            },
            updatedAt=(NOW - timedelta(minutes=10)).isoformat(),
        )
        usage.update(usage_overrides)
        row = dict(provider="codex", usage=usage, pace=paces)
        return _parse("codex", json.dumps([row]), 0, observed_at=NOW)

    def test_parse_optional_pace_and_preserve_duration(self):
        quota = self.parse({"secondary": pace_payload()})
        self.assertIsNone(quota.error)
        self.assertEqual(quota.windows[1].window_minutes, 10080)
        pace = quota.windows[1].pace
        self.assertEqual(pace.observed_at, NOW)
        self.assertEqual(pace.exhausts_at, NOW + timedelta(seconds=235800))
        self.assertEqual(pace_hint(quota, NOW).summary, "7d OVER 13pp")
        self.assertEqual(pace_hint(quota, NOW).forecast, "OUT ~2d17h")
        self.assertEqual(pace_hint(quota, NOW).expected_remaining_percent, 67)
        self.assertEqual(
            pace_hint(quota, NOW + timedelta(hours=1)).forecast, "OUT ~2d16h"
        )

    def test_cursor_monthly_counts_and_claude_reserve(self):
        payload = {
            "provider": "cursor",
            "usage": {
                "primary": {
                    "usedPercent": 5,
                    "windowMinutes": 43200,
                    "resetDescription": "25 / 500 requests",
                    "resetsAt": (NOW + timedelta(days=17)).isoformat(),
                }
            },
            "pace": {
                "primary": {
                    "stage": "farBehind",
                    "deltaPercent": -36,
                    "expectedUsedPercent": 41,
                    "willLastToReset": True,
                }
            },
        }
        quota = _parse("cursor", json.dumps([payload]), 0, observed_at=NOW)
        self.assertEqual(quota.windows[0].request_usage, (25, 500))
        self.assertEqual(pace_hint(quota, NOW).summary, "30d RES 36pp")
        self.assertEqual(pace_hint(quota, NOW).forecast, "~TO RESET")
        payload["usage"]["primary"]["resetDescription"] = "250 / 500 requests"
        inconsistent = _parse("cursor", json.dumps([payload]), 0, observed_at=NOW)
        self.assertEqual(inconsistent.windows[0].remaining_percent, 50)
        self.assertIsNone(inconsistent.windows[0].pace)
        self.assertIsNone(inconsistent.error)
        quota = self.parse(
            {
                "secondary": {
                    "stage": "behind",
                    "deltaPercent": -8,
                    "expectedUsedPercent": 8,
                    "willLastToReset": True,
                }
            },
            secondary={
                "usedPercent": 0,
                "windowMinutes": 10080,
                "resetsAt": (NOW + timedelta(days=6)).isoformat(),
            },
        )
        self.assertEqual(pace_hint(quota, NOW).summary, "7d RES 8pp")

    def test_rounding_tolerance_and_invalid_data_degrade_only_pace(self):
        self.assertIsNotNone(parse_pace(pace_payload(), 53, NOW))
        self.assertIsNone(parse_pace(pace_payload(), 52.99, NOW))
        for raw in (
            None,
            [],
            "bad",
            {"summary": "13% in deficit"},
            {**pace_payload(), "deltaPercent": True},
            {**pace_payload(), "deltaPercent": float("nan")},
            {**pace_payload(), "expectedUsedPercent": 101},
            {**pace_payload(), "willLastToReset": 1},
            {**pace_payload(), "etaSeconds": -1},
            {**pace_payload(), "etaSeconds": float("inf")},
            {**pace_payload(), "etaSeconds": 1e300},
            {**pace_payload(), "stage": []},
            {**pace_payload(), "stage": "onTrack"},
            {**pace_payload(), "stage": "farBehind"},
        ):
            with self.subTest(raw=raw):
                quota = self.parse({"secondary": raw})
                self.assertIsNone(quota.error)
                self.assertEqual(quota.windows[1].remaining_percent, 54)
                self.assertIsNone(quota.windows[1].pace)
        for value in (None, [], "bad"):
            self.assertIsNone(self.parse(value).windows[1].pace)

    def test_unknown_duration_and_missing_or_expired_reset(self):
        quota = provider()
        window = quota.windows[1]
        for changed in (
            replace(window, window_minutes=None),
            replace(window, resets_at=None),
            replace(window, resets_at=NOW),
            replace(window, resets_at=NOW + timedelta(days=8)),
        ):
            self.assertEqual(
                pace_hint(replace(quota, windows=(changed,)), NOW).summary, "PACE --"
            )
        self.assertEqual(
            pace_hint(replace(quota, error="timeout"), NOW).summary, "PACE --"
        )
        self.assertEqual(
            pace_hint(quota, NOW - timedelta(minutes=1)).summary, "PACE --"
        )
        self.assertEqual(pace_hint(quota, NOW + timedelta(days=4)).summary, "PACE --")

    def test_on_track_zero_eta_unknown_eta_and_timezone_equivalence(self):
        for remaining, raw, expected in (
            (67, pace_payload(delta=0, expected=33, stage="onTrack"), "7d ON PACE"),
            (
                100,
                {
                    "stage": "farBehind",
                    "deltaPercent": -33,
                    "expectedUsedPercent": 33,
                    "willLastToReset": True,
                },
                "7d RES 33pp",
            ),
            (0, {**pace_payload(delta=67), "etaSeconds": 0}, "7d OVER 67pp"),
        ):
            p = parse_pace(raw, remaining, NOW)
            quota = provider(
                windows=(
                    QuotaWindow(
                        "primary",
                        "7d",
                        remaining,
                        NOW + timedelta(days=4),
                        None,
                        10080,
                        p,
                    ),
                )
            )
            self.assertEqual(pace_hint(quota, NOW).summary, expected)
            self.assertEqual(
                pace_hint(quota, NOW),
                pace_hint(quota, NOW.astimezone(timezone(timedelta(hours=8)))),
            )
            if remaining == 0:
                self.assertEqual(pace_hint(quota, NOW).forecast, "OUT ~now")
        p = parse_pace(
            {k: v for k, v in pace_payload().items() if k != "etaSeconds"}, 54, NOW
        )
        quota = provider(windows=(replace(provider().windows[1], pace=p),))
        self.assertEqual(pace_hint(quota, NOW).forecast, "ETA --")


class FocusTests(unittest.TestCase):
    def test_longest_known_period_and_stable_slot_ties(self):
        windows = (
            QuotaWindow("primary", "Req", 95, window_minutes=43200),
            QuotaWindow("secondary", "7d", 54, window_minutes=10080),
            QuotaWindow("tertiary", "30d", 80, window_minutes=43200),
        )
        self.assertEqual(long_window(windows).slot, "primary")
        tied = tuple(replace(w, window_minutes=10080) for w in windows)
        self.assertEqual(long_window(tied).slot, "secondary")
        self.assertEqual(
            [w.slot for w in display_windows(tied, "long")],
            ["secondary", "primary", "tertiary"],
        )
        self.assertEqual([w.slot for w in tied], ["primary", "secondary", "tertiary"])
        self.assertEqual(
            [w.slot for w in display_pair(tied, "long")], ["secondary", "primary"]
        )
        self.assertEqual(display_pair(tied, "primary"), (tied[0], tied[1]))

    def test_unknown_period_does_not_infer_from_label(self):
        windows = (
            QuotaWindow("primary", "7d", 90),
            QuotaWindow("secondary", "30d", 50),
        )
        self.assertIsNone(long_window(windows))
        self.assertEqual(display_windows(windows, "long"), windows)
        self.assertEqual(display_pair(windows, "long"), windows)
        self.assertIsNone(
            long_window((QuotaWindow("primary", "5h", 90, window_minutes=300),))
        )
        with self.assertRaises(ValueError):
            display_pair(windows, "bad")


class PaceRenderingTests(unittest.TestCase):
    def test_off_preserves_default_outputs_and_hides_pace_metadata(self):
        quotas = [provider(), provider("claude")]
        stripped = [
            replace(
                q,
                windows=tuple(
                    replace(w, pace=None, window_minutes=None) for w in q.windows
                ),
            )
            for q in quotas
        ]
        self.assertEqual(
            render_quota(quotas, now=NOW).tobytes(),
            render_quota(stripped, now=NOW).tobytes(),
        )
        for style in ("compact", "cards"):
            self.assertEqual(
                render_quota_canvas(quotas, now=NOW, style=style),
                render_quota_canvas(stripped, now=NOW, style=style),
            )
            self.assertNotIn(
                '"pace"', json.dumps(render_quota_canvas(quotas, now=NOW, style=style))
            )

    def test_all_renderers_densities_themes_and_toggle_combinations(self):
        for count in range(1, 7):
            quotas = [provider("service-" + str(i)) for i in range(count)]
            for focus in ("primary", "long"):
                for show in (False, True):
                    with self.subTest(count=count, focus=focus, pace=show):
                        image = render_quota(
                            quotas, now=NOW, pace=show, quota_focus=focus
                        )
                        self.assertEqual(image.size, (296, 152))
                        for style in ("compact", "cards"):
                            for theme in (
                                ("alternating",)
                                if style == "compact"
                                else ("light", "dark", "alternating")
                            ):
                                payload = render_quota_canvas(
                                    quotas,
                                    now=NOW,
                                    style=style,
                                    card_theme=theme,
                                    pace=show,
                                    quota_focus=focus,
                                )
                                CanvasApiRequest.model_validate(payload)
                                view = payload["data"]["providers"][0]
                                self.assertEqual(
                                    view["windows"][0]["slot"],
                                    "secondary" if focus == "long" else "primary",
                                )
                                if show:
                                    self.assertEqual(
                                        view["pace"]["summary"], "7d OVER 13pp"
                                    )
                                    for w in view["windows"]:
                                        self.assertEqual(
                                            w["paceMarker"],
                                            67 if w["slot"] == "secondary" else None,
                                        )
                                else:
                                    self.assertNotIn("pace", view)

    def test_image_pace_text_and_geometry(self):
        for count in range(1, 7):
            original = ImageDraw.ImageDraw.text
            with patch.object(
                ImageDraw.ImageDraw, "text", autospec=True, side_effect=original
            ) as drawing:
                render_quota(
                    [provider("provider-" + str(i)) for i in range(count)],
                    now=NOW,
                    pace=True,
                    quota_focus="long",
                )
            text = [call.args[2] for call in drawing.call_args_list]
            self.assertTrue(any("pp" in s for s in text))
            self.assertEqual(any("OUT ~" in s for s in text), count <= 4)
            for call in drawing.call_args_list:
                (x, y), string, font = call.args[1], call.args[2], call.kwargs["font"]
                self.assertLessEqual(x + font.getlength(string), 290)
                self.assertLess(
                    y + font.getbbox(string)[3] - font.getbbox(string)[1], 152
                )

    def test_card_focus_preserves_request_counts_and_remaining_slots(self):
        windows = (
            QuotaWindow("primary", "5h", 90, window_minutes=300),
            QuotaWindow("secondary", "7d", 54, window_minutes=10080),
            QuotaWindow("tertiary", "30d", 80, window_minutes=43200),
        )
        payload = render_quota_canvas(
            [provider(windows=windows)],
            now=NOW,
            style="cards",
            quota_focus="long",
            pace=True,
        )
        row = payload["data"]["providers"][0]
        self.assertEqual(row["primary"]["slot"], "tertiary")
        self.assertEqual(row["secondary"]["slot"], "primary")
        self.assertEqual(
            {w["slot"] for w in row["windows"]}, {"primary", "secondary", "tertiary"}
        )
        cursor = provider(
            "cursor",
            windows=(
                QuotaWindow(
                    "primary", "Req", 95, NOW + timedelta(days=17), (25, 500), 43200
                ),
            ),
        )
        payload = render_quota_canvas(
            [provider(), cursor], now=NOW, style="cards", quota_focus="long", pace=True
        )
        self.assertEqual(
            payload["data"]["providers"][1]["cardSecondary"], "25/500 used"
        )

    def test_failure_and_unknown_pace_keep_unknown_states(self):
        failed = provider(error="timeout")
        for count in (1, 3, 6):
            rows = [failed] + [provider("service-" + str(i)) for i in range(count - 1)]
            for style in ("compact", "cards"):
                payload = render_quota_canvas(rows, now=NOW, style=style, pace=True)
                self.assertTrue(payload["data"]["providers"][0]["failed"])
                self.assertEqual(
                    payload["data"]["providers"][0]["pace"]["summary"], "PACE --"
                )
                self.assertIn("ERR", json.dumps(payload["windowData"]))


if __name__ == "__main__":
    unittest.main()

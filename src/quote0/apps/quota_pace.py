"""CodexBar pace normalization and shared, renderer-independent presentation rules."""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Optional, Sequence, TYPE_CHECKING

if TYPE_CHECKING:
    from .quota import ProviderQuota, QuotaWindow

STAGES = {
    "onTrack",
    "slightlyAhead",
    "ahead",
    "farAhead",
    "slightlyBehind",
    "behind",
    "farBehind",
}


@dataclass(frozen=True)
class QuotaPace:
    stage: str
    delta_percent: float
    expected_used_percent: float
    will_last_to_reset: bool
    observed_at: datetime
    exhausts_at: Optional[datetime] = None


@dataclass(frozen=True)
class PaceHint:
    slot: Optional[str] = None
    summary: str = "PACE --"
    compact: str = "PACE --"
    forecast: str = "ETA --"
    expected_remaining_percent: Optional[float] = None


def _number(value: Any) -> Optional[float]:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    try:
        result = float(value)
    except (ValueError, OverflowError):
        return None
    return result if math.isfinite(result) else None


def _aware(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)


def parse_pace(
    value: Any, remaining: Optional[float], observed_at: datetime
) -> Optional[QuotaPace]:
    """Invalid optional pace never invalidates the underlying quota snapshot."""
    if not isinstance(value, dict):
        return None
    stage = value.get("stage")
    if not isinstance(stage, str) or stage not in STAGES:
        return None
    delta, expected = _number(value.get("deltaPercent")), _number(
        value.get("expectedUsedPercent")
    )
    actual_remaining = _number(remaining)
    lasts = value.get("willLastToReset")
    if (
        delta is None
        or expected is None
        or actual_remaining is None
        or not -100 <= delta <= 100
        or not 0 <= expected <= 100
        or not 0 <= actual_remaining <= 100
        or type(lasts) is not bool
    ):
        return None
    # CLI rounds expected and delta independently. Allow at most one percentage point.
    if abs((100 - actual_remaining) - expected - delta) > 1.000001:
        return None
    if stage == "onTrack" and abs(delta) > 2.000001:
        return None
    if ("Ahead" in stage or stage == "ahead") and delta < 0:
        return None
    if ("Behind" in stage or stage == "behind") and delta > 0:
        return None
    eta = value.get("etaSeconds")
    if eta is not None:
        eta = _number(eta)
        if eta is None or eta < 0:
            return None
    observed = _aware(observed_at)
    try:
        exhausts = (
            observed + timedelta(seconds=eta) if eta is not None and not lasts else None
        )
    except (OverflowError, ValueError):
        return None
    return QuotaPace(stage, delta, expected, lasts, observed, exhausts)


def long_window(windows: Sequence[QuotaWindow]) -> Optional[QuotaWindow]:
    priorities = {"secondary": 3, "primary": 2, "tertiary": 1}
    candidates = [w for w in windows if (_number(w.window_minutes) or 0) >= 1440]
    return max(
        candidates,
        key=lambda w: (w.window_minutes, priorities.get(w.slot, 0)),
        default=None,
    )


def validate_focus(focus: str) -> None:
    if focus not in ("primary", "long"):
        raise ValueError("Quota focus must be primary or long")


def display_windows(windows: Sequence[QuotaWindow], focus: str) -> tuple:
    validate_focus(focus)
    selected = long_window(windows) if focus == "long" else None
    if selected is None:
        return tuple(windows)
    return (selected,) + tuple(w for w in windows if w.slot != selected.slot)


def display_pair(windows: Sequence[QuotaWindow], focus: str) -> tuple:
    validate_focus(focus)
    selected = long_window(windows) if focus == "long" else None
    by_slot = {w.slot: w for w in windows}
    if selected is None:
        return by_slot.get("primary"), by_slot.get("secondary")
    other = next(
        (
            by_slot[s]
            for s in ("primary", "secondary", "tertiary")
            if s != selected.slot and s in by_slot
        ),
        None,
    )
    return selected, other


def _period(minutes: float) -> str:
    if minutes % 1440 == 0:
        return f"{minutes / 1440:g}d"
    if minutes % 60 == 0:
        return f"{minutes / 60:g}h"
    return f"{minutes:g}m"


def duration_text(seconds: float) -> str:
    minutes = max(0, math.ceil(seconds / 60))
    if not minutes:
        return "now"
    days, rest = divmod(minutes, 1440)
    hours, minutes = divmod(rest, 60)
    if days:
        return f"{days}d{hours}h" if hours else f"{days}d"
    return (
        f"{hours}h{minutes}m"
        if hours and minutes
        else f"{hours}h" if hours else f"{minutes}m"
    )


def pace_hint(quota: ProviderQuota, now: datetime) -> PaceHint:
    window = long_window(quota.windows)
    if quota.error or window is None or window.pace is None or window.resets_at is None:
        return PaceHint()
    pace = window.pace
    current, resets = _aware(now), _aware(window.resets_at)
    try:
        starts = resets - timedelta(minutes=window.window_minutes)
    except (ValueError, OverflowError):
        return PaceHint()
    if not starts <= current < resets or current < _aware(pace.observed_at):
        return PaceHint()
    # Validate manually-created SDK values too, without advancing the snapshot's delta.
    source = {
        "stage": pace.stage,
        "deltaPercent": pace.delta_percent,
        "expectedUsedPercent": pace.expected_used_percent,
        "willLastToReset": pace.will_last_to_reset,
    }
    if parse_pace(source, window.remaining_percent, pace.observed_at) is None:
        return PaceHint()
    label = _period(window.window_minutes)
    magnitude = math.floor(abs(pace.delta_percent) + 0.5)
    if pace.stage == "onTrack" or magnitude == 0:
        summary, compact = f"{label} ON PACE", f"{label} OK"
    else:
        status, sign = ("OVER", "+") if pace.delta_percent > 0 else ("RES", "-")
        summary = f"{label} {status} {magnitude}pp"
        compact = f"{label} {sign}{magnitude}pp"
    forecast = "ETA --"
    if pace.will_last_to_reset:
        forecast = "~TO RESET"
    elif pace.exhausts_at is not None:
        forecast = "OUT ~" + duration_text(
            (_aware(pace.exhausts_at) - current).total_seconds()
        )
    return PaceHint(
        window.slot, summary, compact, forecast, 100 - pace.expected_used_percent
    )

"""Fetch CodexBar quota snapshots and render a 296 × 152 dashboard."""

import json
import math
import re
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any, List, Optional, Sequence, Tuple

from PIL import Image, ImageDraw, ImageFont

from .quota_pace import (
    QuotaPace,
    parse_pace,
    display_pair,
    display_windows,
    pace_hint,
    validate_focus,
)


@dataclass(frozen=True)
class QuotaWindow:
    slot: str
    label: str
    remaining_percent: Optional[float] = None
    resets_at: Optional[datetime] = None
    request_usage: Optional[Tuple[int, int]] = None
    window_minutes: Optional[float] = None
    pace: Optional[QuotaPace] = None


@dataclass(frozen=True)
class ProviderQuota:
    provider: str
    windows: Tuple[QuotaWindow, ...] = ()
    updated_at: Optional[datetime] = None
    source: Optional[str] = None
    error: Optional[str] = None


_SLOTS = ("primary", "secondary", "tertiary")
_SLOT_LABELS = {"primary": "P", "secondary": "S", "tertiary": "T"}
_PROVIDER_NAMES = {
    "codex": "Codex",
    "claude": "Claude",
    "gemini": "Gemini",
    "copilot": "Copilot",
    "openai": "OpenAI",
    "azure-openai": "Azure OpenAI",
    "antigravity": "Antigravity",
    "opencode": "OpenCode",
    "opencodego": "OpenCode Go",
}


def validate_providers(providers: Sequence[str]) -> None:
    """Require one to six unique provider IDs, in display order."""
    if isinstance(providers, (str, bytes)) or not 1 <= len(providers) <= 6:
        raise ValueError("Select between 1 and 6 CodexBar provider IDs.")
    for provider in providers:
        if (
            not isinstance(provider, str)
            or re.fullmatch(r"[a-z][a-z0-9-]*", provider) is None
            or provider in ("all", "both")
        ):
            raise ValueError("Use individual lowercase CodexBar provider IDs.")
    if len(set(providers)) != len(providers):
        raise ValueError("CodexBar provider IDs must be unique.")


def _date(value: Any) -> Optional[datetime]:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _number(value: Any) -> Optional[float]:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    try:
        number = float(value)
    except (OverflowError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _window_label(slot: str, minutes: Any) -> str:
    duration = _number(minutes)
    if duration is None or duration <= 0:
        return _SLOT_LABELS[slot]
    if duration % 1440 == 0:
        return "{:g}d".format(duration / 1440)
    if duration % 60 == 0:
        return "{:g}h".format(duration / 60)
    return "{:g}m".format(duration)


def _provider_error(value: Any) -> str:
    if isinstance(value, dict):
        message = value.get("message")
        if isinstance(message, str) and message.strip():
            return message.strip()
    if isinstance(value, str) and value.strip():
        return value.strip()
    return "CodexBar could not fetch this provider."


def _cursor_requests(raw: dict, usage: dict) -> Optional[Tuple[int, int]]:
    """Read legacy Cursor request counts, without guessing from percentages."""
    description = raw.get("resetDescription")
    candidates = []
    if isinstance(description, str):
        match = re.fullmatch(r"\s*([\d,]+)\s*/\s*([\d,]+)\s+requests\s*", description)
        if match:
            candidates.append(match.groups())
    details = usage.get("details")
    for section in details if isinstance(details, list) else []:
        rows = section.get("rows") if isinstance(section, dict) else None
        for row in rows if isinstance(rows, list) else []:
            if not isinstance(row, dict) or row.get("label") != "Request quota":
                continue
            value = row.get("value")
            if isinstance(value, str):
                match = re.fullmatch(r"\s*([\d,]+)\s*/\s*([\d,]+)\s*", value)
                if match:
                    candidates.append(match.groups())
    for used, limit in candidates:
        try:
            counts = int(used.replace(",", "")), int(limit.replace(",", ""))
        except ValueError:
            continue
        if counts[1] > 0:
            return counts
    return None


def _parse(
    provider: str,
    output: str,
    returncode: int,
    *,
    observed_at: Optional[datetime] = None,
) -> ProviderQuota:
    try:
        payload = json.loads(output)
    except (ValueError, TypeError):
        return ProviderQuota(provider, error="CodexBar returned invalid JSON.")
    if not isinstance(payload, list):
        return ProviderQuota(provider, error="Expected a CodexBar JSON array.")
    rows = [
        row
        for row in payload
        if isinstance(row, dict) and row.get("provider") == provider
    ]
    if len(rows) != 1:
        return ProviderQuota(
            provider, error="Expected one current-account result for this provider."
        )
    row = rows[0]
    error = _provider_error(row["error"]) if row.get("error") is not None else None
    if returncode and not error:
        error = "CodexBar exited with status {}.".format(returncode)
    usage = row.get("usage")
    if not isinstance(usage, dict):
        return ProviderQuota(provider, error=error or "No quota data returned.")
    windows = []
    captured_at = observed_at if observed_at is not None else datetime.now(timezone.utc)
    paces = row.get("pace") if isinstance(row.get("pace"), dict) else {}
    for slot in _SLOTS:
        raw = usage.get(slot)
        if not isinstance(raw, dict):
            continue
        used = _number(raw.get("usedPercent"))
        remaining = None if used is None else max(0.0, min(100.0, 100.0 - used))
        requests = (
            _cursor_requests(raw, usage)
            if provider == "cursor" and slot == "primary"
            else None
        )
        if requests is not None:
            remaining = max(0.0, min(100.0, 100.0 * (1 - requests[0] / requests[1])))
        duration = _number(raw.get("windowMinutes"))
        windows.append(
            QuotaWindow(
                slot=slot,
                label=(
                    "Req"
                    if requests is not None
                    else _window_label(slot, raw.get("windowMinutes"))
                ),
                remaining_percent=remaining,
                resets_at=_date(raw.get("resetsAt")),
                request_usage=requests,
                window_minutes=(
                    duration if duration is not None and duration > 0 else None
                ),
                pace=parse_pace(paces.get(slot), remaining, captured_at),
            )
        )
    if not windows and not error:
        error = "No quota windows returned."
    return ProviderQuota(
        provider=provider,
        windows=tuple(windows),
        updated_at=_date(usage.get("updatedAt")),
        source=row.get("source") if isinstance(row.get("source"), str) else None,
        error=error,
    )


def fetch_quotas(
    providers: Sequence[str], *, timeout: float = 120
) -> List[ProviderQuota]:
    """Fetch each current account once; provider failures remain individual rows.

    CodexBar 0.56.3 emits an array, including error rows, before returning a
    nonzero exit status. Always inspect its stdout, even after a failed fetch.
    """
    validate_providers(providers)
    if _number(timeout) is None or timeout <= 0:
        raise ValueError(
            "CodexBar timeout must be a positive, finite number of seconds."
        )
    quotas = []
    for provider in providers:
        try:
            result = subprocess.run(
                ["codexbar", "usage", "--provider", provider, "--json", "--json-only"],
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )
        except FileNotFoundError as exc:
            raise FileNotFoundError(
                "CodexBar CLI was not found. Install codexbar and add it to PATH."
            ) from exc
        except subprocess.TimeoutExpired:
            quotas.append(
                ProviderQuota(
                    provider,
                    error=f"CodexBar timed out after {timeout:g}s. Increase --timeout if needed.",
                )
            )
            continue
        except OSError as exc:
            raise RuntimeError(
                "Could not start the CodexBar CLI: {}".format(exc)
            ) from exc
        quotas.append(_parse(provider, result.stdout, result.returncode))
    return quotas


@lru_cache(maxsize=12)
def _font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    # Matplotlib already ships with Quote0; avoid a system-font dependency or
    # importing Matplotlib's font manager during ordinary CLI commands.
    from matplotlib import get_data_path

    filename = "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
    path = Path(get_data_path()) / "fonts" / "ttf" / filename
    return ImageFont.truetype(str(path), size)


def _fit(text: str, font: ImageFont.FreeTypeFont, width: int) -> str:
    if font.getlength(text) <= width:
        return text
    while text and font.getlength(text + "…") > width:
        text = text[:-1]
    return text + "…" if text else ""


def _text(
    draw: ImageDraw.ImageDraw,
    xy: Tuple[int, int],
    text: str,
    font: ImageFont.FreeTypeFont,
    width: int,
) -> None:
    draw.text(xy, _fit(text, font, width), font=font, fill=0, anchor="lt")


def _percent(window: Optional[QuotaWindow]) -> str:
    if window is None or window.remaining_percent is None:
        return "--"
    return "{:.0f}%".format(window.remaining_percent)


def _reset(window: Optional[QuotaWindow], now: datetime) -> str:
    if window is None or window.resets_at is None:
        return "--"
    minutes = max(0, math.ceil((window.resets_at - now).total_seconds() / 60))
    if minutes == 0:
        return "now"
    days, remainder = divmod(minutes, 1440)
    hours, minutes = divmod(remainder, 60)
    if days:
        return "{}d{}h".format(days, hours) if hours else "{}d".format(days)
    if hours:
        return "{}h{}m".format(hours, minutes) if minutes else "{}h".format(hours)
    return "{}m".format(minutes)


def _name(provider: str) -> str:
    return _PROVIDER_NAMES.get(provider, provider.replace("-", " ").title())


def _footer(quotas: Sequence[ProviderQuota], current: datetime) -> str:
    source_times = [
        quota.updated_at
        for quota in quotas
        if quota.updated_at is not None and not quota.error
    ]
    if source_times:
        stamp = min(source_times).astimezone(current.tzinfo)
        footer = "Updated " + stamp.strftime("%m-%d %H:%M")
    elif all(quota.error for quota in quotas):
        footer = "Checked " + current.strftime("%m-%d %H:%M")
    else:
        footer = "Updated --"
    return footer


def render_quota(
    quotas: Sequence[ProviderQuota],
    *,
    now: Optional[datetime] = None,
    pace: bool = False,
    quota_focus: str = "primary",
) -> Image.Image:
    """Render one to six ordered provider rows as a monochrome device image.

    One provider gets up to three windows and bars. Two or three providers get
    primary/secondary windows plus reset countdowns. Four to six get compact
    primary/secondary rows. The footer reports the oldest valid source time.
    """
    validate_providers([quota.provider for quota in quotas])
    current = now if now is not None else datetime.now().astimezone()
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    validate_focus(quota_focus)
    if pace or quota_focus != "primary":
        return _render_insights(quotas, current, pace=pace, quota_focus=quota_focus)
    image = Image.new("1", (296, 152), 1)
    draw = ImageDraw.Draw(image)
    _text(draw, (6, 4), "QUOTA LEFT", _font(13, True), 284)
    draw.line((6, 21, 289, 21), fill=0)

    if len(quotas) == 1:
        quota = quotas[0]
        _text(draw, (6, 27), _name(quota.provider), _font(16, True), 284)
        if quota.error or not quota.windows:
            _text(draw, (6, 62), "ERR  Unavailable", _font(16), 284)
            _text(draw, (6, 87), "Check CodexBar", _font(12), 284)
        else:
            for index, window in enumerate(quota.windows[:3]):
                y = 51 + index * 27
                _text(draw, (6, y), window.label, _font(12), 56)
                _text(draw, (67, y - 2), _percent(window), _font(16, True), 67)
                detail = (
                    "{}/{} used".format(*window.request_usage)
                    if window.request_usage is not None
                    else "reset " + _reset(window, current)
                )
                _text(draw, (145, y), detail, _font(12), 144)
                draw.rectangle((6, y + 18, 289, y + 22), outline=0)
                if (
                    window.remaining_percent is not None
                    and window.remaining_percent > 0
                ):
                    right = 7 + round(281 * window.remaining_percent / 100)
                    draw.rectangle((7, y + 19, min(right, 288), y + 21), fill=0)
                if window.request_usage is not None and len(quota.windows) == 1:
                    _text(
                        draw,
                        (6, y + 36),
                        "reset " + _reset(window, current),
                        _font(12),
                        284,
                    )
    else:
        row_height = 108 // len(quotas)
        for index, quota in enumerate(quotas):
            y = 26 + index * row_height
            _text(draw, (6, y), _name(quota.provider), _font(12, True), 100)
            windows = {window.slot: window for window in quota.windows}
            primary = windows.get("primary")
            requests = primary.request_usage if primary else None
            if quota.error or not quota.windows:
                _text(draw, (113, y), "ERR  Unavailable", _font(12), 176)
            elif requests is not None:
                used, limit = requests
                _text(draw, (113, y), f"{max(0, limit - used)}/{limit}", _font(12), 88)
                _text(draw, (207, y), "left " + _percent(primary), _font(12), 82)
            else:
                for slot, x, width in (("primary", 113, 88), ("secondary", 207, 82)):
                    window = windows.get(slot)
                    label = window.label if window else _SLOT_LABELS[slot]
                    _text(
                        draw, (x, y), label + " " + _percent(window), _font(12), width
                    )
            if len(quotas) <= 3:
                if quota.error or not quota.windows:
                    resets = "Check CodexBar"
                elif requests is not None:
                    resets = "Req {}/{} used · reset {}".format(
                        *requests, _reset(primary, current)
                    )
                else:
                    resets = "reset P {}  /  S {}".format(
                        _reset(windows.get("primary"), current),
                        _reset(windows.get("secondary"), current),
                    )
                _text(draw, (6, y + 17), resets, _font(12), 283)
            if index < len(quotas) - 1:
                draw.line((6, y + row_height - 3, 289, y + row_height - 3), fill=0)

    footer = _footer(quotas, current)
    draw.line((6, 135, 289, 135), fill=0)
    _text(draw, (6, 139), footer, _font(10), 284)
    return image


def _display_metrics(primary, secondary):
    counts = primary.request_usage if primary is not None else None
    if counts is not None:
        used, limit = counts
        return f"{max(0, limit - used)}/{limit}", "left " + _percent(primary)
    return (
        (primary.label if primary else "P") + " " + _percent(primary),
        (secondary.label if secondary else "S") + " " + _percent(secondary),
    )


def _display_resets(primary, secondary, current):
    if primary is not None and primary.request_usage is not None:
        return "Req {}/{} used · reset {}".format(
            *primary.request_usage, _reset(primary, current)
        )
    return "reset {} {} / {} {}".format(
        primary.label if primary else "P",
        _reset(primary, current),
        secondary.label if secondary else "S",
        _reset(secondary, current),
    )


def _image_pace_marker(draw, y, expected_remaining):
    position = max(7, min(287, 7 + round(280 * expected_remaining / 100)))
    # A dark tick with light shoulders is visible over both filled and empty bar regions.
    draw.line((position, y + 18, position, y + 22), fill=1, width=3)
    draw.line((position, y + 18, position, y + 22), fill=0, width=1)


def _render_insights(quotas, current, *, pace, quota_focus):
    image = Image.new("1", (296, 152), 1)
    draw = ImageDraw.Draw(image)
    _text(draw, (6, 4), "QUOTA LEFT", _font(13, True), 284)
    draw.line((6, 21, 289, 21), fill=0)
    if len(quotas) == 1:
        quota = quotas[0]
        failed = bool(quota.error or not quota.windows)
        hint = pace_hint(quota, current)
        _text(
            draw,
            (6, 27),
            _name(quota.provider),
            _font(16, True),
            95 if pace and not failed else 284,
        )
        if failed:
            _text(draw, (6, 62), "ERR  Unavailable", _font(16), 284)
            _text(draw, (6, 87), "Check CodexBar", _font(12), 284)
        else:
            if pace:
                _text(draw, (105, 27), hint.summary, _font(11, True), 184)
                _text(draw, (105, 40), hint.forecast, _font(11), 184)
            windows = display_windows(quota.windows, quota_focus)
            for index, window in enumerate(windows[:3]):
                y = (57 + index * 25) if pace else (51 + index * 27)
                _text(draw, (6, y), window.label, _font(12), 56)
                _text(draw, (67, y - 2), _percent(window), _font(16, True), 67)
                detail = (
                    "{}/{} used".format(*window.request_usage)
                    if window.request_usage is not None
                    else "reset " + _reset(window, current)
                )
                _text(draw, (145, y), detail, _font(12), 144)
                draw.rectangle((6, y + 18, 289, y + 22), outline=0)
                if (
                    window.remaining_percent is not None
                    and window.remaining_percent > 0
                ):
                    right = 7 + round(281 * window.remaining_percent / 100)
                    draw.rectangle((7, y + 19, min(right, 288), y + 21), fill=0)
                if (
                    pace
                    and window.slot == hint.slot
                    and hint.expected_remaining_percent is not None
                ):
                    _image_pace_marker(draw, y, hint.expected_remaining_percent)
                if window.request_usage is not None and len(windows) == 1:
                    _text(
                        draw,
                        (6, y + 36),
                        "reset " + _reset(window, current),
                        _font(12),
                        284,
                    )
    else:
        height = 108 // len(quotas)
        for index, quota in enumerate(quotas):
            y = 26 + index * height
            failed = bool(quota.error or not quota.windows)
            primary, secondary = display_pair(quota.windows, quota_focus)
            first, second = _display_metrics(primary, secondary)
            hint = pace_hint(quota, current)
            dense = pace and len(quotas) >= 4
            _text(
                draw,
                (6, y),
                _name(quota.provider),
                _font(12, True),
                80 if dense else 100,
            )
            if failed:
                _text(
                    draw,
                    (90 if dense else 113, y),
                    "ERR  Unavailable",
                    _font(12),
                    199 if dense else 176,
                )
            elif dense:
                _text(draw, (90, y), first, _font(11), 67)
                _text(draw, (161, y), second, _font(11), 60)
                _text(draw, (225, y), hint.compact, _font(10), 65)
            else:
                _text(draw, (113, y), first, _font(12), 88)
                _text(draw, (207, y), second, _font(12), 82)
            if len(quotas) <= 3:
                line = (
                    "Check CodexBar"
                    if failed
                    else _display_resets(primary, secondary, current)
                )
                if pace and not failed and len(quotas) == 3:
                    line = hint.summary + " | " + hint.forecast
                _text(draw, (6, y + 17), line, _font(11 if pace else 12), 284)
                if pace and not failed and len(quotas) == 2:
                    _text(
                        draw,
                        (6, y + 33),
                        hint.summary + " | " + hint.forecast,
                        _font(11),
                        284,
                    )
            elif pace and len(quotas) == 4 and not failed:
                _text(draw, (6, y + 14), hint.forecast, _font(10), 284)
            if index < len(quotas) - 1:
                draw.line((6, y + height - 1, 289, y + height - 1), fill=0)
    draw.line((6, 135, 289, 135), fill=0)
    _text(draw, (6, 139), _footer(quotas, current), _font(10), 284)
    return image

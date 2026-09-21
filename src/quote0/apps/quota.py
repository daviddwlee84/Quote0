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


@dataclass(frozen=True)
class QuotaWindow:
    slot: str
    label: str
    remaining_percent: Optional[float] = None
    resets_at: Optional[datetime] = None


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


def _parse(provider: str, output: str, returncode: int) -> ProviderQuota:
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
    for slot in _SLOTS:
        raw = usage.get(slot)
        if not isinstance(raw, dict):
            continue
        used = _number(raw.get("usedPercent"))
        remaining = None if used is None else max(0.0, min(100.0, 100.0 - used))
        windows.append(
            QuotaWindow(
                slot=slot,
                label=_window_label(slot, raw.get("windowMinutes")),
                remaining_percent=remaining,
                resets_at=_date(raw.get("resetsAt")),
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


def fetch_quotas(providers: Sequence[str]) -> List[ProviderQuota]:
    """Fetch each current account once; provider failures remain individual rows.

    CodexBar 0.56.3 emits an array, including error rows, before returning a
    nonzero exit status. Always inspect its stdout, even after a failed fetch.
    """
    validate_providers(providers)
    quotas = []
    for provider in providers:
        try:
            result = subprocess.run(
                ["codexbar", "usage", "--provider", provider, "--json", "--json-only"],
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )
        except FileNotFoundError as exc:
            raise FileNotFoundError(
                "CodexBar CLI was not found. Install codexbar and add it to PATH."
            ) from exc
        except subprocess.TimeoutExpired:
            quotas.append(
                ProviderQuota(provider, error="CodexBar timed out after 30s.")
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


def render_quota(
    quotas: Sequence[ProviderQuota], *, now: Optional[datetime] = None
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
    image = Image.new("1", (296, 152), 1)
    draw = ImageDraw.Draw(image)
    _text(draw, (6, 4), "QUOTA LEFT", _font(13, True), 284)
    draw.line((6, 21, 289, 21), fill=0)

    if len(quotas) == 1:
        quota = quotas[0]
        _text(draw, (6, 27), _name(quota.provider), _font(16, True), 284)
        if quota.error:
            _text(draw, (6, 62), "ERR  Unavailable", _font(16), 284)
            _text(draw, (6, 87), "Check CodexBar", _font(12), 284)
        else:
            for index, window in enumerate(quota.windows[:3]):
                y = 51 + index * 27
                _text(draw, (6, y), window.label, _font(12), 56)
                _text(draw, (67, y - 2), _percent(window), _font(16, True), 67)
                _text(
                    draw, (145, y), "reset " + _reset(window, current), _font(12), 144
                )
                draw.rectangle((6, y + 18, 289, y + 22), outline=0)
                if (
                    window.remaining_percent is not None
                    and window.remaining_percent > 0
                ):
                    right = 7 + round(281 * window.remaining_percent / 100)
                    draw.rectangle((7, y + 19, min(right, 288), y + 21), fill=0)
    else:
        row_height = 108 // len(quotas)
        for index, quota in enumerate(quotas):
            y = 26 + index * row_height
            _text(draw, (6, y), _name(quota.provider), _font(12, True), 100)
            windows = {window.slot: window for window in quota.windows}
            if quota.error:
                _text(draw, (113, y), "ERR  Unavailable", _font(12), 176)
            else:
                for slot, x, width in (("primary", 113, 88), ("secondary", 207, 82)):
                    window = windows.get(slot)
                    label = window.label if window else _SLOT_LABELS[slot]
                    _text(
                        draw, (x, y), label + " " + _percent(window), _font(12), width
                    )
            if len(quotas) <= 3:
                resets = (
                    "Check CodexBar"
                    if quota.error
                    else "reset P {}  /  S {}".format(
                        _reset(windows.get("primary"), current),
                        _reset(windows.get("secondary"), current),
                    )
                )
                _text(draw, (6, y + 17), resets, _font(12), 283)
            if index < len(quotas) - 1:
                draw.line((6, y + row_height - 3, 289, y + row_height - 3), fill=0)

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
    draw.line((6, 135, 289, 135), fill=0)
    _text(draw, (6, 139), footer, _font(10), 284)
    return image

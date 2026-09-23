"""Native Canvas quota rendering using the same snapshot and formatting as PNG."""

from datetime import datetime, timezone
from typing import Optional, Sequence

from .quota import ProviderQuota, _footer, _name, _percent, _reset, validate_providers
from ..models import CanvasApiRequest


def quota_display_data(quotas: Sequence[ProviderQuota], now: datetime) -> dict:
    """Only public display values, with JSON-safe types and no provider credentials."""
    providers = []
    for quota in quotas:
        windows = []
        for window in quota.windows[:3]:
            remaining = window.remaining_percent
            windows.append(
                {
                    "label": window.label,
                    "percent": _percent(window),
                    "reset": "reset " + _reset(window, now),
                    "detail": (
                        "{}/{} used".format(*window.request_usage)
                        if window.request_usage is not None
                        else "reset " + _reset(window, now)
                    ),
                    "barWidth": (
                        0
                        if remaining is None
                        else round(280 * max(0, min(100, remaining)) / 100)
                    ),
                }
            )
        by_slot = {window.slot: window for window in quota.windows}
        primary, secondary = by_slot.get("primary"), by_slot.get("secondary")
        counts = primary.request_usage if primary is not None else None
        if counts is not None:
            used, limit = counts
            first = f"{max(0, limit - used)}/{limit}"
            second = "left " + _percent(primary)
            resets = "Req {}/{} used · reset {}".format(
                used, limit, _reset(primary, now)
            )
        else:
            first = (primary.label if primary else "P") + " " + _percent(primary)
            second = (secondary.label if secondary else "S") + " " + _percent(secondary)
            resets = "reset P {}  /  S {}".format(
                _reset(primary, now), _reset(secondary, now)
            )
        failed = bool(quota.error or not quota.windows)
        providers.append(
            {
                "name": _name(quota.provider),
                "failed": failed,
                "windows": windows,
                "first": first,
                "second": second,
                "resets": "Check CodexBar" if failed else resets,
            }
        )
    return {
        "title": "QUOTA LEFT",
        "providers": providers,
        "footer": _footer(quotas, now),
    }


def _bind(path: str) -> str:
    return '{{get inputData "' + path + '" default="--"}}'


def _element(children=None, *, style=None, tw="flex flex-col", kind="div"):
    props = {"tw": tw}
    if style is not None:
        props["style"] = {"boxSizing": "border-box", **style}
    if children is not None:
        props["children"] = children
    return {"type": kind, "props": props}


def _text(path=None, *, literal=None, width=None, size=14, bold=False):
    style = {
        "fontSize": size,
        "lineHeight": f"{size + 3}px",
        "whiteSpace": "nowrap",
        "overflow": "hidden",
        "textOverflow": "ellipsis",
        "flexShrink": 0,
    }
    if width is not None:
        style["width"] = width
    if bold:
        style["fontWeight"] = 700
    return _element(
        _bind(path) if path else literal,
        kind="span",
        tw=f"text-{size}-chillduansans",
        style=style,
    )


def render_quota_canvas(
    quotas: Sequence[ProviderQuota], *, now: Optional[datetime] = None
) -> dict:
    """Return a reusable Canvas request, not a visual preview or a PNG wrapper."""
    validate_providers([quota.provider for quota in quotas])
    current = now if now is not None else datetime.now().astimezone()
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    data = quota_display_data(quotas, current)
    rows = []
    if len(quotas) == 1:
        provider = data["providers"][0]
        rows.append(
            _element(
                [_text("providers.0.name", width=284, size=16, bold=True)],
                style={"height": 25, "flexShrink": 0},
            )
        )
        if provider["failed"]:
            rows.append(_text(literal="ERR  Unavailable", size=16))
            rows.append(_text(literal="Check CodexBar"))
        else:
            for index, window in enumerate(provider["windows"]):
                path = f"providers.0.windows.{index}"
                labels = _element(
                    [
                        _text(path + ".label", width=56),
                        _text(path + ".percent", width=67, size=16, bold=True),
                        _text(path + ".detail", width=139),
                    ],
                    tw="flex flex-row items-center",
                    style={"gap": 11, "height": 20},
                )
                bar = _element(
                    [
                        _element(
                            style={
                                "height": 2,
                                "width": _bind(path + ".barWidth") + "px",
                                "backgroundColor": "black",
                            }
                        )
                    ],
                    style={
                        "height": 4,
                        "width": 284,
                        "border": "1px solid black",
                        "padding": 0,
                    },
                )
                rows.append(
                    _element([labels, bar], style={"height": 27, "flexShrink": 0})
                )
            if (
                len(provider["windows"]) == 1
                and quotas[0].windows[0].request_usage is not None
            ):
                rows.append(_text("providers.0.windows.0.reset"))
    else:
        height = 108 // len(quotas)
        for index, provider in enumerate(data["providers"]):
            path = f"providers.{index}"
            main = [_text(path + ".name", width=100, bold=True)]
            if provider["failed"]:
                main.append(_text(literal="ERR  Unavailable", width=176))
            else:
                main.extend(
                    [
                        _text(path + ".first", width=88),
                        _text(path + ".second", width=82),
                    ]
                )
            children = [
                _element(main, tw="flex flex-row", style={"gap": 7, "height": 18})
            ]
            if len(quotas) <= 3:
                children.append(_text(path + ".resets", width=284))
            style = {"height": height, "flexShrink": 0, "overflow": "hidden"}
            if index < len(quotas) - 1:
                style["borderBottom"] = "1px solid black"
            rows.append(_element(children, style=style))
    header = _element(
        [_text("title", size=14, bold=True)],
        style={
            "height": 22,
            "paddingTop": 3,
            "borderBottom": "1px solid black",
            "flexShrink": 0,
        },
    )
    body = _element(
        rows,
        style={"height": 113, "paddingTop": 4, "overflow": "hidden", "flexShrink": 0},
    )
    footer = _element(
        [_text("footer", size=11)],
        style={
            "height": 17,
            "paddingTop": 2,
            "borderTop": "1px solid black",
            "flexShrink": 0,
        },
    )
    payload = {
        "data": data,
        "windowData": {
            "default": [
                _element(
                    [header, body, footer],
                    tw="flex flex-col bg-white text-black",
                    style={
                        "width": 296,
                        "height": 152,
                        "paddingLeft": 6,
                        "paddingRight": 6,
                        "boxSizing": "border-box",
                    },
                )
            ]
        },
        "layoutFull": {"style": {"padding": 0}},
        "border": 0,
    }
    # One place enforces the same structural limits for exported and sent payloads.
    CanvasApiRequest.model_validate(payload)
    return payload

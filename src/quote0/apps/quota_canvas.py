"""Native Canvas quota rendering using the same snapshot and formatting as PNG."""

from datetime import datetime, timezone
from typing import Literal, Optional, Sequence

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
                    "slot": window.slot,
                    "hasRequestUsage": window.request_usage is not None,
                    "label": window.label,
                    "percent": _percent(window),
                    "reset": "reset " + _reset(window, now),
                    "resetIn": _reset(window, now),
                    "fillPercent": (
                        0 if remaining is None else max(0, min(100, remaining))
                    ),
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


def _render_compact(
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


def _card_text(
    path=None,
    *,
    literal=None,
    width=None,
    size=12,
    bold=False,
    color="black",
    line_height=None,
):
    text = _text(path, literal=literal, width=width, size=size, bold=bold)
    text["props"]["style"]["color"] = color
    if line_height is not None:
        text["props"]["style"]["lineHeight"] = f"{line_height}px"
    return text


def _card(children, *, width, height, dark=False, padding=5, gap=2):
    return _element(
        children,
        style={
            "width": width,
            "height": height,
            "padding": padding,
            "gap": gap,
            "border": "1px solid " + ("white" if dark else "black"),
            "borderRadius": 7,
            "backgroundColor": "black" if dark else "white",
            "overflow": "hidden",
            "flexShrink": 0,
        },
    )


def _card_bar(path, width, *, dark=False):
    ink = "white" if dark else "black"
    return _element(
        [
            _element(
                style={
                    "width": _bind(path + ".fillPercent") + "%",
                    "height": "100%",
                    "backgroundColor": ink,
                }
            )
        ],
        style={
            "width": width,
            "height": 6,
            "border": "1px solid " + ink,
            "borderRadius": 3,
            "overflow": "hidden",
            "flexShrink": 0,
        },
    )


def _card_data(data):
    """Bind named slots rather than accidentally treating secondary as primary."""

    def missing(slot):
        return {
            "label": slot,
            "percent": "--",
            "resetIn": "--",
            "reset": "reset --",
            "detail": "reset --",
            "fillPercent": 0,
        }

    for provider in data["providers"]:
        by_slot = {w["slot"]: w for w in provider["windows"]}
        provider["primary"] = by_slot.get("primary", missing("P"))
        provider["secondary"] = by_slot.get("secondary", missing("S"))
        provider["tertiary"] = by_slot.get("tertiary", missing("T"))
        primary, secondary = provider["primary"], provider["secondary"]
        provider["cardPrimaryReset"] = primary["label"] + " " + primary["reset"]
        if primary.get("hasRequestUsage", False):
            provider["cardSecondary"] = primary["detail"]
            provider["cardSecondaryReset"] = "requests"
        else:
            provider["cardSecondary"] = secondary["label"] + " " + secondary["percent"]
            provider["cardSecondaryReset"] = secondary["reset"]
    count = len(data["providers"])
    data["serviceCount"] = f"{count} SERVICE" + ("S" if count > 1 else "")
    return data


def _provider_card(data, index, width, *, dark=False):
    provider = data["providers"][index]
    path = f"providers.{index}"
    ink = "white" if dark else "black"
    inner = width - 12  # border + padding, each side
    if provider["failed"]:
        return _card(
            [
                _card_text(path + ".name", width=inner, size=14, bold=True, color=ink),
                _card_text(literal="ERR", size=26, bold=True, color=ink),
                _card_text(literal="Unavailable", width=inner, size=11, color=ink),
                _card_text(literal="Check CodexBar", width=inner, size=10, color=ink),
            ],
            width=width,
            height=107,
            dark=dark,
        )
    # Two/three columns keep the main value large; supporting lines have fixed slots.
    narrow = width < 110
    main_size = 26 if narrow else 34
    # Give 100% the whole numeric slot; window labels live on the reset line.
    primary = _card_text(
        path + ".primary.percent",
        width=inner,
        size=main_size,
        bold=True,
        color=ink,
        line_height=33,
    )
    return _card(
        [
            _card_text(
                path + ".name",
                width=inner,
                size=14,
                bold=True,
                color=ink,
                line_height=17,
            ),
            primary,
            _card_bar(path + ".primary", inner, dark=dark),
            _card_text(
                path + ".cardPrimaryReset",
                width=inner,
                size=11,
                color=ink,
                line_height=13,
            ),
            _card_text(
                path + ".cardSecondary",
                width=inner,
                size=12,
                bold=True,
                color=ink,
                line_height=14,
            ),
            _card_text(
                path + ".cardSecondaryReset",
                width=inner,
                size=10,
                color=ink,
                line_height=12,
            ),
        ],
        width=width,
        height=107,
        dark=dark,
        gap=0,
    )


def _card_dark(theme, *, alternating_dark=False):
    return theme == "dark" or (theme == "alternating" and alternating_dark)


def _single_cards(data, theme):
    provider = data["providers"][0]
    hero_dark = _card_dark(theme)
    hero_ink = "white" if hero_dark else "black"
    side_dark = _card_dark(theme, alternating_dark=True)
    side_ink = "white" if side_dark else "black"
    if provider["failed"]:
        return _provider_card(data, 0, 288, dark=hero_dark)
    windows = provider["windows"]
    # Additional slots appear as secondary metric cards, not ornamental counters.
    secondary = [w for w in windows if w["slot"] != "primary"][:2]
    hero_width = 180 if secondary else 288
    inner = hero_width - 14
    detail = provider["primary"]["reset"]
    if provider["primary"].get("hasRequestUsage", False):
        detail = provider["primary"]["detail"] + " · " + detail
    provider["heroDetail"] = detail
    hero = _card(
        [
            _element(
                [
                    _card_text(
                        "providers.0.name",
                        width=inner - 28,
                        size=16,
                        bold=True,
                        color=hero_ink,
                    ),
                    _card_text(
                        "providers.0.primary.label", width=28, size=11, color=hero_ink
                    ),
                ],
                tw="flex flex-row items-center",
                style={"height": 20, "flexShrink": 0},
            ),
            _card_text(
                "providers.0.primary.percent",
                size=38,
                bold=True,
                line_height=43,
                color=hero_ink,
            ),
            _card_bar("providers.0.primary", inner, dark=hero_dark),
            _card_text(
                "providers.0.heroDetail",
                width=inner,
                size=12,
                line_height=15,
                color=hero_ink,
            ),
        ],
        width=hero_width,
        height=107,
        padding=6,
        gap=2,
        dark=hero_dark,
    )
    if not secondary:
        return hero
    tiles = []
    tile_height = (107 - 5 * (len(secondary) - 1)) / len(secondary)
    for window in secondary:
        path = f"providers.0.{window['slot']}"
        if len(secondary) == 1:
            children = [
                _card_text(path + ".label", size=13, bold=True, color=side_ink),
                _card_text(path + ".percent", size=28, bold=True, color=side_ink),
                _card_bar(path, 90, dark=side_dark),
                _card_text(path + ".reset", width=90, size=11, color=side_ink),
            ]
        else:
            children = [
                _element(
                    [
                        _card_text(path + ".label", width=28, size=11, color=side_ink),
                        _card_text(
                            path + ".percent",
                            width=62,
                            size=21,
                            bold=True,
                            color=side_ink,
                        ),
                    ],
                    tw="flex flex-row items-center",
                    style={"height": 25, "flexShrink": 0},
                ),
                _card_text(
                    path + ".reset", width=90, size=10, color=side_ink, line_height=13
                ),
            ]
        tiles.append(
            _card(children, width=102, height=tile_height, dark=side_dark, gap=1)
        )
    side = _element(tiles, style={"width": 102, "height": 107, "gap": 5})
    return _element([hero, side], tw="flex flex-row", style={"gap": 6, "height": 107})


def _dense_cards(data, theme):
    count = len(data["providers"])
    row_count = (count + 1) // 2
    height = (107 - (row_count - 1) * 4) / row_count
    dense = count > 4
    rows = []
    for start in range(0, count, 2):
        cards = []
        for index in range(start, min(start + 2, count)):
            provider = data["providers"][index]
            path = f"providers.{index}"
            dark = _card_dark(theme, alternating_dark=index % 2 == 1)
            ink = "white" if dark else "black"
            inner = 135 if dense else 129
            metrics = (
                [
                    _card_text(
                        literal="ERR  Unavailable",
                        width=inner,
                        size=12,
                        color=ink,
                        line_height=13,
                    )
                ]
                if provider["failed"]
                else [
                    _card_text(
                        path + ".first",
                        width=inner / 2,
                        size=12 if dense else 14,
                        color=ink,
                        line_height=13 if dense else 18,
                    ),
                    _card_text(
                        path + ".second",
                        width=inner / 2,
                        size=12 if dense else 14,
                        color=ink,
                        line_height=13 if dense else 18,
                    ),
                ]
            )
            cards.append(
                _card(
                    [
                        _card_text(
                            path + ".name",
                            width=inner,
                            size=12 if dense else 14,
                            bold=True,
                            color=ink,
                            line_height=14 if dense else 18,
                        ),
                        _element(
                            metrics,
                            tw="flex flex-row",
                            style={"height": 13 if dense else 18},
                        ),
                    ],
                    width=141,
                    height=height,
                    dark=dark,
                    padding=2 if dense else 5,
                    gap=0 if dense else 2,
                )
            )
        rows.append(
            _element(
                cards,
                tw="flex flex-row",
                style={"gap": 6, "height": height, "flexShrink": 0},
            )
        )
    return _element(rows, style={"gap": 4, "height": 107})


def _cards_payload(data, theme):
    data = _card_data(data)
    count = len(data["providers"])
    frame_dark = theme != "light"
    frame_ink = "white" if frame_dark else "black"
    if count == 1:
        body = _single_cards(data, theme)
    elif count <= 3:
        width = (288 - (count - 1) * 6) / count
        body = _element(
            [
                _provider_card(
                    data, i, width, dark=_card_dark(theme, alternating_dark=i == 1)
                )
                for i in range(count)
            ],
            tw="flex flex-row",
            style={"height": 107, "gap": 6},
        )
    else:
        body = _dense_cards(data, theme)
    header = _element(
        [
            _card_text(
                "title", width=180, size=12, bold=True, color=frame_ink, line_height=15
            ),
            _card_text(
                "serviceCount", width=108, size=10, color=frame_ink, line_height=15
            ),
        ],
        tw="flex flex-row justify-between",
        style={"height": 15, "flexShrink": 0},
    )
    footer = _element(
        [
            _card_text("footer", width=288, size=10, color=frame_ink, line_height=14),
        ],
        style={"height": 14, "flexShrink": 0},
    )
    return {
        "data": data,
        "windowData": {
            "default": [
                _element(
                    [header, body, footer],
                    tw=f"flex flex-col text-{frame_ink}",
                    style={
                        "width": 296,
                        "height": 152,
                        "padding": 4,
                        "gap": 4,
                        "backgroundColor": "black" if frame_dark else "white",
                    },
                )
            ]
        },
        "layoutFull": {"style": {"padding": 0}},
        "border": 1 if theme == "dark" else 0,
    }


def render_quota_canvas(
    quotas: Sequence[ProviderQuota],
    *,
    now: Optional[datetime] = None,
    style: Literal["compact", "cards"] = "compact",
    card_theme: Literal["light", "dark", "alternating"] = "alternating",
) -> dict:
    """Render ordered quotas as compact rows or monochrome cards; never an image wrapper."""
    if card_theme not in ("light", "dark", "alternating"):
        raise ValueError("Card theme must be light, dark or alternating")
    if style == "compact":
        if card_theme != "alternating":
            raise ValueError("Card themes require the cards Canvas style")
        return _render_compact(quotas, now=now)
    if style != "cards":
        raise ValueError("Canvas style must be compact or cards")
    validate_providers([quota.provider for quota in quotas])
    current = now if now is not None else datetime.now().astimezone()
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    payload = _cards_payload(quota_display_data(quotas, current), card_theme)
    CanvasApiRequest.model_validate(payload)
    return payload

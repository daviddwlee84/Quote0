"""Offline Canvas structure checks, not a template compiler or visual preview."""

import json
from urllib.parse import urlsplit

UNSAFE = {"__proto__", "constructor", "prototype"}
RESERVED_DATA = UNSAFE | {
    "type",
    "key",
    "windowData",
    "layoutFull",
    "taskAlias",
    "link",
    "border",
}


def validate_canvas(payload: dict) -> None:
    def fail(path, message):
        raise ValueError(f"{path}: {message}")

    def walk(value, path, depth=0):
        if depth > 64:
            fail(path, "JSON nesting is too deep")
        if isinstance(value, dict):
            for key, item in value.items():
                if key in UNSAFE:
                    fail(f"{path}.{key}", "reserved key")
                walk(item, f"{path}.{key}", depth + 1)
        elif isinstance(value, list):
            for index, item in enumerate(value):
                walk(item, f"{path}[{index}]", depth + 1)
        elif (
            isinstance(value, str)
            and path.startswith("windowData")
            and len(value) > 4000
        ):
            fail(path, "string exceeds 4000 characters")

    for name, limit in (("data", 65536), ("windowData", 131072), ("layoutFull", 8192)):
        if name not in payload:
            continue
        value = payload[name]
        if not isinstance(value, dict):
            fail(name, "must be an object")
        try:
            size = len(
                json.dumps(value, ensure_ascii=False, allow_nan=False).encode("utf-8")
            )
        except (TypeError, ValueError, RecursionError):
            fail(name, "must contain finite JSON values")
        if size > limit:
            fail(name, f"exceeds {limit} bytes")
        walk(value, name)
    for key in payload.get("data", {}):
        if key in RESERVED_DATA:
            fail(f"data.{key}", "reserved key")
    window = payload.get("windowData")
    if not isinstance(window, dict) or not isinstance(window.get("default"), list):
        fail("windowData.default", "must be an array")

    count = 0

    def node(value, path, depth=1, text_allowed=False):
        nonlocal count
        if depth > 16:
            fail(path, "element nesting exceeds 16")
        if isinstance(value, str) and text_allowed:
            return
        if isinstance(value, list):
            for index, child in enumerate(value):
                node(child, f"{path}[{index}]", depth, text_allowed)
            return
        if not isinstance(value, dict):
            fail(
                path,
                "expected an element object" + (" or text" if text_allowed else ""),
            )
        if "$ifAny" in value:
            if set(value) - {"$ifAny", "$then", "$else"} or "$then" not in value:
                fail(path, "condition needs $ifAny/$then and optional $else")
            paths = value["$ifAny"]
            if isinstance(paths, str):
                paths = [paths]
            if (
                not isinstance(paths, list)
                or not paths
                or any(not isinstance(p, str) or not p for p in paths)
            ):
                fail(path + ".$ifAny", "expected a path or non-empty list of paths")
            for branch in ("$then", "$else"):
                if branch in value and value[branch] is not None:
                    node(value[branch], path + "." + branch, depth + 1, text_allowed)
            return
        if set(value) - {"type", "props"} or value.get("type") not in {
            "div",
            "span",
            "img",
        }:
            fail(path + ".type", "only div, span and img elements are supported")
        count += 1
        if count > 80:
            fail(path, "element count exceeds 80")
        props = value.get("props")
        if not isinstance(props, dict):
            fail(path + ".props", "must be an object")
        for key in props:
            if key.startswith("on") or key in {
                "dangerouslySetInnerHTML",
                "ref",
                "srcSet",
            }:
                fail(path + ".props." + key, "unsupported property")
        if "tw" in props and not isinstance(props["tw"], str):
            fail(path + ".props.tw", "must be a string")
        if "style" in props and not isinstance(props["style"], dict):
            fail(path + ".props.style", "must be an object")
        if "$for" in props:
            loop = props["$for"]
            if not isinstance(loop, dict) or set(loop) - {
                "items",
                "as",
                "index",
                "limit",
            }:
                fail(path + ".props.$for", "invalid loop structure")
            for key in ("items", "as"):
                if not isinstance(loop.get(key), str) or not loop[key]:
                    fail(path + ".props.$for." + key, "must be a non-empty string")
            if "index" in loop and (
                not isinstance(loop["index"], str) or not loop["index"]
            ):
                fail(path + ".props.$for.index", "must be a non-empty string")
            if "limit" in loop and (
                type(loop["limit"]) is not int or loop["limit"] < 1
            ):
                fail(path + ".props.$for.limit", "must be a positive integer")
        if "$empty" in props:
            if "$for" not in props:
                fail(path + ".props.$empty", "requires $for")
            node(props["$empty"], path + ".props.$empty", depth + 1)
        if value["type"] == "img":
            src = props.get("src")
            if not isinstance(src, str) or not src:
                fail(path + ".props.src", "image source is required")
            if "{{" not in src and not src.startswith("data:image/"):
                parts = urlsplit(src)
                if parts.scheme not in ("http", "https") or not parts.netloc:
                    fail(
                        path + ".props.src",
                        "use an image data URI or public http(s) URL",
                    )
        if "children" in props:
            node(props["children"], path + ".props.children", depth + 1, True)

    for layer, elements in window.items():
        if not isinstance(elements, list):
            fail(f"windowData.{layer}", "layer must be an array")
        node(elements, f"windowData.{layer}")
    layout = payload.get("layoutFull", {})
    if "tw" in layout and not isinstance(layout["tw"], str):
        fail("layoutFull.tw", "must be a string")
    if "style" in layout and not isinstance(layout["style"], dict):
        fail("layoutFull.style", "must be an object")

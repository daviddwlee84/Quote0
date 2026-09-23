#!/usr/bin/env python3
"""Quote/0 device management, content delivery, and applications."""

import base64
import io
import json as jsonlib
import re
import sys
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Annotated, List, Literal, Optional, Sequence, Union
from urllib.parse import urlsplit

import tyro

from .client import DotClient, Quote0, UNSET
from .config import (
    environment_key,
    load_environment,
    make_config,
    resolve_account,
    resolve_device,
    validate_name,
    write_config,
)
from .models import (
    ApiResponse,
    BorderColor,
    CanvasApiRequest,
    DeviceSettingsRequest,
    TextStyles,
)
from .utils import get_preset_images


class PresetImageName(Enum):
    ALL_BLACK = "all_black"
    CHECKERBOARD_GRAY = "checkerboard_gray"
    ONE_PIXEL_BLACK = "1x1_black"


@dataclass
class TargetOptions:
    device: Optional[str] = None
    """Local device name; otherwise use explicit credentials or defaults.device"""
    config: Path = Path("quote0.toml")
    """Account/device configuration file"""
    api_key: Optional[str] = None
    """Explicit API key; prefer environment variables to avoid shell history"""
    device_id: Optional[str] = None
    """Explicit device ID"""


@dataclass
class DeviceOptions(TargetOptions):
    no_refresh: bool = False
    """Save content without requesting immediate display"""
    task_key: Optional[str] = None
    """Select a particular API content item from devices tasks"""
    task_alias: Optional[str] = None
    """Name the task; omit to keep its name or pass an empty string to clear it"""


@dataclass
class Text(DeviceOptions):
    """Send text content"""

    title: Optional[str] = None
    message: Optional[str] = None
    signature: Optional[str] = None
    link: Optional[str] = None
    icon_file: Optional[Path] = None
    """PNG icon file (40px × 40px recommended)"""
    icon_url: Optional[str] = None
    """Public http(s) image URL; mutually exclusive with icon-file"""
    styles_file: Optional[Path] = None
    """JSON typography overrides for title, message and signature"""


@dataclass
class Image(DeviceOptions):
    """Send an image"""

    file: Optional[Path] = None
    preset: Optional[PresetImageName] = None
    base64: Optional[str] = None
    url: Optional[str] = None
    """Public http(s) image URL; use exactly one image source"""
    border: BorderColor = BorderColor.WHITE
    link: Optional[str] = None
    dither_type: Optional[str] = None
    dither_kernel: Optional[str] = None


@dataclass
class Canvas(DeviceOptions):
    """Validate or send a Canvas request JSON file"""

    file: Path = tyro.MISSING
    validate_only: bool = False
    """Check structure offline, without resolving a device or sending"""


@dataclass
class Quota(DeviceOptions):
    """Display current-account quotas from CodexBar"""

    providers: List[str] = tyro.MISSING
    """One to six distinct provider IDs, in display order"""
    output: Optional[Path] = None
    """Only save a PNG (image) or JSON (canvas); no device credentials required"""
    renderer: Literal["image", "canvas"] = "image"
    timeout: float = 120
    """Maximum seconds to wait for each CodexBar provider"""


@dataclass
class Apps:
    """Applications built on the generic client"""

    command: Union[
        Annotated[Quota, tyro.conf.subcommand(name="quota")],
        Annotated[None, tyro.conf.Suppress],
    ]


@dataclass
class AccountOptions:
    account: Optional[str] = None
    config: Path = Path("quote0.toml")
    api_key: Optional[str] = None
    json: bool = False
    """Print machine-readable response data only"""


@dataclass
class DevicesList(AccountOptions):
    """List devices visible to an account"""


@dataclass
class Status(TargetOptions):
    """Read battery, connectivity and render status"""

    json: bool = False


@dataclass
class Tasks(TargetOptions):
    """List task keys and names for content selection"""

    task_type: Literal["loop", "fixed"] = "loop"
    json: bool = False


@dataclass
class Next(TargetOptions):
    """Switch to the next content item"""


@dataclass
class SettingsGet(TargetOptions):
    """Read current device settings"""

    json: bool = False


@dataclass
class SettingsUpdate(TargetOptions):
    """Update only fields present in a settings JSON file"""

    file: Path = tyro.MISSING


@dataclass
class Settings:
    command: Union[
        Annotated[SettingsGet, tyro.conf.subcommand(name="get")],
        Annotated[SettingsUpdate, tyro.conf.subcommand(name="update")],
        Annotated[None, tyro.conf.Suppress],
    ]


@dataclass
class Devices:
    """Discover devices and manage their state/content"""

    command: Union[
        Annotated[DevicesList, tyro.conf.subcommand(name="list")],
        Annotated[Status, tyro.conf.subcommand(name="status")],
        Annotated[Tasks, tyro.conf.subcommand(name="tasks")],
        Annotated[Next, tyro.conf.subcommand(name="next")],
        Annotated[Settings, tyro.conf.subcommand(name="settings")],
        Annotated[None, tyro.conf.Suppress],
    ]


@dataclass
class TimezonesList(AccountOptions):
    """List timezone keys accepted by device settings"""


@dataclass
class Timezones:
    command: Union[
        Annotated[TimezonesList, tyro.conf.subcommand(name="list")],
        Annotated[None, tyro.conf.Suppress],
    ]


@dataclass
class ConfigInit:
    """Discover and bind devices, interactively or with --bind NAME=ID ..."""

    account: str = "personal"
    api_key_env: str = "DOT_API_KEY"
    config: Path = Path("quote0.toml")
    bind: Optional[List[str]] = None
    default_device: Optional[str] = None
    force: bool = False
    """Replace an existing configuration after complete validation"""


@dataclass
class Config:
    command: Union[
        Annotated[ConfigInit, tyro.conf.subcommand(name="init")],
        Annotated[None, tyro.conf.Suppress],
    ]


def _client(config: TargetOptions) -> Quote0:
    credentials = resolve_device(
        device=config.device,
        config=config.config,
        api_key=config.api_key,
        device_id=config.device_id,
    )
    return Quote0(credentials.api_key, credentials.device_id)


def _account_client(config: AccountOptions) -> DotClient:
    return DotClient(
        resolve_account(
            account=config.account, config=config.config, api_key=config.api_key
        )
    )


def _report_response(response: ApiResponse) -> None:
    if response.success:
        print(f"✅ {response.message}")
    else:
        print(f"❌ {response.message}", file=sys.stderr)
        if response.error:
            print(f"Error details: {response.error}", file=sys.stderr)
        if response.status_code == 404:
            print(
                "Check the device ID and that the matching API content is in its Dot App Loop.",
                file=sys.stderr,
            )
        sys.exit(1)


def _data(response: ApiResponse):
    if not response.success:
        _report_response(response)
    return response.model_dump(mode="json")["response"]


def _json(value):
    return jsonlib.dumps(value, ensure_ascii=False, indent=2, allow_nan=False)


def _read_json(path: Path) -> dict:
    def invalid_constant(value):
        raise ValueError("JSON must contain finite values")

    try:
        value = jsonlib.loads(
            path.read_text(encoding="utf-8"), parse_constant=invalid_constant
        )
    except (jsonlib.JSONDecodeError, UnicodeError):
        raise ValueError(f"Invalid JSON file: {path}") from None
    if not isinstance(value, dict):
        raise ValueError(f"Expected a JSON object in {path}")
    return value


def _public_url(url: str) -> str:
    parts = urlsplit(url)
    if (
        parts.scheme not in ("http", "https")
        or not parts.hostname
        or parts.username
        or parts.password
        or len(url) > 2048
    ):
        raise ValueError(
            "Use a public http(s) image URL without credentials (max 2048 characters)."
        )
    return url


def _task_options(config: DeviceOptions) -> dict:
    values = {}
    if config.task_key is not None:
        values["task_key"] = config.task_key
    if config.task_alias is not None:
        values["task_alias"] = config.task_alias
    return values


def text_command(config: Text) -> None:
    if not any([config.title, config.message, config.signature]):
        raise ValueError(
            "At least one of --title, --message, or --signature is required"
        )
    if config.icon_file is not None and config.icon_url is not None:
        raise ValueError("Use only one of --icon-file and --icon-url")
    icon = _public_url(config.icon_url) if config.icon_url is not None else None
    if config.icon_file is not None:
        content = config.icon_file.read_bytes()
        if len(content) > 1024 * 1024:
            raise ValueError("Icon exceeds 1 MB")
        icon = base64.b64encode(content).decode("ascii")
    styles = (
        TextStyles.model_validate(_read_json(config.styles_file))
        if config.styles_file
        else None
    )
    response = _client(config).send_text(
        refresh_now=not config.no_refresh,
        title=config.title,
        message=config.message,
        signature=config.signature,
        icon=icon,
        link=config.link,
        styles=styles,
        **_task_options(config),
    )
    _report_response(response)


def image_command(config: Image) -> None:
    if (
        sum(
            item is not None
            for item in (config.file, config.preset, config.base64, config.url)
        )
        != 1
    ):
        raise ValueError("Use exactly one of --file, --preset, --base64, or --url")
    if config.preset is not None:
        content = get_preset_images()[config.preset.value].base64
    elif config.file is not None:
        raw = config.file.read_bytes()
        if len(raw) > 3 * 1024 * 1024:
            raise ValueError("Image exceeds 3 MB")
        content = base64.b64encode(raw).decode("ascii")
    elif config.url is not None:
        content = _public_url(config.url)
    else:
        content = config.base64
    _report_response(
        _client(config).send_image(
            image_base64=content,
            border=config.border,
            refresh_now=not config.no_refresh,
            link=config.link,
            dither_type=config.dither_type,
            dither_kernel=config.dither_kernel,
            **_task_options(config),
        )
    )


def _send_canvas(client: Quote0, request: CanvasApiRequest) -> ApiResponse:
    return client.send_canvas(
        request.windowData,
        data=request.data,
        layout_full=request.layoutFull,
        link=request.link,
        border=request.border,
        refresh_now=request.refreshNow,
        task_key=request.taskKey,
        task_alias=(
            request.taskAlias if "taskAlias" in request.model_fields_set else UNSET
        ),
    )


def canvas_command(config: Canvas) -> None:
    payload = _read_json(config.file)
    if config.no_refresh:
        payload["refreshNow"] = False
    if config.task_key is not None:
        payload["taskKey"] = config.task_key
    if config.task_alias is not None:
        payload["taskAlias"] = config.task_alias
    request = CanvasApiRequest.model_validate(payload)
    if config.validate_only:
        print("Canvas structure is valid; rendering has not been verified.")
    else:
        _report_response(_send_canvas(_client(config), request))


def quota_command(config: Quota) -> None:
    from .apps.quota import fetch_quotas, render_quota, validate_providers

    validate_providers(config.providers)
    if (
        config.renderer == "canvas"
        and config.output is not None
        and config.output.suffix.lower() != ".json"
    ):
        raise ValueError(
            "Canvas output must use a .json file; use renderer image for PNG previews."
        )
    # Exports do not resolve credentials, devices or tasks.
    client = None if config.output is not None else _client(config)
    quotas = fetch_quotas(config.providers, timeout=config.timeout)
    if config.renderer == "canvas":
        from .apps.quota_canvas import render_quota_canvas

        payload = render_quota_canvas(quotas)
        if config.output is not None:
            config.output.write_text(_json(payload) + "\n", encoding="utf-8")
        else:
            _report_response(
                client.send_canvas(
                    payload["windowData"],
                    data=payload["data"],
                    layout_full=payload.get("layoutFull"),
                    border=BorderColor.WHITE,
                    refresh_now=not config.no_refresh,
                    **_task_options(config),
                )
            )
    else:
        picture = render_quota(quotas)
        if config.output is not None:
            picture.save(config.output, format="PNG")
        else:
            buffer = io.BytesIO()
            picture.save(buffer, format="PNG")
            _report_response(
                client.send_image(
                    image_base64=base64.b64encode(buffer.getvalue()).decode("ascii"),
                    border=BorderColor.WHITE,
                    refresh_now=not config.no_refresh,
                    dither_type="NONE",
                    **_task_options(config),
                )
            )
    if config.output is not None:
        print(f"Saved quota {config.renderer} output: {config.output}")
    failures = [quota for quota in quotas if quota.error]
    for quota in failures:
        print(f"⚠️  {quota.provider}: {quota.error}", file=sys.stderr)
    if failures:
        sys.exit(1)


def _table(rows, columns):
    def cell(value):
        # Remote aliases are data, not terminal control sequences.
        return "".join(
            c if c.isprintable() else " "
            for c in str(value if value is not None else "--")
        )

    values = [[cell(row.get(key)) for key in columns] for row in rows]
    widths = [
        max(len(key), *(len(row[i]) for row in values)) if values else len(key)
        for i, key in enumerate(columns)
    ]
    print("  ".join(key.ljust(widths[i]) for i, key in enumerate(columns)))
    for row in values:
        print("  ".join(value.ljust(widths[i]) for i, value in enumerate(row)))
    if not values:
        print("(none)")


def query_command(config) -> None:
    columns = None
    if isinstance(config, DevicesList):
        response = _account_client(config).list_devices()
        columns = ["id", "alias", "location", "model", "edition"]
    elif isinstance(config, TimezonesList):
        response = _account_client(config).list_timezones()
        columns = ["key", "name", "utcOffsetLabel"]
    elif isinstance(config, Tasks):
        response = _client(config).list_tasks(config.task_type)
        columns = ["key", "type", "taskAlias"]
    elif isinstance(config, Status):
        response = _client(config).get_status()
    else:
        response = _client(config).get_settings()
    data = _data(response)
    if config.json or columns is None:
        print(_json(data))
    else:
        _table(data, columns)


def config_init_command(config: ConfigInit) -> None:
    validate_name(config.account)
    if config.config.exists() and not config.force:
        raise ValueError(
            f"Configuration already exists: {config.config}; use --force to replace it."
        )
    if config.bind is None and not sys.stdin.isatty():
        raise ValueError(
            "Non-interactive initialization requires --bind NAME=DEVICE_ID ..."
        )
    load_environment()
    rows = _data(DotClient(environment_key(config.api_key_env)).list_devices())
    if not rows:
        raise ValueError("No devices were returned for this account.")
    bindings, default_device = config.bind, config.default_device
    if bindings is None:
        _table(
            [{"number": index + 1, **row} for index, row in enumerate(rows)],
            ["number", "id", "alias", "location", "model"],
        )
        selected = input("Device numbers (space-separated; blank cancels): ").split()
        if not selected:
            raise ValueError("Initialization cancelled; no file written.")
        if any(
            not index.isdigit() or not 1 <= int(index) <= len(rows)
            for index in selected
        ):
            raise ValueError("Select device numbers from the displayed list.")
        bindings = []
        for index in selected:
            row = rows[int(index) - 1]
            suggestion = (
                re.sub(r"[^A-Za-z0-9_-]+", "-", row.get("alias") or "").strip("-_")
                or f"device-{index}"
            )
            name = input(f"Local name [{suggestion}]: ").strip() or suggestion
            bindings.append(f"{name}={row['id']}")
        if default_device is None and len(bindings) > 1:
            default_device = input("Default device local name: ").strip()
    if default_device is None:
        if len(bindings) != 1:
            raise ValueError("Multiple bindings require --default-device.")
        default_device = bindings[0].partition("=")[0]
    settings = make_config(config.account, config.api_key_env, bindings, default_device)
    available = {row["id"] for row in rows}
    if any(
        device["device_id"] not in available for device in settings["devices"].values()
    ):
        raise ValueError(
            "A bound device was not returned by this account's device list."
        )
    write_config(config.config, settings, force=config.force)
    print(f"Saved device configuration: {config.config}")


def main(args: Optional[Sequence[str]] = None) -> None:
    config = tyro.cli(
        Union[Text, Image, Canvas, Apps, Devices, Timezones, Config],
        args=args,
        config=(tyro.conf.OmitSubcommandPrefixes, tyro.conf.OmitArgPrefixes),
    )
    while isinstance(config, (Apps, Devices, Settings, Timezones, Config)):
        config = config.command
    try:
        if isinstance(config, Text):
            text_command(config)
        elif isinstance(config, Image):
            image_command(config)
        elif isinstance(config, Canvas):
            canvas_command(config)
        elif isinstance(config, Quota):
            quota_command(config)
        elif isinstance(config, ConfigInit):
            config_init_command(config)
        elif isinstance(config, Next):
            _report_response(_client(config).next_content())
        elif isinstance(config, SettingsUpdate):
            request = DeviceSettingsRequest.model_validate(_read_json(config.file))
            _report_response(_client(config).update_settings(request))
        elif isinstance(
            config, (DevicesList, TimezonesList, Status, Tasks, SettingsGet)
        ):
            query_command(config)
    except (EOFError, KeyboardInterrupt):
        print("Cancelled.", file=sys.stderr)
        sys.exit(1)
    except (ValueError, OSError, RuntimeError) as exc:
        print(f"❌ Error: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

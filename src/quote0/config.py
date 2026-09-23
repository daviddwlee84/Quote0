"""Account credentials, fixed device bindings, and configuration initialization."""

import json
import os
import re
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

try:
    import tomllib
except ModuleNotFoundError:  # Python 3.9 and 3.10
    import tomli as tomllib


@dataclass(frozen=True)
class DeviceCredentials:
    api_key: str = field(repr=False)
    device_id: str


def _string(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def validate_name(name: str) -> None:
    if not isinstance(name, str) or not re.fullmatch(
        r"[A-Za-z0-9][A-Za-z0-9_-]*", name
    ):
        raise ValueError(
            "Local names must use letters, numbers, hyphens or underscores."
        )


def load_environment() -> None:
    try:
        load_dotenv(dotenv_path=Path.cwd() / ".env", override=False)
    except OSError:
        raise ValueError("Cannot read the current directory's .env file.") from None


def environment_key(name: str) -> str:
    if not isinstance(name, str) or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name):
        raise ValueError("Account needs a valid api_key_env variable name.")
    value = os.getenv(name)
    if not _string(value):
        raise ValueError(f"Environment variable {name!r} is missing or empty.")
    return value


def validate_config(settings: dict) -> dict:
    if set(settings) - {"accounts", "devices", "defaults"}:
        raise ValueError(
            "Unknown configuration section; use accounts, devices and defaults."
        )
    for section in ("accounts", "devices", "defaults"):
        if not isinstance(settings.get(section, {}), dict):
            raise ValueError(f"{section} must be a TOML table.")
    accounts, devices = settings.get("accounts", {}), settings.get("devices", {})
    for name, profile in accounts.items():
        validate_name(name)
        if not isinstance(profile, dict) or set(profile) != {"api_key_env"}:
            raise ValueError(f"Account {name!r} needs only an api_key_env field.")
        env = profile["api_key_env"]
        if not isinstance(env, str) or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", env):
            raise ValueError(
                f"Account {name!r} needs a valid api_key_env variable name."
            )
    for name, profile in devices.items():
        validate_name(name)
        if not isinstance(profile, dict):
            raise ValueError(f"Device {name!r} must be a TOML table.")
        if "api_key_env" in profile:
            raise ValueError(
                "Old device config is unsupported; move api_key_env to accounts or run config init."
            )
        if set(profile) != {"device_id", "account"} or not _string(
            profile.get("device_id")
        ):
            raise ValueError(
                f"Device {name!r} needs a non-empty device_id and account."
            )
        if (
            not isinstance(profile["account"], str)
            or profile["account"] not in accounts
        ):
            raise ValueError(f"Device {name!r} references an unknown account.")
    defaults = settings.get("defaults", {})
    if set(defaults) - {"account", "device"}:
        raise ValueError("defaults supports only account and device.")
    for field_name, choices in (("account", accounts), ("device", devices)):
        if field_name in defaults and (
            not isinstance(defaults[field_name], str)
            or defaults[field_name] not in choices
        ):
            raise ValueError(f"Unknown default {field_name}.")
    return settings


def load_config(config: Path, *, required: bool = False) -> dict:
    try:
        with Path(config).open("rb") as stream:
            settings = tomllib.load(stream)
    except FileNotFoundError:
        if not required:
            return {}
        raise ValueError(f"Cannot read device configuration: {config}") from None
    except OSError:
        raise ValueError(f"Cannot read device configuration: {config}") from None
    except (tomllib.TOMLDecodeError, UnicodeError):
        raise ValueError(f"Invalid TOML device configuration: {config}") from None
    return validate_config(settings)


def resolve_account(
    *,
    account: Optional[str] = None,
    config: Path = Path("quote0.toml"),
    api_key: Optional[str] = None,
) -> str:
    load_environment()
    if api_key is not None:
        if not _string(api_key):
            raise ValueError("API key must be non-empty.")
        return api_key
    settings = load_config(config, required=account is not None)
    name = (
        account if account is not None else settings.get("defaults", {}).get("account")
    )
    if name is None:
        return environment_key("DOT_API_KEY")
    if name not in settings.get("accounts", {}):
        raise ValueError(f"Unknown account {name!r}.")
    return environment_key(settings["accounts"][name]["api_key_env"])


def resolve_device(
    *,
    device: Optional[str] = None,
    config: Path = Path("quote0.toml"),
    api_key: Optional[str] = None,
    device_id: Optional[str] = None,
) -> DeviceCredentials:
    """Explicit name, explicit direct flags, default device, then direct environment.

    Named devices allow explicit field overrides but never inherit unrelated DOT_*.
    Direct flags bypass TOML entirely, so partial flags cannot borrow a default ID/key.
    """
    load_environment()
    settings = {}
    if device is not None or (api_key is None and device_id is None):
        settings = load_config(config, required=device is not None)
        if device is None:
            device = settings.get("defaults", {}).get("device")
    if device is not None:
        if device not in settings.get("devices", {}):
            raise ValueError(f"Unknown device {device!r} in {config}.")
        profile = settings["devices"][device]
        key = (
            api_key
            if api_key is not None
            else environment_key(
                settings["accounts"][profile["account"]]["api_key_env"]
            )
        )
        identifier = device_id if device_id is not None else profile["device_id"]
    else:
        key = api_key if api_key is not None else os.getenv("DOT_API_KEY")
        identifier = device_id if device_id is not None else os.getenv("DOT_DEVICE_ID")
    if not _string(key):
        raise ValueError("API key is required; set DOT_API_KEY or use --api-key.")
    if not _string(identifier):
        raise ValueError("Device ID is required; set DOT_DEVICE_ID or use --device-id.")
    return DeviceCredentials(key, identifier)


def make_config(
    account: str, api_key_env: str, bindings: list, default_device: str
) -> dict:
    devices = {}
    for binding in bindings:
        name, separator, identifier = binding.partition("=")
        validate_name(name)
        if not separator or not _string(identifier) or name in devices:
            raise ValueError("Bindings must be unique NAME=DEVICE_ID entries.")
        if any(item["device_id"] == identifier for item in devices.values()):
            raise ValueError(
                "A device ID may only be bound once during initialization."
            )
        devices[name] = {"account": account, "device_id": identifier}
    if not devices:
        raise ValueError("Select at least one device.")
    return validate_config(
        {
            "defaults": {"account": account, "device": default_device},
            "accounts": {account: {"api_key_env": api_key_env}},
            "devices": devices,
        }
    )


def write_config(config: Path, settings: dict, *, force: bool = False) -> None:
    """Publish a complete TOML file atomically; never overwrite without force."""
    validate_config(settings)
    lines = ["# Credentials are read from the environment or cwd/.env.", "[defaults]"]

    def quote(value):
        return json.dumps(value, ensure_ascii=False)

    for key, value in settings.get("defaults", {}).items():
        lines.append(f"{key} = {quote(value)}")
    for section in ("accounts", "devices"):
        for name, profile in settings.get(section, {}).items():
            lines.extend(["", f"[{section}.{quote(name)}]"])
            lines.extend(f"{key} = {quote(value)}" for key, value in profile.items())
    destination = Path(config)
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=destination.parent,
        prefix=".quote0-",
        delete=False,
    ) as stream:
        temporary = Path(stream.name)
        try:
            stream.write("\n".join(lines) + "\n")
            stream.flush()
            os.fsync(stream.fileno())
        except BaseException:
            temporary.unlink(missing_ok=True)
            raise
    try:
        if force:
            os.replace(temporary, destination)
        else:
            os.link(temporary, destination)
    except FileExistsError:
        raise ValueError(
            f"Configuration already exists: {destination}; use --force to replace it."
        ) from None
    finally:
        temporary.unlink(missing_ok=True)

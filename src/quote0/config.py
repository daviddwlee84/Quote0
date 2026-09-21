"""Resolve credentials for a named device or the legacy environment settings."""

import os
import re
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


def _nonempty_string(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def resolve_device(
    *,
    device: Optional[str] = None,
    config: Path = Path("quote0.toml"),
    api_key: Optional[str] = None,
    device_id: Optional[str] = None,
) -> DeviceCredentials:
    """Load cwd/.env, then resolve explicit flags over the selected credentials.

    Named devices use only their own ``device_id`` and ``api_key_env`` fields.
    Without a name, the legacy DOT_API_KEY and DOT_DEVICE_ID variables apply,
    and the TOML configuration is not read.
    """
    try:
        load_dotenv(dotenv_path=Path.cwd() / ".env", override=False)
    except OSError:
        raise ValueError("Cannot read the current directory's .env file.") from None

    if device is None:
        resolved_key = api_key if api_key is not None else os.getenv("DOT_API_KEY")
        resolved_id = device_id if device_id is not None else os.getenv("DOT_DEVICE_ID")
        if not _nonempty_string(resolved_key):
            raise ValueError("API key is required; set DOT_API_KEY or use --api-key.")
        if not _nonempty_string(resolved_id):
            raise ValueError(
                "Device ID is required; set DOT_DEVICE_ID or use --device-id."
            )
        return DeviceCredentials(api_key=resolved_key, device_id=resolved_id)

    config = Path(config)
    try:
        with config.open("rb") as stream:
            settings = tomllib.load(stream)
    except OSError:
        raise ValueError(f"Cannot read device configuration: {config}") from None
    except (tomllib.TOMLDecodeError, UnicodeError):
        raise ValueError(f"Invalid TOML device configuration: {config}") from None

    devices = settings.get("devices")
    if not isinstance(devices, dict) or device not in devices:
        raise ValueError(f"Unknown device {device!r} in {config}.")
    profile = devices[device]
    if not isinstance(profile, dict):
        raise ValueError(f"Device {device!r} must be a TOML table.")

    resolved_id = device_id if device_id is not None else profile.get("device_id")
    if not _nonempty_string(resolved_id):
        raise ValueError(
            f"Device {device!r} needs a non-empty device_id; use --device-id "
            "or update its configuration."
        )

    resolved_key = api_key
    if api_key is None:
        key_env = profile.get("api_key_env")
        if not isinstance(key_env, str) or not re.fullmatch(
            r"[A-Za-z_][A-Za-z0-9_]*", key_env
        ):
            raise ValueError(
                f"Device {device!r} needs a valid api_key_env variable name; "
                "use --api-key or update its configuration."
            )
        resolved_key = os.getenv(key_env)
        if not _nonempty_string(resolved_key):
            raise ValueError(
                f"Environment variable {key_env!r} is missing or empty; "
                "set it or use --api-key."
            )
    if not _nonempty_string(resolved_key):
        raise ValueError("API key must be non-empty; use --api-key.")

    return DeviceCredentials(api_key=resolved_key, device_id=resolved_id)

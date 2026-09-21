#!/usr/bin/env python3
"""
Quote/0 CLI Tool - Send text and images to your Quote/0 device

TODO: make use of our models.py?!
"""

import base64
import io
import sys
from typing import Annotated, List, Optional, Sequence, Union
from pathlib import Path
import tyro
from dataclasses import dataclass
from enum import Enum

from .client import Quote0
from .config import resolve_device
from .models import ApiResponse, BorderColor
from .utils import get_preset_images


class PresetImageName(Enum):
    """Available preset images"""

    ALL_BLACK = "all_black"
    CHECKERBOARD_GRAY = "checkerboard_gray"
    ONE_PIXEL_BLACK = "1x1_black"


@dataclass
class DeviceOptions:
    """Shared delivery options."""

    device: Optional[str] = None
    """Named device from the TOML configuration"""

    config: Path = Path("quote0.toml")
    """Device configuration file (read only when --device is supplied)"""

    api_key: Optional[str] = None
    """Override the device API key (otherwise use its configured environment variable or DOT_API_KEY)"""

    device_id: Optional[str] = None
    """Override the device ID (otherwise use the named device or DOT_DEVICE_ID)"""

    no_refresh: bool = False
    """Don't refresh the display immediately after sending"""


@dataclass
class Text(DeviceOptions):
    """Send text to Quote/0 device"""

    title: Optional[str] = None
    """Text title to display"""

    message: Optional[str] = None
    """Text content to display"""

    signature: Optional[str] = None
    """Text signature to display"""

    link: Optional[str] = None
    """HTTP/HTTPS link or Scheme URL for NFC touch"""

    icon_file: Optional[Path] = None
    """Path to PNG icon file (40px*40px)"""


@dataclass
class Image(DeviceOptions):
    """Send image to Quote/0 device"""

    # Image-specific options

    # --- Image source options ---
    file: Optional[Path] = None
    """Path to image file"""

    preset: Optional[PresetImageName] = None
    """Use a preset test image"""

    base64: Optional[str] = None
    """PNG Base64 encoded image string (alternative to --file and --preset)"""
    # ----------------------------

    border: BorderColor = BorderColor.WHITE
    """Border color (WHITE=0, BLACK=1)"""

    link: Optional[str] = None
    """HTTP/HTTPS link or Scheme URL for NFC touch"""

    dither_type: Optional[str] = None
    """Dithering type (DIFFUSION, ORDERED, NONE)"""

    dither_kernel: Optional[str] = None
    """Dithering algorithm (only used when dither_type is DIFFUSION)"""


@dataclass
class Quota(DeviceOptions):
    """Display current-account quotas from the CodexBar CLI"""

    providers: List[str] = tyro.MISSING
    """One to six distinct CodexBar provider IDs, in display order"""

    output: Optional[Path] = None
    """Save a PNG preview instead of sending; device credentials are not required"""


@dataclass
class Apps:
    """Applications built on the generic Quote/0 client"""

    command: Union[
        Annotated[Quota, tyro.conf.subcommand(name="quota")],
        Annotated[None, tyro.conf.Suppress],
    ]


def _client(config: DeviceOptions) -> Quote0:
    credentials = resolve_device(
        device=config.device,
        config=config.config,
        api_key=config.api_key,
        device_id=config.device_id,
    )
    return Quote0(credentials.api_key, credentials.device_id)


def _report_response(response: ApiResponse) -> None:
    if response.success:
        print(f"✅ {response.message}")
    else:
        print(f"❌ {response.message}", file=sys.stderr)
        if response.error:
            print(f"Error details: {response.error}", file=sys.stderr)
        sys.exit(1)


def text_command(config: Text) -> None:
    """Execute text command"""
    client = _client(config)

    if not any([config.title, config.message, config.signature]):
        print(
            "❌ Error: At least one of --title, --message, or --signature is required"
        )
        sys.exit(1)

    # Handle icon file
    icon_base64 = None
    if config.icon_file:
        if not config.icon_file.exists():
            print(f"❌ Error: Icon file not found: {config.icon_file}")
            sys.exit(1)

        try:
            with open(config.icon_file, "rb") as f:
                icon_base64 = base64.b64encode(f.read()).decode("utf-8")
            print(f"📁 Loaded icon from: {config.icon_file}")
        except Exception as e:
            print(f"❌ Error loading icon file: {e}")
            sys.exit(1)

    print("📤 Sending text to Quote/0 device...")
    response = client.send_text(
        refresh_now=not config.no_refresh,
        title=config.title,
        message=config.message,
        signature=config.signature,
        icon=icon_base64,
        link=config.link,
    )

    _report_response(response)


def image_command(config: Image) -> None:
    """Execute image command"""
    client = _client(config)

    # Validate that exactly one of file, preset, or base64 is provided
    image_sources = [config.file, config.preset, config.base64]
    provided_sources = [source for source in image_sources if source is not None]

    if len(provided_sources) == 0:
        print("❌ Error: One of --file, --preset, or --base64 is required")
        sys.exit(1)

    if len(provided_sources) > 1:
        print("❌ Error: Can only use one of --file, --preset, or --base64")
        sys.exit(1)

    # Get image base64
    image_base64 = ""

    if config.preset:
        print(f"🖼️  Using preset image: {config.preset.value}")
        presets = get_preset_images()
        if config.preset.value not in presets:
            print(f"❌ Error: Unknown preset: {config.preset.value}")
            sys.exit(1)
        image_base64 = presets[config.preset.value].base64

    elif config.file:
        if not config.file.exists():
            print(f"❌ Error: Image file not found: {config.file}")
            sys.exit(1)

        try:
            # For CLI, we need to handle file objects differently
            print(f"📁 Loading image from: {config.file}")
            with open(config.file, "rb") as f:
                image_data = f.read()
                image_base64 = base64.b64encode(image_data).decode("utf-8")

            print(f"📏 Image loaded, size: {len(image_data)} bytes")

        except Exception as e:
            print(f"❌ Error loading image file: {e}")
            sys.exit(1)

    elif config.base64:
        print("📄 Using provided base64 image data")
        image_base64 = config.base64
        print(f"📏 Base64 data length: {len(image_base64)} characters")

    print(f"📤 Sending image to Quote/0 device... (border: {config.border.name})")
    response = client.send_image(
        image_base64=image_base64,
        border=config.border,
        refresh_now=not config.no_refresh,
        link=config.link,
        dither_type=config.dither_type,
        dither_kernel=config.dither_kernel,
    )

    _report_response(response)


def quota_command(config: Quota) -> None:
    """Fetch, render, and optionally deliver the quota application."""
    from .apps.quota import fetch_quotas, render_quota, validate_providers

    validate_providers(config.providers)
    # Resolve delivery settings before fetching. Previews need no device at all.
    client = None if config.output is not None else _client(config)
    quotas = fetch_quotas(config.providers)
    picture = render_quota(quotas)

    if config.output is not None:
        picture.save(config.output, format="PNG")
        print(f"🖼️  Saved quota preview: {config.output}")
    else:
        buffer = io.BytesIO()
        picture.save(buffer, format="PNG")
        assert client is not None
        _report_response(
            client.send_image(
                image_base64=base64.b64encode(buffer.getvalue()).decode("ascii"),
                border=BorderColor.WHITE,
                refresh_now=not config.no_refresh,
                dither_type="NONE",
            )
        )

    failures = [quota for quota in quotas if quota.error]
    for quota in failures:
        print(f"⚠️  {quota.provider}: {quota.error}", file=sys.stderr)
    if failures:
        sys.exit(1)


def main(args: Optional[Sequence[str]] = None) -> None:
    """Main CLI entry point"""
    config = tyro.cli(
        Union[Text, Image, Apps],
        args=args,
        config=(tyro.conf.OmitSubcommandPrefixes, tyro.conf.OmitArgPrefixes),
    )

    try:
        if isinstance(config, Text):
            text_command(config)
        elif isinstance(config, Image):
            image_command(config)
        elif isinstance(config, Apps) and isinstance(config.command, Quota):
            quota_command(config.command)
    except (ValueError, OSError, RuntimeError) as exc:
        print(f"❌ Error: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

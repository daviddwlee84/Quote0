#!/usr/bin/env python3
"""
Quote/0 CLI Tool - Send text and images to your Quote/0 device

TODO: make use of our models.py?!
"""

import os
import sys
from typing import Optional, Union
from pathlib import Path
import tyro
from dataclasses import dataclass
from enum import Enum

from .client import Quote0
from .models import BorderColor
from .utils import get_preset_images


class PresetImageName(Enum):
    """Available preset images"""

    ALL_BLACK = "all_black"
    CHECKERBOARD_GRAY = "checkerboard_gray"
    ONE_PIXEL_BLACK = "1x1_black"


@dataclass
class TextConfig:
    """Send text to Quote/0 device"""

    # Global options
    api_key: str = os.getenv("DOT_API_KEY", "")
    """DOT API key (defaults to DOT_API_KEY environment variable)"""

    device_id: str = os.getenv("DOT_DEVICE_ID", "")
    """DOT device ID (defaults to DOT_DEVICE_ID environment variable)"""

    no_refresh: bool = False
    """Don't refresh the display immediately after sending"""

    # Text-specific options
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
class ImageConfig:
    """Send image to Quote/0 device"""

    # Global options
    api_key: str = os.getenv("DOT_API_KEY", "")
    """DOT API key (defaults to DOT_API_KEY environment variable)"""

    device_id: str = os.getenv("DOT_DEVICE_ID", "")
    """DOT device ID (defaults to DOT_DEVICE_ID environment variable)"""

    no_refresh: bool = False
    """Don't refresh the display immediately after sending"""

    # Image-specific options
    file: Optional[Path] = None
    """Path to image file"""

    preset: Optional[PresetImageName] = None
    """Use a preset test image"""

    border: BorderColor = BorderColor.WHITE
    """Border color (WHITE=0, BLACK=1)"""

    link: Optional[str] = None
    """HTTP/HTTPS link or Scheme URL for NFC touch"""

    dither_type: Optional[str] = None
    """Dithering type (DIFFUSION, ORDERED, NONE)"""

    dither_kernel: Optional[str] = None
    """Dithering algorithm (only used when dither_type is DIFFUSION)"""


def text_command(config: TextConfig) -> None:
    """Execute text command"""
    if not config.api_key or not config.device_id:
        print("❌ Error: API key and device ID are required")
        print(
            "Set DOT_API_KEY and DOT_DEVICE_ID environment variables or use --api-key and --device-id flags"
        )
        sys.exit(1)

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
            import base64

            with open(config.icon_file, "rb") as f:
                icon_base64 = base64.b64encode(f.read()).decode("utf-8")
            print(f"📁 Loaded icon from: {config.icon_file}")
        except Exception as e:
            print(f"❌ Error loading icon file: {e}")
            sys.exit(1)

    # Create client and send text
    client = Quote0(config.api_key, config.device_id)

    print("📤 Sending text to Quote/0 device...")
    response = client.send_text(
        refresh_now=not config.no_refresh,
        title=config.title,
        message=config.message,
        signature=config.signature,
        icon=icon_base64,
        link=config.link,
    )

    if response.success:
        print(f"✅ {response.message}")
    else:
        print(f"❌ {response.message}")
        if response.error:
            print(f"Error details: {response.error}")
        sys.exit(1)


def image_command(config: ImageConfig) -> None:
    """Execute image command"""
    if not config.api_key or not config.device_id:
        print("❌ Error: API key and device ID are required")
        print(
            "Set DOT_API_KEY and DOT_DEVICE_ID environment variables or use --api-key and --device-id flags"
        )
        sys.exit(1)

    if not config.file and not config.preset:
        print("❌ Error: Either --file or --preset is required")
        sys.exit(1)

    if config.file and config.preset:
        print("❌ Error: Cannot use both --file and --preset, choose one")
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
            import base64

            # For CLI, we need to handle file objects differently
            print(f"📁 Loading image from: {config.file}")
            with open(config.file, "rb") as f:
                image_data = f.read()
                image_base64 = base64.b64encode(image_data).decode("utf-8")

            print(f"📏 Image loaded, size: {len(image_data)} bytes")

        except Exception as e:
            print(f"❌ Error loading image file: {e}")
            sys.exit(1)

    # Create client and send image
    client = Quote0(config.api_key, config.device_id)

    print(f"📤 Sending image to Quote/0 device... (border: {config.border.name})")
    response = client.send_image(
        image_base64=image_base64,
        border=config.border,
        refresh_now=not config.no_refresh,
        link=config.link,
        dither_type=config.dither_type,
        dither_kernel=config.dither_kernel,
    )

    if response.success:
        print(f"✅ {response.message}")
    else:
        print(f"❌ {response.message}")
        if response.error:
            print(f"Error details: {response.error}")
        sys.exit(1)


def main() -> None:
    """Main CLI entry point"""
    # Use tyro's Union-based subcommand support
    config = tyro.cli(Union[TextConfig, ImageConfig])

    if isinstance(config, TextConfig):
        text_command(config)
    elif isinstance(config, ImageConfig):
        image_command(config)
    else:
        print("❌ Error: Unknown configuration type")
        sys.exit(1)


if __name__ == "__main__":
    main()

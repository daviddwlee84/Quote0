#!/usr/bin/env python3
"""
Quote/0 CLI Tool - Send text and images to your Quote/0 device
"""

import os
import sys
from typing import Optional
from pathlib import Path
import tyro
from enum import Enum

from .client import Quote0
from .models import BorderColor
from .utils import get_preset_images


class PresetImageName(Enum):
    """Available preset images"""

    ALL_BLACK = "all_black"
    CHECKERBOARD_GRAY = "checkerboard_gray"
    ONE_PIXEL_BLACK = "1x1_black"


def text_command(
    api_key: str = os.getenv("DOT_API_KEY", ""),
    device_id: str = os.getenv("DOT_DEVICE_ID", ""),
    no_refresh: bool = False,
    title: Optional[str] = None,
    message: Optional[str] = None,
    signature: Optional[str] = None,
    link: Optional[str] = None,
    icon_file: Optional[Path] = None,
) -> None:
    """Send text to Quote/0 device.

    Args:
        api_key: DOT API key (defaults to DOT_API_KEY environment variable)
        device_id: DOT device ID (defaults to DOT_DEVICE_ID environment variable)
        no_refresh: Don't refresh the display immediately after sending
        title: Text title to display
        message: Text content to display
        signature: Text signature to display
        link: HTTP/HTTPS link or Scheme URL for NFC touch
        icon_file: Path to PNG icon file (40px*40px)
    """
    if not api_key or not device_id:
        print("❌ Error: API key and device ID are required")
        print(
            "Set DOT_API_KEY and DOT_DEVICE_ID environment variables or use --api-key and --device-id flags"
        )
        sys.exit(1)

    if not any([title, message, signature]):
        print(
            "❌ Error: At least one of --title, --message, or --signature is required"
        )
        sys.exit(1)

    # Handle icon file
    icon_base64 = None
    if icon_file:
        if not icon_file.exists():
            print(f"❌ Error: Icon file not found: {icon_file}")
            sys.exit(1)

        try:
            import base64

            with open(icon_file, "rb") as f:
                icon_base64 = base64.b64encode(f.read()).decode("utf-8")
            print(f"📁 Loaded icon from: {icon_file}")
        except Exception as e:
            print(f"❌ Error loading icon file: {e}")
            sys.exit(1)

    # Create client and send text
    client = Quote0(api_key, device_id)

    print("📤 Sending text to Quote/0 device...")
    response = client.send_text(
        refresh_now=not no_refresh,
        title=title,
        message=message,
        signature=signature,
        icon=icon_base64,
        link=link,
    )

    if response.success:
        print(f"✅ {response.message}")
    else:
        print(f"❌ {response.message}")
        if response.error:
            print(f"Error details: {response.error}")
        sys.exit(1)


def image_command(
    api_key: str = os.getenv("DOT_API_KEY", ""),
    device_id: str = os.getenv("DOT_DEVICE_ID", ""),
    no_refresh: bool = False,
    file: Optional[Path] = None,
    preset: Optional[PresetImageName] = None,
    border: BorderColor = BorderColor.WHITE,
    link: Optional[str] = None,
    dither_type: Optional[str] = None,
    dither_kernel: Optional[str] = None,
) -> None:
    """Send image to Quote/0 device.

    Args:
        api_key: DOT API key (defaults to DOT_API_KEY environment variable)
        device_id: DOT device ID (defaults to DOT_DEVICE_ID environment variable)
        no_refresh: Don't refresh the display immediately after sending
        file: Path to image file
        preset: Use a preset test image
        border: Border color (WHITE=0, BLACK=1)
        link: HTTP/HTTPS link or Scheme URL for NFC touch
        dither_type: Dithering type (DIFFUSION, ORDERED, NONE)
        dither_kernel: Dithering algorithm (only used when dither_type is DIFFUSION)
    """
    if not api_key or not device_id:
        print("❌ Error: API key and device ID are required")
        print(
            "Set DOT_API_KEY and DOT_DEVICE_ID environment variables or use --api-key and --device-id flags"
        )
        sys.exit(1)

    if not file and not preset:
        print("❌ Error: Either --file or --preset is required")
        sys.exit(1)

    if file and preset:
        print("❌ Error: Cannot use both --file and --preset, choose one")
        sys.exit(1)

    # Get image base64
    image_base64 = ""

    if preset:
        print(f"🖼️  Using preset image: {preset.value}")
        presets = get_preset_images()
        if preset.value not in presets:
            print(f"❌ Error: Unknown preset: {preset.value}")
            sys.exit(1)
        image_base64 = presets[preset.value].base64

    elif file:
        if not file.exists():
            print(f"❌ Error: Image file not found: {file}")
            sys.exit(1)

        try:
            import base64

            # For CLI, we need to handle file objects differently
            print(f"📁 Loading image from: {file}")
            with open(file, "rb") as f:
                image_data = f.read()
                image_base64 = base64.b64encode(image_data).decode("utf-8")

            print(f"📏 Image loaded, size: {len(image_data)} bytes")

        except Exception as e:
            print(f"❌ Error loading image file: {e}")
            sys.exit(1)

    # Create client and send image
    client = Quote0(api_key, device_id)

    print(f"📤 Sending image to Quote/0 device... (border: {border.name})")
    response = client.send_image(
        image_base64=image_base64,
        border=border,
        refresh_now=not no_refresh,
        link=link,
        dither_type=dither_type,
        dither_kernel=dither_kernel,
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
    # Use tyro's dictionary-based subcommand support for cleaner command names
    tyro.extras.subcommand_cli_from_dict(
        {
            "text": text_command,
            "image": image_command,
        }
    )


if __name__ == "__main__":
    main()

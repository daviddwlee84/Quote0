"""
Quote/0 Python API Package
"""

from .client import DotClient, Quote0
from .models import (
    CanvasApiRequest,
    DeviceInfo,
    DeviceSettingsRequest,
    DeviceSettings,
    DeviceStatus,
    DeviceTask,
    TimezoneInfo,
    TextStyles,
    ImageApiRequest,
    TextApiRequest,
    ApiResponse,
    PresetImage,
    BorderColor,
)
from .utils import image_to_base64, validate_image_dimensions, get_preset_images
from .streamlit_components import (
    setup_api_credentials,
    show_api_response,
    show_legacy_api_response,
)

__version__ = "0.1.1"

__all__ = [
    "Quote0",
    "DotClient",
    "CanvasApiRequest",
    "DeviceInfo",
    "DeviceSettingsRequest",
    "DeviceSettings",
    "DeviceStatus",
    "DeviceTask",
    "TimezoneInfo",
    "TextStyles",
    "ImageApiRequest",
    "TextApiRequest",
    "ApiResponse",
    "PresetImage",
    "BorderColor",
    "image_to_base64",
    "validate_image_dimensions",
    "get_preset_images",
    "setup_api_credentials",
    "show_api_response",
    "show_legacy_api_response",
]

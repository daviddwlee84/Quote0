"""
Quote/0 Python API Package
"""

from .client import Quote0
from .models import ImageApiRequest, TextApiRequest, ApiResponse, PresetImage
from .utils import image_to_base64, validate_image_dimensions, get_preset_images
from .streamlit_components import (
    setup_api_credentials,
    show_api_response,
    show_legacy_api_response,
)

__version__ = "0.1.0"

__all__ = [
    "Quote0",
    "ImageApiRequest",
    "TextApiRequest",
    "ApiResponse",
    "PresetImage",
    "image_to_base64",
    "validate_image_dimensions",
    "get_preset_images",
    "setup_api_credentials",
    "show_api_response",
    "show_legacy_api_response",
]

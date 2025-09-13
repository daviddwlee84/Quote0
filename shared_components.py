"""
Shared components for Quote/0 API Playground - Legacy compatibility layer
"""

from typing import Optional, Dict, Any
from streamlit.runtime.uploaded_file_manager import UploadedFile

# Import from the new quote0 package
from src.quote0 import (
    Quote0,
    BorderColor,
    setup_api_credentials,
    show_legacy_api_response as show_api_response,
    image_to_base64,
    validate_image_dimensions,
    get_preset_images,
)


def call_image_api(
    api_key: str,
    device_id: str,
    image_base64: str,
    border: int = 0,
    refresh_now: bool = True,
    link: Optional[str] = None,
    dither_type: Optional[str] = None,
    dither_kernel: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Call the Quote/0 Image API (Legacy wrapper)

    Args:
        api_key: DOT API key
        device_id: DOT device ID
        image_base64: Base64 encoded image string
        border: Border color (default: 0=white, 1=black)
        refresh_now: Whether to refresh display immediately (default: True)
        link: Optional link for NFC touch (default: None)
        dither_type: Optional dithering type (DIFFUSION, ORDERED, NONE) (default: None)
        dither_kernel: Optional dithering algorithm (only used when dither_type is DIFFUSION) (default: None)

    Returns:
        API response as dictionary
    """
    client = Quote0(api_key, device_id)

    # Convert int border to BorderColor enum for backward compatibility
    border_color = BorderColor.WHITE if border == 0 else BorderColor.BLACK

    response = client.send_image(
        image_base64=image_base64,
        border=border_color,
        refresh_now=refresh_now,
        link=link,
        dither_type=dither_type,
        dither_kernel=dither_kernel,
    )

    # Convert to legacy format
    return {
        "success": response.success,
        "status_code": response.status_code,
        "response": response.response or {},
        "message": response.message,
        "error": response.error,
    }


def call_text_api(
    api_key: str,
    device_id: str,
    refresh_now: bool = True,
    title: Optional[str] = None,
    message: Optional[str] = None,
    signature: Optional[str] = None,
    icon: Optional[str] = None,
    link: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Call the Quote/0 Text API (Legacy wrapper)

    Args:
        api_key: DOT API key
        device_id: DOT device ID
        refresh_now: Whether to refresh display immediately (default: True)
        title: Text title to display (optional)
        message: Text content to display (optional)
        signature: Text signature to display (optional)
        icon: Base64 encoded PNG icon data (40px*40px) (optional)
        link: HTTP/HTTPS link or Scheme URL for NFC touch (optional)

    Returns:
        API response as dictionary
    """
    client = Quote0(api_key, device_id)
    response = client.send_text(
        refresh_now=refresh_now,
        title=title,
        message=message,
        signature=signature,
        icon=icon,
        link=link,
    )

    # Convert to legacy format
    return {
        "success": response.success,
        "status_code": response.status_code,
        "response": response.response or {},
        "message": response.message,
        "error": response.error,
    }


# Legacy functions are now imported from src.quote0
# All functions (image_to_base64, validate_image_dimensions, get_preset_images, show_api_response, setup_api_credentials)
# are available through the imports at the top of this file

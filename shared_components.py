"""
Shared components for Quote/0 API Playground
"""

import os
import streamlit as st
import requests
import base64
import io
from typing import Optional, Dict, Any, Union
from streamlit.runtime.uploaded_file_manager import UploadedFile

try:
    from dotenv import load_dotenv
except ImportError:
    # Fallback if dotenv is not available
    def load_dotenv() -> None:
        pass


# Load environment variables from .env file
load_dotenv()


def setup_api_credentials() -> tuple[str, str]:
    """
    Setup API credentials in sidebar with environment variables as defaults.
    Returns tuple of (api_key, device_id)
    """
    st.sidebar.header("🔑 API Configuration")

    # Get default values from environment variables
    default_api_key = os.getenv("DOT_API_KEY", "")
    default_device_id = os.getenv("DOT_DEVICE_ID", "")

    # Input fields in sidebar
    api_key = st.sidebar.text_input(
        "DOT API Key",
        value=default_api_key,
        type="password",
        help="Your Quote/0 API key from the mobile app",
    )

    device_id = st.sidebar.text_input(
        "DOT Device ID",
        value=default_device_id,
        help="Your Quote/0 device ID from the mobile app",
    )

    # Validation
    if not api_key:
        st.sidebar.warning("⚠️ Please enter your API key")
    if not device_id:
        st.sidebar.warning("⚠️ Please enter your device ID")

    # Status indicator
    if api_key and device_id:
        st.sidebar.success("✅ API credentials configured")
    else:
        st.sidebar.error("❌ API credentials missing")

    return api_key, device_id


def call_image_api(
    api_key: str,
    device_id: str,
    image_base64: str,
    border: int = 0,
    refresh_now: bool = True,
) -> Dict[str, Any]:
    """
    Call the Quote/0 Image API

    Args:
        api_key: DOT API key
        device_id: DOT device ID
        image_base64: Base64 encoded image string
        border: Border size (default: 0)
        refresh_now: Whether to refresh display immediately (default: True)

    Returns:
        API response as dictionary
    """
    url = "https://dot.mindreset.tech/api/open/image"

    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    payload = {
        "refreshNow": refresh_now,
        "deviceId": device_id,
        "image": image_base64,
        "border": border,
    }

    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        return {
            "success": True,
            "status_code": response.status_code,
            "response": response.json() if response.content else {},
            "message": "Image sent successfully!",
        }
    except requests.exceptions.RequestException as e:
        return {
            "success": False,
            "error": str(e),
            "message": f"API call failed: {str(e)} ({response.text})",
        }


def call_text_api(
    api_key: str, device_id: str, text_content: str, refresh_now: bool = True
) -> Dict[str, Any]:
    """
    Call the Quote/0 Text API

    Args:
        api_key: DOT API key
        device_id: DOT device ID
        text_content: Text content to display
        refresh_now: Whether to refresh display immediately (default: True)

    Returns:
        API response as dictionary
    """
    url = "https://dot.mindreset.tech/api/open/text"

    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    payload = {"refreshNow": refresh_now, "deviceId": device_id, "text": text_content}

    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        return {
            "success": True,
            "status_code": response.status_code,
            "response": response.json() if response.content else {},
            "message": "Text sent successfully!",
        }
    except requests.exceptions.RequestException as e:
        return {
            "success": False,
            "error": str(e),
            "message": f"API call failed: {str(e)} ({response.text})",
        }


def image_to_base64(
    image_file: Optional[UploadedFile],
    target_width: int = 296,
    target_height: int = 152,
    max_size_kb: int = 50,
) -> str:
    """
    Convert uploaded image file to PNG base64 string with size optimization

    Args:
        image_file: Streamlit uploaded file object
        target_width: Target width for Quote/0 display (default: 296)
        target_height: Target height for Quote/0 display (default: 152)
        max_size_kb: Maximum file size in KB (default: 50KB)

    Returns:
        Base64 encoded PNG image string
    """
    if image_file is not None:
        try:
            from PIL import Image

            # Open the image with PIL
            image = Image.open(image_file)

            # Convert to RGB if necessary (removes alpha channel for JPEG compatibility)
            if image.mode in ("RGBA", "LA", "P"):
                # Create a white background for transparency
                background = Image.new("RGB", image.size, (255, 255, 255))
                if image.mode == "P":
                    image = image.convert("RGBA")
                background.paste(
                    image,
                    mask=image.split()[-1] if image.mode in ("RGBA", "LA") else None,
                )
                image = background
            elif image.mode not in ("RGB", "L"):
                image = image.convert("RGB")

            # Resize image to Quote/0 dimensions while maintaining aspect ratio
            original_width, original_height = image.size
            aspect_ratio = original_width / original_height
            target_aspect_ratio = target_width / target_height

            if aspect_ratio > target_aspect_ratio:
                # Image is wider, fit by width
                new_width = target_width
                new_height = int(target_width / aspect_ratio)
            else:
                # Image is taller, fit by height
                new_height = target_height
                new_width = int(target_height * aspect_ratio)

            # Only resize if the image is larger than target dimensions
            if original_width > target_width or original_height > target_height:
                image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)

            # Convert to PNG format in memory with optimization
            png_buffer = io.BytesIO()

            # Try different quality settings if file is too large
            quality = 95
            image.save(png_buffer, format="PNG", optimize=True, quality=quality)
            png_bytes = png_buffer.getvalue()

            # Check file size and reduce quality if needed
            while len(png_bytes) > max_size_kb * 1024 and quality > 10:
                png_buffer = io.BytesIO()
                quality -= 10
                image.save(png_buffer, format="PNG", optimize=True, quality=quality)
                png_bytes = png_buffer.getvalue()

            # If still too large, reduce dimensions
            while (
                len(png_bytes) > max_size_kb * 1024 and min(new_width, new_height) > 50
            ):
                new_width = int(new_width * 0.9)
                new_height = int(new_height * 0.9)
                image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
                png_buffer = io.BytesIO()
                image.save(png_buffer, format="PNG", optimize=True, quality=quality)
                png_bytes = png_buffer.getvalue()

            # Convert to base64
            base64_string = base64.b64encode(png_bytes).decode("utf-8")

            return base64_string

        except Exception as e:
            st.error(f"Error converting image to PNG: {str(e)}")
            return ""
    return ""


def validate_image_dimensions(
    image_file: UploadedFile, target_width: int = 296, target_height: int = 152
) -> bool:
    """
    Validate if image dimensions are suitable for Quote/0 display

    Args:
        image_file: Streamlit uploaded file object
        target_width: Target width (default: 296px)
        target_height: Target height (default: 152px)

    Returns:
        True if dimensions are valid or acceptable
    """
    try:
        from PIL import Image

        image = Image.open(image_file)
        width, height = image.size

        # Check if dimensions match exactly
        if width == target_width and height == target_height:
            return True

        # Check if aspect ratio is close
        target_ratio = target_width / target_height
        actual_ratio = width / height

        # Allow some tolerance for aspect ratio
        if abs(target_ratio - actual_ratio) < 0.1:
            return True

        return False
    except Exception:
        # If we can't validate, assume it's ok
        return True


def get_preset_images() -> Dict[str, Dict[str, str]]:
    """
    Get preset test images for Quote/0

    Returns:
        Dictionary of preset images with name, description, and base64 data
    """
    return {
        "1x1_black": {
            "name": "1×1 Black Pixel",
            "description": "Minimal test image (1×1 black pixel)",
            "base64": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQd1PeAAAADElEQVR42mNgYGAAAAAEAAHI6uv5AAAAAElFTkSuQmCC",
            "dimensions": "1×1",
        },
        "all_black": {
            "name": "All Black (296×152)",
            "description": "Full size black image for Quote/0",
            "base64": "iVBORw0KGgoAAAANSUhEUgAAASgAAACYAQAAAAB/wUl1AAAAHElEQVR4nO3BMQEAAADCoPVPbQo/oAAAAAAA4G8WkAABUhYjKAAAAABJRU5ErkJggg==",
            "dimensions": "296×152",
        },
        "checkerboard_gray": {
            "name": "Checkerboard Gray",
            "description": "Gray checkerboard pattern (296×152)",
            "base64": "iVBORw0KGgoAAAANSUhEUgAAASgAAACYAQAAAAB/wUl1AAAAN0lEQVR4nO3MsQ0AMAgEsSBlRZZkSlb4Hl99cs0Lqk6uH10sFovFYrFYLBaLxWKxWCwWi8W6aC1FhjRHozCNPQAAAABJRU5ErkJggg==",
            "dimensions": "296×152",
        },
    }


def show_api_response(response: Dict[str, Any]) -> None:
    """
    Display API response in Streamlit UI

    Args:
        response: API response dictionary
    """
    if response["success"]:
        st.success(response["message"])
        if response.get("response"):
            with st.expander("📋 API Response Details"):
                st.json(response["response"])
    else:
        st.error(response["message"])
        with st.expander("🔍 Error Details"):
            st.code(response.get("error", "Unknown error"))

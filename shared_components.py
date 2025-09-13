"""
Shared components for Quote/0 API Playground
"""

import os
import streamlit as st
import requests
import base64
from typing import Optional, Dict, Any

try:
    from dotenv import load_dotenv
except ImportError:
    # Fallback if dotenv is not available
    def load_dotenv():
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
    default_api_key = os.getenv('DOT_API_KEY', '')
    default_device_id = os.getenv('DOT_DEVICE_ID', '')
    
    # Input fields in sidebar
    api_key = st.sidebar.text_input(
        "DOT API Key",
        value=default_api_key,
        type="password",
        help="Your Quote/0 API key from the mobile app"
    )
    
    device_id = st.sidebar.text_input(
        "DOT Device ID", 
        value=default_device_id,
        help="Your Quote/0 device ID from the mobile app"
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

def call_image_api(api_key: str, device_id: str, image_base64: str, border: int = 0, refresh_now: bool = True) -> Dict[str, Any]:
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
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "refreshNow": refresh_now,
        "deviceId": device_id,
        "image": image_base64,
        "border": border
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        return {
            "success": True,
            "status_code": response.status_code,
            "response": response.json() if response.content else {},
            "message": "Image sent successfully!"
        }
    except requests.exceptions.RequestException as e:
        return {
            "success": False,
            "error": str(e),
            "message": f"API call failed: {str(e)}"
        }

def call_text_api(api_key: str, device_id: str, text_content: str, refresh_now: bool = True) -> Dict[str, Any]:
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
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "refreshNow": refresh_now,
        "deviceId": device_id,
        "text": text_content
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        return {
            "success": True,
            "status_code": response.status_code,
            "response": response.json() if response.content else {},
            "message": "Text sent successfully!"
        }
    except requests.exceptions.RequestException as e:
        return {
            "success": False,
            "error": str(e),
            "message": f"API call failed: {str(e)}"
        }

def image_to_base64(image_file) -> str:
    """
    Convert uploaded image file to base64 string
    
    Args:
        image_file: Streamlit uploaded file object
        
    Returns:
        Base64 encoded image string
    """
    if image_file is not None:
        # Read the image file
        image_bytes = image_file.read()
        # Convert to base64
        base64_string = base64.b64encode(image_bytes).decode('utf-8')
        return base64_string
    return ""

def validate_image_dimensions(image_file, target_width: int = 296, target_height: int = 152) -> bool:
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

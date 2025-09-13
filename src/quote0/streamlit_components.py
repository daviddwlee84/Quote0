"""
Streamlit-specific components for Quote/0 API Playground
"""

import os
import streamlit as st
from typing import Dict, Any
from .models import ApiResponse


def setup_api_credentials() -> tuple[str, str]:
    """
    Setup API credentials in sidebar with environment variables as defaults.
    Returns tuple of (api_key, device_id)
    """
    try:
        from dotenv import load_dotenv

        load_dotenv()
    except ImportError:
        pass

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


def show_api_response(response: ApiResponse) -> None:
    """
    Display API response in Streamlit UI

    Args:
        response: ApiResponse object
    """
    if response.success:
        st.success(response.message)
        if response.response:
            with st.expander("📋 API Response Details"):
                st.json(response.response)
    else:
        st.error(response.message)
        with st.expander("🔍 Error Details"):
            st.code(response.error or "Unknown error")


def show_legacy_api_response(response: Dict[str, Any]) -> None:
    """
    Display legacy API response format in Streamlit UI (for backward compatibility)

    Args:
        response: API response dictionary (legacy format)
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

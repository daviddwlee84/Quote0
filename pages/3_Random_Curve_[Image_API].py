"""
Random Curve Generator with Fragment Refresh - Quote/0 Image API Demo
"""

import streamlit as st
from typing import Literal, Dict, List, Any
from datetime import datetime, timedelta
import io
import base64
import numpy as np
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import random
import time

matplotlib.use("Agg")

# Import shared components
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared_components import (
    setup_api_credentials,
    call_image_api,
    show_api_response,
)
from src.quote0.models import BorderColor

st.set_page_config(page_title="Random Curve - Quote/0", page_icon="📈", layout="wide")

st.title("📈 Random Curve Generator")
st.markdown(
    "Generate and display random curves on your Quote/0 device with auto-refresh"
)

# Setup API credentials in sidebar
with st.sidebar:
    api_key, device_id = setup_api_credentials()

    # Add sidebar info
    st.markdown("---")
    st.markdown("**💡 Tips**")
    st.markdown("• Auto-refresh every 10 seconds")
    st.markdown("• Data grows over time")
    st.markdown("• Configurable parameters")
    st.markdown("• Optional auto-send to device")

    # Configuration options
    st.markdown("---")
    st.markdown("### ⚙️ Configuration")

    initial_data_length = st.slider(
        "Initial data length",
        min_value=10,
        max_value=100,
        value=50,
        help="Starting number of data points",
    )

    max_data_length = st.slider(
        "Max data length",
        min_value=50,
        max_value=500,
        value=200,
        help="Maximum data points before reset",
    )

    volatility = st.slider(
        "Volatility",
        min_value=0.1,
        max_value=2.0,
        value=0.8,
        step=0.1,
        help="How much the curve fluctuates",
    )

    growth_rate = st.slider(
        "Growth rate",
        min_value=-0.01,
        max_value=0.01,
        value=0.002,
        step=0.001,
        help="Overall trend (positive = up, negative = down)",
    )

    auto_send = st.checkbox(
        "Auto-send to Quote/0 on refresh",
        value=False,
        help="Automatically send curve to device when it refreshes",
    )


def _format_large_number(value: float) -> str:
    """Format large numbers with K (thousand) or M (million) suffix."""
    if abs(value) >= 1_000_000:
        return f"{value / 1_000_000:.1f}M"
    elif abs(value) >= 1_000:
        return f"{value / 1_000:.1f}K"
    else:
        return f"{value:,.0f}"


def _generate_mock_data(
    data_length: int,
    volatility: float = 0.8,
    growth_rate: float = 0.002,
) -> Dict[str, Any]:
    """
    Generate mock trading data for demonstration purposes.

    Args:
        data_length: Number of data points to generate
        volatility: How much the price fluctuates (0.1 to 2.0)
        growth_rate: Overall trend direction (-0.01 to 0.01)

    Returns:
        Dictionary containing times, profit data, and metrics
    """
    # Generate timestamps (simulate trading hours)
    base_time = datetime.now().replace(hour=9, minute=0, second=0, microsecond=0)
    times = []

    for i in range(data_length):
        # Simulate trading hours: 9:00-11:30, 13:00-15:00
        if i < 30:  # Morning session
            time_offset = timedelta(minutes=i * 2)
        else:  # Afternoon session
            time_offset = timedelta(hours=2, minutes=(i - 30) * 2)

        times.append(base_time + time_offset)

    # Generate random walk profit data
    np.random.seed(42)  # For reproducible results
    profits = []
    current_profit = 0.0

    for i in range(data_length):
        # Random walk with drift
        change = np.random.normal(growth_rate, volatility * 0.01)
        current_profit += change * (
            10000 + abs(current_profit)
        )  # Scale based on current value
        profits.append(current_profit)

    # Convert to numpy array
    profits = np.array(profits, dtype=float)

    # Generate mock trading metrics
    latest_total_profit = profits[-1] if len(profits) > 0 else 0.0
    latest_settle_profit = latest_total_profit * 0.7  # Assume 70% is settled
    latest_float_profit = latest_total_profit * 0.3  # Assume 30% is floating
    latest_total_turnover = abs(latest_total_profit) * 1000  # Mock turnover
    latest_active_turnover = latest_total_turnover * 0.6  # Active portion

    rate_of_return_bp = (
        (latest_total_profit / latest_total_turnover * 10000)
        if latest_total_turnover != 0
        else 0.0
    )

    return {
        "times": times,
        "total_profit": profits,
        "metrics": {
            "total": latest_total_profit,
            "settle": latest_settle_profit,
            "float": latest_float_profit,
            "return_bp": rate_of_return_bp,
            "turnover": latest_total_turnover,
            "active_turnover": latest_active_turnover,
        },
    }


def render_mock_curve_base64(
    data_length: int,
    *,
    width: int = 296,
    height: int = 152,
    dpi: int = 100,
    show_zero_axis: bool = True,
    x_mode: Literal["index", "time"] = "index",
    facecolor: str | None = None,
    volatility: float = 0.8,
    growth_rate: float = 0.002,
) -> str:
    """
    Generate a random curve and render it as base64 PNG.
    Similar to render_compact_base64_from_api but uses mock data.

    Args:
        data_length: Number of data points
        width: Image width in pixels
        height: Image height in pixels
        dpi: DPI for rendering
        show_zero_axis: Whether to show zero line
        x_mode: 'index' for simple x-axis, 'time' for datetime x-axis
        facecolor: Background color (None for transparent)
        volatility: Curve volatility
        growth_rate: Overall trend

    Returns:
        Base64 encoded PNG image
    """
    # Generate mock data
    s = _generate_mock_data(data_length, volatility, growth_rate)

    # Setup matplotlib
    fig = plt.figure(figsize=(width / dpi, height / dpi), dpi=dpi, facecolor=facecolor)

    # Header text
    m = s["metrics"]
    fig.text(
        0.02,
        0.92,
        f"Random Curve ({datetime.now().strftime('%m/%d %H:%M:%S')})",
        fontsize=8,
        weight="bold",
    )
    fig.text(0.02, 0.78, f"Total: {m['total']:,.0f}", fontsize=8)
    fig.text(0.35, 0.78, f"Settle: {m['settle']:,.0f}", fontsize=8)
    fig.text(0.68, 0.78, f"Float: {m['float']:,.0f}", fontsize=8)
    fig.text(0.02, 0.64, f"Return: {m['return_bp']:.2f} bp", fontsize=8)
    fig.text(0.35, 0.64, f"Turnover: {_format_large_number(m['turnover'])}", fontsize=7)
    fig.text(
        0.68, 0.64, f"Active: {_format_large_number(m['active_turnover'])}", fontsize=7
    )

    # Curve plot
    ax = fig.add_axes([0.06, 0.08, 0.90, 0.50])

    y = s["total_profit"]
    if len(y) == 0:
        y = np.array([0.0])

    if x_mode == "time" and len(s["times"]) == len(y):
        x = mdates.date2num(s["times"])
    else:
        x = np.arange(len(y))

    # Set y-limits
    ymin, ymax = float(y.min()), float(y.max())
    if show_zero_axis:
        ymin = min(ymin, 0.0)
        ymax = max(ymax, 0.0)
    pad = (ymax - ymin) * 0.07 if ymax > ymin else 1.0
    ax.set_ylim(ymin - pad, ymax + pad)
    ax.set_xlim(x.min(), x.max())

    # Plot curve
    ax.plot(x, y, linewidth=1.6)

    # Zero axis
    if show_zero_axis:
        ax.axhline(0, linewidth=0.8)

    # Minimal styling
    ax.axis("off")

    # Convert to base64
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=dpi)
    plt.close(fig)
    return base64.b64encode(buf.getvalue()).decode("ascii")


# Main content
col1, col2 = st.columns([1, 1])

with col1:
    st.header("📊 Live Random Curve")

    # Session state for data management
    if "data_length" not in st.session_state:
        st.session_state.data_length = initial_data_length
    if "start_time" not in st.session_state:
        st.session_state.start_time = time.time()

    @st.fragment(run_every=10)
    def update_curve():
        """Fragment that updates every 10 seconds"""
        # Simulate data growth over time
        elapsed_time = time.time() - st.session_state.start_time
        growth_factor = min(1.0, elapsed_time / 300)  # Full growth after 5 minutes
        current_length = int(
            initial_data_length
            + (max_data_length - initial_data_length) * growth_factor
        )

        # Reset if we hit max length
        if current_length >= max_data_length:
            st.session_state.start_time = time.time()
            current_length = initial_data_length

        st.session_state.data_length = current_length

        # Generate and display curve
        try:
            b64_image = render_mock_curve_base64(
                data_length=st.session_state.data_length,
                show_zero_axis=True,
                x_mode="index",
                facecolor=None,
                volatility=volatility,
                growth_rate=growth_rate,
            )

            # Display the image
            import base64 as b64_module

            image_data = b64_module.b64decode(b64_image)
            st.image(
                image_data,
                caption=f"Random Curve (Points: {st.session_state.data_length})",
                use_container_width=True,
            )

            # Show current metrics
            s = _generate_mock_data(
                st.session_state.data_length, volatility, growth_rate
            )
            m = s["metrics"]

            st.markdown("### 📈 Current Metrics")
            col_a, col_b, col_c = st.columns(3)
            with col_a:
                st.metric("Total Profit", f"{m['total']:,.0f}")
            with col_b:
                st.metric("Return (bp)", f"{m['return_bp']:.2f} bp")
            with col_c:
                st.metric("Turnover", f"{_format_large_number(m['turnover'])}")

            # Auto-send to Quote/0 if enabled
            if auto_send and api_key and device_id:
                try:
                    # Prepare API call for auto-send
                    api_kwargs = {
                        "api_key": api_key,
                        "device_id": device_id,
                        "image_base64": b64_image,
                        "border": BorderColor.WHITE.value,  # Default border for auto-send
                        "refresh_now": True,  # Always refresh for auto-send
                    }

                    # Call API without showing response to avoid cluttering the UI
                    response = call_image_api(**api_kwargs)

                    # Show minimal success indicator
                    if response.get("success"):
                        st.success("✅ Auto-sent to Quote/0", icon="📡")
                    else:
                        st.warning("⚠️ Auto-send failed", icon="⚠️")

                except Exception as e:
                    st.warning(f"⚠️ Auto-send error: {str(e)[:50]}...", icon="⚠️")

        except Exception as e:
            st.error(f"Error generating curve: {e}")

    # Call the fragment function
    update_curve()

with col2:
    st.header("🎯 Send to Quote/0")

    # API options
    st.markdown("### ⚙️ API Options")

    border = st.selectbox(
        "Border Color",
        options=[BorderColor.WHITE, BorderColor.BLACK],
        format_func=lambda x: "White" if x == BorderColor.WHITE else "Black",
        help="Border color for the display",
    )

    refresh_now = st.checkbox(
        "Refresh immediately",
        value=True,
        help="Whether to refresh the display immediately after sending",
    )

    # Advanced options
    with st.expander("🎨 Advanced Options"):
        link = st.text_input(
            "NFC Link (optional)",
            placeholder="https://example.com",
            help="URL to open when NFC is touched",
        )

    # Send button
    if st.button(
        "🚀 Send Current Curve to Quote/0",
        type="primary",
        disabled=not (api_key and device_id),
    ):
        if not api_key or not device_id:
            st.error("❌ Please configure your API credentials in the sidebar first!")
        else:
            with st.spinner("Generating and sending curve..."):
                try:
                    # Generate current curve
                    b64_image = render_mock_curve_base64(
                        data_length=st.session_state.data_length,
                        show_zero_axis=True,
                        x_mode="index",
                        facecolor=None,
                        volatility=volatility,
                        growth_rate=growth_rate,
                    )

                    # Prepare API call
                    api_kwargs = {
                        "api_key": api_key,
                        "device_id": device_id,
                        "image_base64": b64_image,
                        "border": border.value,
                        "refresh_now": refresh_now,
                    }

                    # Add link if provided
                    if link.strip():
                        api_kwargs["link"] = link.strip()

                    # Call API
                    response = call_image_api(**api_kwargs)

                    # Show response
                    show_api_response(response)

                except Exception as e:
                    st.error(f"❌ Error sending to Quote/0: {e}")

    st.markdown("---")
    st.markdown("### 📋 Current Settings")
    st.info(
        f"""
    • **Data Points:** {st.session_state.data_length}
    • **Volatility:** {volatility}
    • **Growth Rate:** {growth_rate}
    • **Auto-refresh:** Every 10 seconds
    • **Auto-send:** {"Enabled" if auto_send else "Disabled"}
    """
    )

# Footer
st.markdown("---")
st.markdown(
    "📚 **Documentation:** [Image API Docs](https://dot.mindreset.tech/docs/server/template/api/image_api)"
)

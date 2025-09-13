"""
Image API Page for Quote/0 API Playground
"""

import streamlit as st
from PIL import Image
import io
import sys
import os

# Add parent directory to path to import shared components
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared_components import (
    setup_api_credentials,
    call_image_api,
    image_to_base64,
    validate_image_dimensions,
    show_api_response,
    get_preset_images,
)

st.set_page_config(page_title="Image API - Quote/0", page_icon="📷", layout="wide")

st.title("📷 Image API")
st.markdown("Upload and display images on your Quote/0 device (296px × 152px)")

# Setup API credentials in sidebar
api_key, device_id = setup_api_credentials()

# Add sidebar info
st.sidebar.markdown("---")
st.sidebar.markdown("**💡 Tips**")
st.sidebar.markdown("• Optimal size: 296×152 pixels")
st.sidebar.markdown("• Supports: PNG, JPG, JPEG")
st.sidebar.markdown("• Black & white works best")
st.sidebar.markdown("• Use high contrast images")

# Main content area
col1, col2 = st.columns([1, 1])

with col1:
    st.header("🖼️ Image Upload")

    # Option to choose between upload and preset
    image_source = st.radio(
        "Image source:",
        ["Upload file", "Use preset image"],
        help="Choose to upload your own image or use a preset test image",
    )

    uploaded_file = None
    preset_base64 = None

    if image_source == "Upload file":
        # File uploader
        uploaded_file = st.file_uploader(
            "Choose an image file",
            type=["png", "jpg", "jpeg"],
            help="Upload PNG, JPG, or JPEG files. Optimal size is 296×152 pixels.",
        )
    else:
        # Preset image selector
        preset_images = get_preset_images()
        preset_options = [
            f"{img['name']} ({img['dimensions']})" for img in preset_images.values()
        ]
        preset_keys = list(preset_images.keys())

        selected_preset_idx = st.selectbox(
            "Choose a preset image:",
            range(len(preset_options)),
            format_func=lambda x: preset_options[x],
            help="Select a preset test image",
        )

        if selected_preset_idx is not None:
            selected_preset_key = preset_keys[selected_preset_idx]
            selected_preset = preset_images[selected_preset_key]
            preset_base64 = selected_preset["base64"]

            st.info(f"✅ Selected: {selected_preset['name']}")
            st.markdown(f"**Description:** {selected_preset['description']}")

            # Show preset image preview
            import base64
            from PIL import Image
            import io

            try:
                # Decode base64 to show preview
                image_data = base64.b64decode(preset_base64)
                preset_image = Image.open(io.BytesIO(image_data))
                st.image(
                    preset_image,
                    caption=f"{selected_preset['name']} ({selected_preset['dimensions']})",
                    width="stretch",
                )
            except Exception as e:
                st.warning(f"Could not preview image: {e}")

    # Handle uploaded file display
    if uploaded_file is not None:
        # Display image info
        st.success(f"✅ File uploaded: {uploaded_file.name}")

        # Load and display image
        image = Image.open(uploaded_file)
        width, height = image.size

        st.info(f"📐 Image dimensions: {width}×{height} pixels")

        # Check dimensions
        if width == 296 and height == 152:
            st.success("✅ Perfect dimensions for Quote/0!")
        elif validate_image_dimensions(uploaded_file):
            st.warning("⚠️ Dimensions are close but not exact. Image will be resized.")
        else:
            st.warning("⚠️ Image dimensions may not be optimal for Quote/0 display.")

        # Display image preview
        st.image(
            image, caption=f"{uploaded_file.name} ({width}×{height})", width="stretch"
        )

    # API options - Always show regardless of image source
    st.header("⚙️ API Options")

    # Basic options
    col_basic1, col_basic2 = st.columns(2)
    with col_basic1:
        border = st.number_input(
            "Border size",
            min_value=0,
            max_value=1,
            value=0,
            help="0 = white border, 1 = black border",
        )

    with col_basic2:
        refresh_now = st.checkbox(
            "Refresh immediately",
            value=True,
            help="Whether to refresh the display immediately after sending",
        )

    # Initialize variables outside expander
    link = ""
    dither_type = "Default"
    dither_kernel = "FLOYD_STEINBERG"

    # Advanced options
    with st.expander("🎨 Advanced Options"):
        # Link option
        link = st.text_input(
            "NFC Link (optional)",
            placeholder="https://example.com or app://scheme",
            help="URL to open when NFC is touched",
        )

        # Dithering options
        col_dither1, col_dither2 = st.columns(2)

        with col_dither1:
            dither_type = st.selectbox(
                "Dithering Type",
                ["Default", "DIFFUSION", "ORDERED", "NONE"],
                index=0,
                help="Image dithering algorithm type",
            )

        with col_dither2:
            # Only show dither kernel if DIFFUSION is selected
            if dither_type == "DIFFUSION":
                dither_kernel = st.selectbox(
                    "Dithering Algorithm",
                    [
                        "FLOYD_STEINBERG",
                        "ATKINSON",
                        "BURKES",
                        "SIERRA2",
                        "STUCKI",
                        "JARVIS_JUDICE_NINKE",
                        "DIFFUSION_ROW",
                        "DIFFUSION_COLUMN",
                        "DIFFUSION_2D",
                    ],
                    index=0,
                    help="Specific dithering algorithm (only for DIFFUSION type)",
                )
            else:
                dither_kernel = "FLOYD_STEINBERG"  # Default value, won't be used

    # Send button - Always show if we have image source
    has_image = uploaded_file is not None or preset_base64 is not None
    if st.button(
        "🚀 Send to Quote/0",
        type="primary",
        disabled=not (api_key and device_id and has_image),
    ):
        if not api_key or not device_id:
            st.error("❌ Please configure your API credentials in the sidebar first!")
        elif not has_image:
            st.error("❌ Please select an image first!")
        else:
            with st.spinner("Sending image to Quote/0..."):
                base64_image = None

                if image_source == "Upload file" and uploaded_file:
                    # Reset file pointer and convert uploaded file
                    uploaded_file.seek(0)
                    with st.spinner("Optimizing image size..."):
                        base64_image = image_to_base64(uploaded_file)
                        st.info("✅ Image optimized for Quote/0 (PNG, max 50KB)")
                elif image_source == "Use preset image" and preset_base64:
                    # Use preset base64 directly
                    base64_image = preset_base64

                if base64_image:
                    # Prepare optional parameters
                    api_kwargs = {
                        "api_key": api_key,
                        "device_id": device_id,
                        "image_base64": base64_image,
                        "border": border,
                        "refresh_now": refresh_now,
                    }

                    # Add link if provided
                    if link.strip():
                        api_kwargs["link"] = link.strip()

                    # Add dithering parameters if not default
                    if dither_type != "Default":
                        api_kwargs["dither_type"] = dither_type
                        if dither_type == "DIFFUSION":
                            api_kwargs["dither_kernel"] = dither_kernel

                    # Call API
                    response = call_image_api(**api_kwargs)

                    # Show response
                    show_api_response(response)
                else:
                    st.error("❌ Failed to get image data")

with col2:
    st.header("🎯 Quote/0 Preview")

    # Determine which image to preview
    preview_image = None
    preview_name = ""
    selected_preset_key = None

    if uploaded_file is not None:
        preview_image = Image.open(uploaded_file)
        preview_name = uploaded_file.name
    elif preset_base64 is not None and "selected_preset_idx" in locals():
        # Decode preset image for preview
        import base64
        import io

        try:
            image_data = base64.b64decode(preset_base64)
            preview_image = Image.open(io.BytesIO(image_data))
            preset_images = get_preset_images()
            preset_keys = list(preset_images.keys())
            selected_preset_key = preset_keys[selected_preset_idx]
            preview_name = preset_images[selected_preset_key]["name"]
        except Exception as e:
            st.error(f"Error loading preset image: {e}")
            preview_name = "Preset image"

    if preview_image is not None:
        # Resize to Quote/0 dimensions for preview
        quote0_size = (296, 152)
        preview_resized = preview_image.resize(quote0_size, Image.Resampling.LANCZOS)

        # Convert to grayscale for more accurate preview
        preview_gray = preview_resized.convert("L")

        st.markdown("**Preview on Quote/0 device:**")
        st.image(preview_gray, caption=f"Preview (296×152, grayscale)", width="stretch")

        # Show base64 preview
        with st.expander("🔍 Base64 Preview"):
            if image_source == "Upload file" and uploaded_file:
                uploaded_file.seek(0)
                base64_data = image_to_base64(uploaded_file)
            else:
                base64_data = preset_base64

            if base64_data:
                st.text_area(
                    "Base64 encoded image",
                    value=(
                        base64_data[:200] + "..."
                        if len(base64_data) > 200
                        else base64_data
                    ),
                    height=100,
                    help=f"Full length: {len(base64_data)} characters",
                )
    else:
        st.info("👆 Upload an image or select a preset to see preview")

        # Show sample images info
        st.markdown("**Sample test images:**")
        st.markdown(
            "You can test with the sample scripts in the `scripts/image_api_test/` directory:"
        )
        st.code(
            """
# Test with a 1x1 black pixel
./scripts/image_api_test/1x1_black.sh

# Test with all black image
./scripts/image_api_test/all_black.sh

# Test with checkerboard pattern
./scripts/image_api_test/checkerboard_gray.sh
        """
        )

# Footer info
st.markdown("---")
st.markdown(
    "📚 **Documentation:** [Image API Docs](https://dot.mindreset.tech/docs/server/template/api/image_api)"
)

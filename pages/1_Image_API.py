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
from shared_components import setup_api_credentials, call_image_api, image_to_base64, validate_image_dimensions, show_api_response

st.set_page_config(
    page_title="Image API - Quote/0",
    page_icon="📷",
    layout="wide"
)

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
    
    # File uploader
    uploaded_file = st.file_uploader(
        "Choose an image file",
        type=['png', 'jpg', 'jpeg'],
        help="Upload PNG, JPG, or JPEG files. Optimal size is 296×152 pixels."
    )
    
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
        st.image(image, caption=f"{uploaded_file.name} ({width}×{height})", use_column_width=True)
        
        # API options
        st.header("⚙️ API Options")
        
        col_opt1, col_opt2 = st.columns(2)
        with col_opt1:
            border = st.number_input(
                "Border size",
                min_value=0,
                max_value=10,
                value=0,
                help="Border around the image in pixels"
            )
        
        with col_opt2:
            refresh_now = st.checkbox(
                "Refresh immediately",
                value=True,
                help="Whether to refresh the display immediately after sending"
            )
        
        # Convert image to base64
        if st.button("🚀 Send to Quote/0", type="primary", disabled=not (api_key and device_id)):
            if not api_key or not device_id:
                st.error("❌ Please configure your API credentials in the sidebar first!")
            else:
                with st.spinner("Converting image and sending to Quote/0..."):
                    # Reset file pointer
                    uploaded_file.seek(0)
                    
                    # Convert to base64
                    base64_image = image_to_base64(uploaded_file)
                    
                    if base64_image:
                        # Call API
                        response = call_image_api(
                            api_key=api_key,
                            device_id=device_id,
                            image_base64=base64_image,
                            border=border,
                            refresh_now=refresh_now
                        )
                        
                        # Show response
                        show_api_response(response)
                    else:
                        st.error("❌ Failed to convert image to base64")

with col2:
    st.header("🎯 Quote/0 Preview")
    
    if uploaded_file is not None:
        # Create a preview showing how it would look on Quote/0
        preview_image = Image.open(uploaded_file)
        
        # Resize to Quote/0 dimensions for preview
        quote0_size = (296, 152)
        preview_resized = preview_image.resize(quote0_size, Image.Resampling.LANCZOS)
        
        # Convert to grayscale for more accurate preview
        preview_gray = preview_resized.convert('L')
        
        st.markdown("**Preview on Quote/0 device:**")
        st.image(
            preview_gray, 
            caption=f"Preview (296×152, grayscale)",
            use_column_width=True
        )
        
        # Show base64 preview
        with st.expander("🔍 Base64 Preview"):
            uploaded_file.seek(0)
            base64_data = image_to_base64(uploaded_file)
            if base64_data:
                st.text_area(
                    "Base64 encoded image",
                    value=base64_data[:200] + "..." if len(base64_data) > 200 else base64_data,
                    height=100,
                    help=f"Full length: {len(base64_data)} characters"
                )
    else:
        st.info("👆 Upload an image to see preview")
        
        # Show sample images info
        st.markdown("**Sample test images:**")
        st.markdown("You can test with the sample scripts in the `scripts/image_api_test/` directory:")
        st.code("""
# Test with a 1x1 black pixel
./scripts/image_api_test/1x1_black.sh

# Test with all black image
./scripts/image_api_test/all_black.sh

# Test with checkerboard pattern
./scripts/image_api_test/checkerboard_gray.sh
        """)

# Footer info
st.markdown("---")
st.markdown("📚 **Documentation:** [Image API Docs](https://dot.mindreset.tech/docs/server/template/api/image_api)")

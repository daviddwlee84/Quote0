"""
Text API Page for Quote/0 API Playground
"""

import streamlit as st
import sys
import os

# Add parent directory to path to import shared components
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared_components import (
    setup_api_credentials,
    call_text_api,
    show_api_response,
    image_to_base64,
)

st.set_page_config(page_title="Text API - Quote/0", page_icon="📝", layout="wide")

st.title("📝 Text API")
st.markdown("Send text content to your Quote/0 device")

# Setup API credentials in sidebar
with st.sidebar:
    api_key, device_id = setup_api_credentials()

# Add sidebar info
st.sidebar.markdown("---")
st.sidebar.markdown("**💡 Tips**")
st.sidebar.markdown("• Keep text concise")
st.sidebar.markdown("• Use line breaks for formatting")
st.sidebar.markdown("• E-ink displays work best with simple text")
st.sidebar.markdown("• Consider the 296×152 pixel display size")

# Main content area
col1, col2 = st.columns([2, 1])

with col1:
    st.header("✍️ Text Content")

    # Template selection
    st.markdown("### 📝 Text Template")

    template_options = {
        "Custom": {
            "title": "",
            "message": "",
            "signature": "",
            "link": "",
        },
        "Simple Message": {
            "title": "Hello",
            "message": "World from Quote/0!",
            "signature": "",
            "link": "",
        },
        "Weather Update": {
            "title": "Weather",
            "message": "San Francisco\n22°C\nSunny",
            "signature": "Today",
            "link": "x-apple-weather://",
        },
        "Reminder": {
            "title": "REMINDER",
            "message": "Team meeting",
            "signature": "3:00 PM",
            "link": "x-apple-reminder://",
        },
        "Status Update": {
            "title": "Status",
            "message": "Working on:\n• Task A\n• Task B",
            "signature": "Updated now",
            "link": "https://github.com",
        },
        "Quote of the Day": {
            "title": "Quote",
            "message": '"The best time to plant a tree was 20 years ago. The second best time is now."',
            "signature": "- Chinese Proverb",
            "link": "https://www.brainyquote.com",
        },
    }

    selected_template = st.selectbox(
        "Choose a template:",
        list(template_options.keys()),
        help="Select a template to quickly fill in the text fields",
    )

    # Text API fields
    st.markdown("### 📝 Text Fields")

    col_title, col_message = st.columns(2)

    # Initialize session state for form fields if not exists
    if "text_title" not in st.session_state:
        st.session_state.text_title = ""
    if "text_message" not in st.session_state:
        st.session_state.text_message = ""
    if "text_signature" not in st.session_state:
        st.session_state.text_signature = ""
    if "text_link" not in st.session_state:
        st.session_state.text_link = ""

    with col_title:
        title = st.text_input(
            "Title",
            value=st.session_state.text_title,
            placeholder="Optional title...",
            help="Text title displayed on screen",
            key="title_input",
        )
        st.session_state.text_title = title

    with col_message:
        message = st.text_area(
            "Message",
            value=st.session_state.text_message,
            placeholder="Main text content...",
            height=100,
            help="Main text content displayed on screen",
            key="message_input",
        )
        st.session_state.text_message = message

    # Additional fields
    col_sig, col_link = st.columns(2)

    with col_sig:
        signature = st.text_input(
            "Signature",
            value=st.session_state.text_signature,
            placeholder="Optional signature...",
            help="Text signature displayed on screen",
            key="signature_input",
        )
        st.session_state.text_signature = signature

    with col_link:
        link = st.text_input(
            "Link (NFC Touch)",
            value=st.session_state.text_link,
            placeholder="https://example.com or scheme://...",
            help="URL or scheme for NFC touch interaction",
            key="link_input",
        )
        st.session_state.text_link = link

    # Apply template button
    if selected_template != "Custom":
        if st.button(f"📝 Apply '{selected_template}' Template", type="secondary"):
            template_data = template_options[selected_template]
            st.session_state.text_title = template_data["title"]
            st.session_state.text_message = template_data["message"]
            st.session_state.text_signature = template_data["signature"]
            st.session_state.text_link = template_data["link"]
            st.success(f"✅ Applied '{selected_template}' template!")
            st.rerun()

    # Icon upload
    st.markdown("### 🎨 Icon (Optional)")
    icon_file = st.file_uploader(
        "Upload icon image (40×40px recommended)",
        type=["png", "jpg", "jpeg", "gif", "bmp", "webp"],
        help="Icon displayed in bottom-left corner (will be resized to 40×40px PNG)",
    )

    # Process icon using our image_to_base64 function
    icon_base64 = ""
    if icon_file:
        with st.spinner("Processing icon..."):
            # Use image_to_base64 with icon dimensions and smaller size limit
            icon_base64 = image_to_base64(
                image_file=icon_file,
                target_width=40,
                target_height=40,
                max_size_kb=10,  # Smaller limit for icons
            )

        if icon_base64:
            st.success("✅ Icon processed and ready")
        else:
            st.error("❌ Failed to process icon")

    # Combine content for preview
    text_content = ""
    if title:
        text_content += title + "\n\n"
    if message:
        text_content += message
    if signature:
        text_content += "\n\n" + signature

    # Show character count
    if text_content.strip():
        char_count = len(text_content)
        line_count = text_content.count("\n") + 1
        st.info(f"📊 {char_count} characters, {line_count} lines")

        # Preview
        st.markdown("**Preview:**")
        st.code(text_content.strip(), language=None)

    # API options
    st.header("⚙️ API Options")

    refresh_now = st.checkbox(
        "Refresh immediately",
        value=True,
        help="Whether to refresh the display immediately after sending",
    )

    # Send button
    # Check if at least one text field is filled
    has_content = bool(
        title.strip() or message.strip() or signature.strip() or icon_base64
    )

    if st.button(
        "🚀 Send to Quote/0",
        type="primary",
        disabled=not (api_key and device_id and has_content),
    ):
        if not api_key or not device_id:
            st.error("❌ Please configure your API credentials in the sidebar first!")
        elif not has_content:
            st.error(
                "❌ Please enter at least one text field (title, message, signature) or upload an icon!"
            )
        else:
            with st.spinner("Sending text to Quote/0..."):
                # Call API with individual fields
                response = call_text_api(
                    api_key=api_key,
                    device_id=device_id,
                    refresh_now=refresh_now,
                    title=title if title.strip() else None,
                    message=message if message.strip() else None,
                    signature=signature if signature.strip() else None,
                    icon=icon_base64 if icon_base64 else None,
                    link=link if link.strip() else None,
                )

                # Show response
                show_api_response(response)

with col2:
    st.header("📱 Display Preview")

    if has_content:
        st.markdown("**How it might look on Quote/0:**")

        # Create a styled preview
        preview_style = """
        <div style="
            background-color: #f0f0f0;
            border: 2px solid #333;
            border-radius: 5px;
            padding: 10px;
            margin: 10px 0;
            font-family: monospace;
            font-size: 12px;
            line-height: 1.4;
            color: #000;
            min-height: 100px;
            max-width: 296px;
            word-wrap: break-word;
        ">
        {text}
        </div>
        """.format(
            text=text_content.replace("\n", "<br>")
        )

        st.markdown(preview_style, unsafe_allow_html=True)

        # Show icon preview if uploaded
        if icon_base64:
            st.markdown("**Icon Preview:**")
            st.image(f"data:image/png;base64,{icon_base64}", width=40)

        # Tips for optimization
        if len(text_content) > 200:
            st.warning("⚠️ Long text may not display well on the small screen")

        if text_content.count("\n") > 10:
            st.warning("⚠️ Too many lines may not fit on the display")

    else:
        st.info("👆 Enter text fields to see preview")


# Footer info
st.markdown("---")
st.markdown(
    "📚 **Documentation:** [Text API Docs](https://dot.mindreset.tech/docs/server/template/api/text_api)"
)

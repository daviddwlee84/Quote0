"""
Text API Page for Quote/0 API Playground
"""

import streamlit as st
import sys
import os

# Add parent directory to path to import shared components
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared_components import setup_api_credentials, call_text_api, show_api_response

st.set_page_config(
    page_title="Text API - Quote/0",
    page_icon="📝",
    layout="wide"
)

st.title("📝 Text API")
st.markdown("Send text content to your Quote/0 device")

# Setup API credentials in sidebar
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
    
    # Text input options
    input_mode = st.radio(
        "Input mode:",
        ["Single line", "Multi-line", "Template"]
    )
    
    text_content = ""
    
    if input_mode == "Single line":
        text_content = st.text_input(
            "Enter text to display:",
            placeholder="Your text here...",
            help="Single line of text to display on Quote/0"
        )
    
    elif input_mode == "Multi-line":
        text_content = st.text_area(
            "Enter text to display:",
            placeholder="Your multi-line text here...\nYou can use multiple lines\nfor better formatting",
            height=150,
            help="Multi-line text with line breaks"
        )
    
    elif input_mode == "Template":
        template_type = st.selectbox(
            "Choose template:",
            ["Custom", "Quote", "Status Update", "Weather", "Reminder"]
        )
        
        if template_type == "Quote":
            quote_text = st.text_input("Quote:", placeholder="Enter the quote...")
            quote_author = st.text_input("Author:", placeholder="- Author name")
            if quote_text:
                text_content = f'"{quote_text}"\n\n{quote_author if quote_author else ""}'
                
        elif template_type == "Status Update":
            status = st.text_input("Status:", placeholder="What's happening?")
            timestamp = st.checkbox("Include timestamp", value=True)
            if status:
                text_content = status
                if timestamp:
                    from datetime import datetime
                    current_time = datetime.now().strftime("%m/%d %H:%M")
                    text_content += f"\n\n{current_time}"
                    
        elif template_type == "Weather":
            location = st.text_input("Location:", placeholder="City, Country")
            temp = st.text_input("Temperature:", placeholder="e.g., 22°C")
            condition = st.text_input("Condition:", placeholder="e.g., Sunny")
            if location and temp:
                text_content = f"{location}\n{temp}"
                if condition:
                    text_content += f"\n{condition}"
                    
        elif template_type == "Reminder":
            reminder_text = st.text_input("Reminder:", placeholder="Don't forget to...")
            time_info = st.text_input("Time (optional):", placeholder="e.g., 3:00 PM")
            if reminder_text:
                text_content = f"⏰ REMINDER\n\n{reminder_text}"
                if time_info:
                    text_content += f"\n\n{time_info}"
                    
        else:  # Custom
            text_content = st.text_area(
                "Custom template:",
                placeholder="Create your own text format...",
                height=150
            )
    
    # Show character count
    if text_content:
        char_count = len(text_content)
        line_count = text_content.count('\n') + 1
        st.info(f"📊 {char_count} characters, {line_count} lines")
        
        # Preview
        st.markdown("**Preview:**")
        st.code(text_content, language=None)

    # API options
    st.header("⚙️ API Options")
    
    refresh_now = st.checkbox(
        "Refresh immediately",
        value=True,
        help="Whether to refresh the display immediately after sending"
    )
    
    # Send button
    if st.button("🚀 Send to Quote/0", type="primary", disabled=not (api_key and device_id and text_content)):
        if not api_key or not device_id:
            st.error("❌ Please configure your API credentials in the sidebar first!")
        elif not text_content:
            st.error("❌ Please enter some text content!")
        else:
            with st.spinner("Sending text to Quote/0..."):
                # Call API
                response = call_text_api(
                    api_key=api_key,
                    device_id=device_id,
                    text_content=text_content,
                    refresh_now=refresh_now
                )
                
                # Show response
                show_api_response(response)

with col2:
    st.header("📱 Display Preview")
    
    if text_content:
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
        """.format(text=text_content.replace('\n', '<br>'))
        
        st.markdown(preview_style, unsafe_allow_html=True)
        
        # Tips for optimization
        if len(text_content) > 200:
            st.warning("⚠️ Long text may not display well on the small screen")
        
        if text_content.count('\n') > 10:
            st.warning("⚠️ Too many lines may not fit on the display")
            
    else:
        st.info("👆 Enter text to see preview")
        
    # Sample texts
    st.markdown("---")
    st.markdown("**💡 Sample texts:**")
    
    sample_texts = {
        "Simple Quote": '"The best time to plant a tree was 20 years ago. The second best time is now."\n\n- Chinese Proverb',
        "Status": "Currently working on:\n• Project A\n• Code review\n• Meeting at 3 PM",
        "Weather": "San Francisco\n22°C\nSunny\n\nPerfect day! ☀️",
        "Reminder": "⏰ REMINDER\n\nTeam standup\n9:00 AM\n\nDon't be late!"
    }
    
    for name, sample in sample_texts.items():
        if st.button(f"Load: {name}", key=f"sample_{name}"):
            # This would need to be handled with session state
            st.info(f"Sample text for {name}:\n\n{sample}")

# Footer info
st.markdown("---")
st.markdown("📚 **Documentation:** [Text API Docs](https://dot.mindreset.tech/docs/server/template/api/text_api)")

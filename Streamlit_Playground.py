"""
Quote/0 API Playground
A Streamlit application for testing Quote/0 device APIs
"""

import streamlit as st

# Page configuration
st.set_page_config(
    page_title="Quote/0 API Playground",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Main page content
st.title("🎯 Quote/0 API Playground")

st.markdown("""
Welcome to the Quote/0 API Playground! This application allows you to interact with your Quote/0 device APIs.

## Available APIs

### 📷 Image API
Upload and display images on your Quote/0 device (296px × 152px)

### 📝 Text API  
Send text content to your Quote/0 device

## Getting Started

1. Configure your API credentials in the sidebar
2. Choose an API from the pages in the sidebar
3. Test your Quote/0 device!

## Resources

- [Quote/0 Documentation](https://dot.mindreset.tech/docs/quote_0)
- [API Documentation](https://dot.mindreset.tech/docs/server/template/api)
- [Image API Docs](https://dot.mindreset.tech/docs/server/template/api/image_api)
- [Text API Docs](https://dot.mindreset.tech/docs/server/template/api/text_api)
""")

# Add sidebar info
st.sidebar.markdown("---")
st.sidebar.markdown("**About Quote/0**")
st.sidebar.markdown("Quote/0 is an E-ink display device by SSPAI that can show custom content via API.")
st.sidebar.markdown("[Learn more](https://sspai.com/create/quote0)")

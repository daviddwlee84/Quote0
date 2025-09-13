
## Quote/0 API Playground

This project includes a Streamlit-based API playground for testing Quote/0 device APIs.

### Features

- **Image API Testing**: Upload images or use preset test images
- **Text API Testing**: Send text content with templates
- **Automatic Image Optimization**: Images are automatically resized and optimized for Quote/0 (max 50KB)
- **Preset Test Images**: Includes 1×1 black pixel, full-size black, and checkerboard patterns
- **Environment Configuration**: Uses `.env` file for API credentials

### Setup

1. Install dependencies:
   ```bash
   uv install
   ```

2. Configure API credentials:
   ```bash
   cp env.example .env
   # Edit .env with your DOT_API_KEY and DOT_DEVICE_ID
   ```

3. Run the application:
   ```bash
   uv run streamlit run Streamlit_Playground.py
   ```

### Image Optimization

The application automatically optimizes uploaded images:
- Resizes to fit Quote/0 dimensions (296×152) while maintaining aspect ratio
- Converts to PNG format (required by API)
- Optimizes file size to under 50KB
- Handles transparency by adding white background

### Preset Images

Three preset test images are available:
- **1×1 Black Pixel**: Minimal test image
- **All Black (296×152)**: Full-size black image
- **Checkerboard Gray**: Gray checkerboard pattern

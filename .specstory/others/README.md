
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

## Image API Features

✅ **Complete API parameter support:**
- Border settings (0=white, 1=black)
- NFC link support for touch interaction
- Dithering type (DIFFUSION, ORDERED, NONE)
- Dithering algorithm selection (9 different algorithms)
- Automatic image optimization (PNG, max 50KB)
- Preset test images (1×1 black, full black, checkerboard)

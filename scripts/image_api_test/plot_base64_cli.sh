#!/bin/bash

# Check if image argument is provided via command line or pipe
if [ $# -eq 0 ]; then
    # Try to read from stdin (pipe)
    if [ -t 0 ]; then
        echo "Usage: $0 <base64_image_string>"
        echo "Example: $0 'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQd1PeAAAADElEQVR42mNgYGAAAAAEAAHI6uv5AAAAAElFTkSuQmCC'"
        echo "Or pipe data: echo 'base64_string' | $0"
        echo ""
        echo "This script uses the quote0 CLI tool to send base64 images to your Quote/0 device."
        echo "Make sure to set DOT_API_KEY and DOT_DEVICE_ID environment variables."
        exit 1
    else
        # Read from stdin
        IMAGE_DATA=$(cat)
    fi
else
    IMAGE_DATA="$1"
fi

echo "📄 Sending base64 image to Quote/0 device using CLI..."
echo "📏 Base64 data length: ${#IMAGE_DATA} characters"

# Use the quote0 CLI tool with the new --base64 option
quote0 image --base64 "$IMAGE_DATA" --border BLACK

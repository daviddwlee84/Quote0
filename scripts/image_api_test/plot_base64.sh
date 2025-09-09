#!/bin/bash

# Check if image argument is provided via command line or pipe
if [ $# -eq 0 ]; then
    # Try to read from stdin (pipe)
    if [ -t 0 ]; then
        echo "Usage: $0 <base64_image_string>"
        echo "Example: $0 'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQd1PeAAAADElEQVR42mNgYGAAAAAEAAHI6uv5AAAAAElFTkSuQmCC'"
        echo "Or pipe data: echo 'base64_string' | $0"
        exit 1
    else
        # Read from stdin
        IMAGE_DATA=$(cat)
    fi
else
    IMAGE_DATA="$1"
fi

curl -X POST \
  https://dot.mindreset.tech/api/open/image \
  -H "Authorization: Bearer $DOT_API_KEY" \
  -H 'Content-Type: application/json' \
  --data-raw "{
    \"refreshNow\": true,
    \"deviceId\": \"$DOT_DEVICE_ID\",
    \"image\": \"$IMAGE_DATA\",
    \"border\": 0
  }"

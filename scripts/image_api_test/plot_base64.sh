#!/bin/bash

# Check if image argument is provided
if [ $# -eq 0 ]; then
    echo "Usage: $0 <base64_image_string>"
    echo "Example: $0 'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQd1PeAAAADElEQVR42mNgYGAAAAAEAAHI6uv5AAAAAElFTkSuQmCC'"
    exit 1
fi

IMAGE_DATA="$1"

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

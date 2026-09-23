#!/bin/bash
curl -X POST \
  "https://dot.mindreset.tech/api/authV2/open/device/${DOT_DEVICE_ID}/image" \
  -H "Authorization: Bearer $DOT_API_KEY" \
  -H 'Content-Type: application/json' \
  --data-raw "{
    \"refreshNow\": true,
    \"image\": \"iVBORw0KGgoAAAANSUhEUgAAASgAAACYAQAAAAB/wUl1AAAAHElEQVR4nO3BMQEAAADCoPVPbQo/oAAAAAAA4G8WkAABUhYjKAAAAABJRU5ErkJggg==\",
    \"border\": 0
  }"

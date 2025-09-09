#!/bin/bash
curl -X POST \
  https://dot.mindreset.tech/api/open/image \
  -H "Authorization: Bearer $DOT_API_KEY" \
  -H 'Content-Type: application/json' \
  --data-raw "{
    \"refreshNow\": true,
    \"deviceId\": \"$DOT_DEVICE_ID\",
    \"image\": \"iVBORw0KGgoAAAANSUhEUgAAASgAAACYAQAAAAB/wUl1AAAAHElEQVR4nO3BMQEAAADCoPVPbQo/oAAAAAAA4G8WkAABUhYjKAAAAABJRU5ErkJggg==\",
    \"border\": 0
  }"

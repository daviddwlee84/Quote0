#!/bin/bash
curl -X POST \
  "https://dot.mindreset.tech/api/authV2/open/device/${DOT_DEVICE_ID}/image" \
  -H "Authorization: Bearer $DOT_API_KEY" \
  -H 'Content-Type: application/json' \
  --data-raw "{
    \"refreshNow\": true,
    \"image\": \"iVBORw0KGgoAAAANSUhEUgAAASgAAACYAQAAAAB/wUl1AAAAN0lEQVR4nO3MsQ0AMAgEsSBlRZZkSlb4Hl99cs0Lqk6uH10sFovFYrFYLBaLxWKxWCwWi8W6aC1FhjRHozCNPQAAAABJRU5ErkJggg==\",
    \"border\": 0,
    \"link\": \"https://www.google.com\"
  }"

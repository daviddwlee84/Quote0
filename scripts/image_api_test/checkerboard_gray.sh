curl -X POST \
  https://dot.mindreset.tech/api/open/image \
  -H 'Authorization: Bearer $DOT_API_KEY' \
  -H 'Content-Type: application/json' \
  --data-raw '{
    "refreshNow": true,
    "deviceId": "$DOT_DEVICE_ID",
    "image": "iVBORw0KGgoAAAANSUhEUgAAASgAAACYAQAAAAB/wUl1AAAAN0lEQVR4nO3MsQ0AMAgEsSBlRZZkSlb4Hl99cs0Lqk6uH10sFovFYrFYLBaLxWKxWCwWi8W6aC1FhjRHozCNPQAAAABJRU5ErkJggg==",
    "border": 0
  }'

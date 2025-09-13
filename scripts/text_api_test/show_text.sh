#!/bin/bash

# Default values
REFRESH_NOW="true"
DEVICE_ID="${DOT_DEVICE_ID:-}"
TITLE=""
MESSAGE=""
SIGNATURE=""
ICON=""
LINK=""

# Function to show usage
show_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Send text content to Dot device via Text API"
    echo ""
    echo "OPTIONS:"
    echo "  -t, --title TITLE          Set the title"
    echo "  -m, --message MESSAGE      Set the message content"
    echo "  -s, --signature SIGNATURE  Set the signature"
    echo "  -i, --icon ICON            Set base64 encoded PNG icon"
    echo "  -l, --link LINK            Set the touch link (URL or scheme)"
    echo "  -d, --device DEVICE_ID     Set device ID (overrides DOT_DEVICE_ID)"
    echo "  -r, --refresh BOOLEAN      Set refreshNow flag (default: true)"
    echo "  -h, --help                 Show this help message"
    echo ""
    echo "Environment Variables:"
    echo "  DOT_API_KEY    API key for authentication"
    echo "  DOT_DEVICE_ID  Default device ID"
    echo ""
    echo "Examples:"
    echo "  $0 -t 'Hello' -m 'World'"
    echo "  $0 --title 'Daily Health' --message 'Steps: 5000' --signature 'Today'"
    echo "  $0 -m 'Simple message' -d 'ABCD1234ABCD'"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -t|--title)
            TITLE="$2"
            shift 2
            ;;
        -m|--message)
            MESSAGE="$2"
            shift 2
            ;;
        -s|--signature)
            SIGNATURE="$2"
            shift 2
            ;;
        -i|--icon)
            ICON="$2"
            shift 2
            ;;
        -l|--link)
            LINK="$2"
            shift 2
            ;;
        -d|--device)
            DEVICE_ID="$2"
            shift 2
            ;;
        -r|--refresh)
            REFRESH_NOW="$2"
            shift 2
            ;;
        -h|--help)
            show_usage
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            show_usage
            exit 1
            ;;
    esac
done

# Validate required parameters
if [ -z "$DOT_API_KEY" ]; then
    echo "Error: DOT_API_KEY environment variable is not set"
    exit 1
fi

if [ -z "$DEVICE_ID" ]; then
    echo "Error: Device ID not provided. Use -d option or set DOT_DEVICE_ID environment variable"
    exit 1
fi

# Build JSON payload
JSON_DATA="{"
JSON_DATA="$JSON_DATA\"refreshNow\": $REFRESH_NOW,"
JSON_DATA="$JSON_DATA\"deviceId\": \"$DEVICE_ID\""

if [ -n "$TITLE" ]; then
    JSON_DATA="$JSON_DATA,\"title\": \"$TITLE\""
fi

if [ -n "$MESSAGE" ]; then
    JSON_DATA="$JSON_DATA,\"message\": \"$MESSAGE\""
fi

if [ -n "$SIGNATURE" ]; then
    JSON_DATA="$JSON_DATA,\"signature\": \"$SIGNATURE\""
fi

if [ -n "$ICON" ]; then
    JSON_DATA="$JSON_DATA,\"icon\": \"$ICON\""
fi

if [ -n "$LINK" ]; then
    JSON_DATA="$JSON_DATA,\"link\": \"$LINK\""
fi

JSON_DATA="$JSON_DATA}"

# Make the API call
curl -X POST \
  https://dot.mindreset.tech/api/open/text \
  -H "Authorization: Bearer $DOT_API_KEY" \
  -H 'Content-Type: application/json' \
  --data "$JSON_DATA"

#!/usr/bin/env python3
"""
Example usage of the Quote/0 Python API
"""

from quote0 import Quote0, get_preset_images
from dotenv import load_dotenv, find_dotenv
import os
import time

load_dotenv(find_dotenv())


def main():
    # Initialize the Quote/0 client
    api_key = os.getenv("DOT_API_KEY")
    device_id = os.getenv("DOT_DEVICE_ID")

    # Create Quote/0 client instance
    quote0 = Quote0(api_key, device_id)

    # Example 1: Send text to the device
    print("Sending text...")
    text_response = quote0.send_text(
        title="Hello World!",
        message="This is sent from the Python API",
        signature="Quote/0 Python Client",
    )

    if text_response.success:
        print(f"✅ Text sent successfully: {text_response.message}")
    else:
        print(f"❌ Failed to send text: {text_response.message}")

    time.sleep(3)

    # Example 2: Send a preset image
    print("\nSending image...")
    preset_images = get_preset_images()
    black_image = preset_images["all_black"]

    image_response = quote0.send_image(
        image_base64=black_image.base64,
        border=0,
    )

    if image_response.success:
        print(f"✅ Image sent successfully: {image_response.message}")
    else:
        print(f"❌ Failed to send image: {image_response.message}")

    time.sleep(3)

    # Example 3: Send text with icon and link
    print("\nSending text with NFC link...")
    response_with_link = quote0.send_text(
        title="Tap to visit",
        message="Visit our website",
        link="https://example.com",
    )

    if response_with_link.success:
        print(f"✅ Text with link sent: {response_with_link.message}")
    else:
        print(f"❌ Failed to send text with link: {response_with_link.message}")


if __name__ == "__main__":
    main()

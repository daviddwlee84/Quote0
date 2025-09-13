"""
Quote/0 API Client
"""

import requests
from typing import Optional
from .models import ImageApiRequest, TextApiRequest, ApiResponse


class Quote0:
    """Quote/0 API Client"""

    def __init__(self, api_key: str, device_id: str):
        """
        Initialize Quote/0 client

        Args:
            api_key: DOT API key from the mobile app
            device_id: DOT device ID from the mobile app
        """
        self.api_key = api_key
        self.device_id = device_id
        self.base_url = "https://dot.mindreset.tech/api/open"

    def _get_headers(self) -> dict:
        """Get request headers"""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def send_image(
        self,
        image_base64: str,
        border: int = 0,
        refresh_now: bool = True,
        link: Optional[str] = None,
        dither_type: Optional[str] = None,
        dither_kernel: Optional[str] = None,
    ) -> ApiResponse:
        """
        Send image to Quote/0 device

        Args:
            image_base64: Base64 encoded image string
            border: Border size (default: 0)
            refresh_now: Whether to refresh display immediately (default: True)
            link: Optional link for NFC touch (default: None)
            dither_type: Optional dithering type (DIFFUSION, ORDERED, NONE) (default: None)
            dither_kernel: Optional dithering algorithm (only used when dither_type is DIFFUSION) (default: None)

        Returns:
            ApiResponse object with success status and details
        """
        url = f"{self.base_url}/image"

        # Create request payload using Pydantic model
        request_data = ImageApiRequest(
            refreshNow=refresh_now,
            deviceId=self.device_id,
            image=image_base64,
            border=border,
            link=link,
            ditherType=dither_type,
            ditherKernel=dither_kernel,
        )

        try:
            response = requests.post(
                url,
                json=request_data.model_dump(exclude_none=True),
                headers=self._get_headers(),
            )
            response.raise_for_status()

            return ApiResponse(
                success=True,
                status_code=response.status_code,
                response=response.json() if response.content else {},
                message="Image sent successfully!",
            )

        except requests.exceptions.RequestException as e:
            return ApiResponse(
                success=False,
                error=str(e),
                message=f"API call failed: {str(e)} ({response.text})",
            )

    def send_text(
        self,
        refresh_now: bool = True,
        title: Optional[str] = None,
        message: Optional[str] = None,
        signature: Optional[str] = None,
        icon: Optional[str] = None,
        link: Optional[str] = None,
    ) -> ApiResponse:
        """
        Send text to Quote/0 device

        Args:
            refresh_now: Whether to refresh display immediately (default: True)
            title: Text title to display (optional)
            message: Text content to display (optional)
            signature: Text signature to display (optional)
            icon: Base64 encoded PNG icon data (40px*40px) (optional)
            link: HTTP/HTTPS link or Scheme URL for NFC touch (optional)

        Returns:
            ApiResponse object with success status and details
        """
        url = f"{self.base_url}/text"

        # Create request payload using Pydantic model
        request_data = TextApiRequest(
            refreshNow=refresh_now,
            deviceId=self.device_id,
            title=title,
            message=message,
            signature=signature,
            icon=icon,
            link=link,
        )

        try:
            response = requests.post(
                url,
                json=request_data.model_dump(exclude_none=True),
                headers=self._get_headers(),
            )
            response.raise_for_status()

            return ApiResponse(
                success=True,
                status_code=response.status_code,
                response=response.json() if response.content else {},
                message="Text sent successfully!",
            )

        except requests.exceptions.RequestException as e:
            return ApiResponse(
                success=False,
                error=str(e),
                message=f"API call failed: {str(e)} ({response.text})",
            )

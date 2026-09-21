"""
Quote/0 API Client
"""

import requests
from typing import Optional
from .models import ImageApiRequest, TextApiRequest, ApiResponse, BorderColor


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

    def _post(self, endpoint: str, payload: dict, success_message: str) -> ApiResponse:
        """Send a bounded request and handle transport and API-level failures."""
        response = None
        try:
            response = requests.post(
                f"{self.base_url}/{endpoint}",
                json=payload,
                headers=self._get_headers(),
                timeout=30,
            )
            response.raise_for_status()
        except requests.exceptions.RequestException as error:
            return ApiResponse(
                success=False,
                status_code=response.status_code if response is not None else None,
                error=str(error),
                message=f"API call failed: {error}",
            )

        try:
            body = response.json() if response.content else {}
        except ValueError:
            return ApiResponse(
                success=False,
                status_code=response.status_code,
                error="Invalid JSON response",
                message="API call failed: invalid JSON response",
            )

        if not isinstance(body, dict):
            return ApiResponse(
                success=False,
                status_code=response.status_code,
                error="Expected a JSON object response",
                message="API call failed: expected a JSON object response",
            )

        if "code" in body and body["code"] != 200:
            error = f"API returned code {body['code']}"
            if body.get("message"):
                error += f": {body['message']}"
            return ApiResponse(
                success=False,
                status_code=response.status_code,
                response=body,
                error=error,
                message=f"API call failed: {error}",
            )

        return ApiResponse(
            success=True,
            status_code=response.status_code,
            response=body,
            message=success_message,
        )

    def send_image(
        self,
        image_base64: str,
        border: BorderColor = BorderColor.WHITE,
        refresh_now: bool = True,
        link: Optional[str] = None,
        dither_type: Optional[str] = None,
        dither_kernel: Optional[str] = None,
    ) -> ApiResponse:
        """
        Send image to Quote/0 device

        Args:
            image_base64: Base64 encoded image string
            border: Border color (default: WHITE=0, BLACK=1)
            refresh_now: Whether to refresh display immediately (default: True)
            link: Optional link for NFC touch (default: None)
            dither_type: Optional dithering type (DIFFUSION, ORDERED, NONE) (default: None)
            dither_kernel: Optional dithering algorithm (only used when dither_type is DIFFUSION) (default: None)

        Returns:
            ApiResponse object with success status and details
        """
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

        return self._post(
            "image",
            request_data.model_dump(exclude_none=True),
            "Image sent successfully!",
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

        return self._post(
            "text",
            request_data.model_dump(exclude_none=True),
            "Text sent successfully!",
        )

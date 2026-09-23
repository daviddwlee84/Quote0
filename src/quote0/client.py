"""
Quote/0 API Client
"""

import requests
from typing import Optional
from urllib.parse import quote
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
        self.base_url = "https://dot.mindreset.tech/api/authV2/open/device"

    def _get_headers(self) -> dict:
        """Get request headers"""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def _post(self, endpoint: str, payload: dict, success_message: str) -> ApiResponse:
        """Send a bounded V2 request and preserve server error details."""
        try:
            response = requests.post(
                f"{self.base_url}/{quote(self.device_id, safe='')}/{endpoint}",
                json=payload,
                headers=self._get_headers(),
                timeout=30,
            )
        except requests.exceptions.RequestException as error:
            return ApiResponse(
                success=False,
                status_code=(
                    error.response.status_code if error.response is not None else None
                ),
                error=str(error),
                message=f"API call failed: {error}",
            )

        parse_error = None
        try:
            body = response.json() if response.content else {}
        except ValueError:
            body = None
            parse_error = "Invalid JSON response"

        server_message = body.get("message") if isinstance(body, dict) else None
        if not isinstance(server_message, str) or not server_message.strip():
            server_message = None

        if not 200 <= response.status_code < 300:
            detail = server_message
            if detail is None:
                raw_text = response.text.strip()
                detail = raw_text[:500] + ("..." if len(raw_text) > 500 else "")
            error = f"HTTP {response.status_code}"
            if detail:
                error += f": {detail}"
            return ApiResponse(
                success=False,
                status_code=response.status_code,
                response=body if isinstance(body, dict) else None,
                error=error,
                message=f"API call failed: {error}",
            )

        if not isinstance(body, dict):
            error = parse_error or "Expected a JSON object response"
            return ApiResponse(
                success=False,
                status_code=response.status_code,
                error=error,
                message=f"API call failed: {error}",
            )

        return ApiResponse(
            success=True,
            status_code=response.status_code,
            response=body,
            message=server_message or success_message,
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
            request_data.model_dump(exclude_none=True, exclude={"deviceId"}),
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
            request_data.model_dump(exclude_none=True, exclude={"deviceId"}),
            "Text sent successfully!",
        )

"""Account and device clients for the Dot authV2 OpenAPI."""

from typing import Any, List, Optional, Union
from urllib.parse import quote

import requests
from pydantic import TypeAdapter, ValidationError

from .models import (
    ApiResponse,
    BorderColor,
    CanvasApiRequest,
    DeviceInfo,
    DeviceSettings,
    DeviceSettingsRequest,
    DeviceStatus,
    DeviceTask,
    ImageApiRequest,
    TextApiRequest,
    TextStyles,
    TimezoneInfo,
)

# Distinguish omission (keep current alias) from explicit None (clear it).
UNSET = object()


class DotClient:
    """Account-level discovery and shared bounded HTTP transport."""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://dot.mindreset.tech/api/authV2/open"

    def _get_headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def _request(
        self,
        method: str,
        url: str,
        *,
        payload=None,
        response_type=dict,
        success_message="Request completed.",
    ) -> ApiResponse:
        try:
            if method == "GET":
                response = requests.get(url, headers=self._get_headers(), timeout=30)
            else:
                response = requests.post(
                    url, json=payload, headers=self._get_headers(), timeout=30
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
            error = f"HTTP {response.status_code}" + (f": {detail}" if detail else "")
            return ApiResponse(
                success=False,
                status_code=response.status_code,
                response=body if isinstance(body, dict) else None,
                error=error,
                message=f"API call failed: {error}",
            )
        try:
            if parse_error:
                raise ValueError(parse_error)
            if response_type is dict and not isinstance(body, dict):
                raise ValueError("Expected a JSON object response")
            parsed = TypeAdapter(response_type).validate_python(body)
        except (ValueError, ValidationError) as error:
            detail = (
                str(error)
                if not isinstance(error, ValidationError)
                else "Unexpected API response schema"
            )
            return ApiResponse(
                success=False,
                status_code=response.status_code,
                error=detail,
                message=f"API call failed: {detail}",
            )
        return ApiResponse[response_type](
            success=True,
            status_code=response.status_code,
            response=parsed,
            message=server_message or success_message,
        )

    def list_devices(self) -> ApiResponse[List[DeviceInfo]]:
        return self._request(
            "GET", f"{self.base_url}/devices", response_type=List[DeviceInfo]
        )

    def list_timezones(self) -> ApiResponse[List[TimezoneInfo]]:
        return self._request(
            "GET", f"{self.base_url}/timezones", response_type=List[TimezoneInfo]
        )


class Quote0(DotClient):
    """Device-bound client; existing text/image Python calls remain supported."""

    def __init__(self, api_key: str, device_id: str):
        super().__init__(api_key)
        self.device_id = device_id

    def _device_url(self, endpoint: str) -> str:
        return f"{self.base_url}/device/{quote(self.device_id, safe='')}/{endpoint}"

    def _post(self, endpoint: str, payload: dict, success_message: str) -> ApiResponse:
        return self._request(
            "POST",
            self._device_url(endpoint),
            payload=payload,
            success_message=success_message,
        )

    def get_status(self) -> ApiResponse[DeviceStatus]:
        return self._request(
            "GET", self._device_url("status"), response_type=DeviceStatus
        )

    def list_tasks(self, task_type: str = "loop") -> ApiResponse[List[DeviceTask]]:
        if task_type not in ("loop", "fixed"):
            raise ValueError("task_type must be loop or fixed")
        return self._request(
            "GET", self._device_url(f"{task_type}/list"), response_type=List[DeviceTask]
        )

    def next_content(self) -> ApiResponse:
        return self._post("next", {}, "Content switched.")

    def get_settings(self) -> ApiResponse[DeviceSettings]:
        return self._request(
            "GET", self._device_url("settings"), response_type=DeviceSettings
        )

    def update_settings(
        self, settings: Union[dict, DeviceSettingsRequest]
    ) -> ApiResponse:
        request = DeviceSettingsRequest.model_validate(settings)
        if "timezone" in request.model_fields_set:
            zones = self.list_timezones()
            if not zones.success:
                return zones
            if request.timezone not in {zone.key for zone in zones.response}:
                raise ValueError(
                    "Unsupported timezone; use timezones list for accepted keys."
                )
        return self._post(
            "settings",
            request.model_dump(mode="json", exclude_unset=True),
            "Device settings updated.",
        )

    @staticmethod
    def _content_payload(request, task_key, task_alias):
        payload = request.model_dump(
            mode="json", exclude_none=True, exclude={"deviceId"}
        )
        if task_key is not None:
            payload["taskKey"] = task_key
        if task_alias is not UNSET:
            # Validation before injection also supports explicit null for clearing.
            alias_request = type(request).model_validate(
                {**payload, "taskAlias": task_alias}
            )
            payload["taskAlias"] = alias_request.taskAlias
        return payload

    def send_image(
        self,
        image_base64: Optional[str] = None,
        border: BorderColor = BorderColor.WHITE,
        refresh_now: bool = True,
        link: Optional[str] = None,
        dither_type: Optional[str] = None,
        dither_kernel: Optional[str] = None,
        *,
        image: Optional[str] = None,
        task_key: Optional[str] = None,
        task_alias: Any = UNSET,
    ) -> ApiResponse:
        """Send PNG Base64/data URI or public URL. image_base64 remains an alias."""
        if (image_base64 is None) == (image is None):
            raise ValueError("Supply exactly one of image or image_base64.")
        request = ImageApiRequest(
            image=image if image is not None else image_base64,
            refreshNow=refresh_now,
            border=border,
            link=link,
            ditherType=dither_type,
            ditherKernel=dither_kernel,
            taskKey=task_key,
        )
        return self._post(
            "image",
            self._content_payload(request, task_key, task_alias),
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
        *,
        styles: Optional[Union[dict, TextStyles]] = None,
        task_key: Optional[str] = None,
        task_alias: Any = UNSET,
    ) -> ApiResponse:
        request = TextApiRequest(
            refreshNow=refresh_now,
            title=title,
            message=message,
            signature=signature,
            icon=icon,
            link=link,
            styles=styles,
            taskKey=task_key,
        )
        return self._post(
            "text",
            self._content_payload(request, task_key, task_alias),
            "Text sent successfully!",
        )

    def send_canvas(
        self,
        window_data: dict,
        *,
        data: Optional[dict] = None,
        layout_full: Optional[dict] = None,
        link: Optional[str] = None,
        border: BorderColor = BorderColor.WHITE,
        refresh_now: bool = True,
        task_key: Optional[str] = None,
        task_alias: Any = UNSET,
    ) -> ApiResponse:
        values = dict(
            windowData=window_data,
            data=data if data is not None else {},
            refreshNow=refresh_now,
            border=border,
            taskKey=task_key,
        )
        if layout_full is not None:
            values["layoutFull"] = layout_full
        if link is not None:
            values["link"] = link
        request = CanvasApiRequest(**values)
        return self._post(
            "canvas",
            self._content_payload(request, task_key, task_alias),
            "Canvas sent successfully!",
        )

"""
Pydantic models for Quote/0 API
"""

from enum import IntEnum
from typing import Optional
from pydantic import BaseModel, Field


class BorderColor(IntEnum):
    """Border color options for Quote/0 display"""

    WHITE = 0  # 白色边框
    BLACK = 1  # 黑色边框


class ImageApiRequest(BaseModel):
    """Image API request payload"""

    refreshNow: bool = Field(
        default=True, description="Whether to refresh display immediately"
    )
    deviceId: str = Field(..., description="DOT device ID")
    image: str = Field(..., description="Base64 encoded image string")
    border: BorderColor = Field(
        default=BorderColor.WHITE, description="Border color (0=white, 1=black)"
    )
    link: Optional[str] = Field(default=None, description="Optional link for NFC touch")
    ditherType: Optional[str] = Field(
        default=None, description="Optional dithering type (DIFFUSION, ORDERED, NONE)"
    )
    ditherKernel: Optional[str] = Field(
        default=None,
        description="Optional dithering algorithm (only used when dither_type is DIFFUSION)",
    )


class TextApiRequest(BaseModel):
    """Text API request payload"""

    refreshNow: bool = Field(
        default=True, description="Whether to refresh display immediately"
    )
    deviceId: str = Field(..., description="DOT device ID")
    title: Optional[str] = Field(default=None, description="Text title to display")
    message: Optional[str] = Field(default=None, description="Text content to display")
    signature: Optional[str] = Field(
        default=None, description="Text signature to display"
    )
    icon: Optional[str] = Field(
        default=None, description="Base64 encoded PNG icon data (40px*40px)"
    )
    link: Optional[str] = Field(
        default=None, description="HTTP/HTTPS link or Scheme URL for NFC touch"
    )


class ApiResponse(BaseModel):
    """Standard API response structure"""

    success: bool
    status_code: Optional[int] = None
    response: Optional[dict] = None
    message: str
    error: Optional[str] = None


class PresetImage(BaseModel):
    """Preset test image data"""

    name: str
    description: str
    base64: str
    dimensions: str

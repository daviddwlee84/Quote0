"""Dot OpenAPI models. Wire field names match the official API."""

from enum import IntEnum
from typing import Any, Dict, Generic, List, Literal, Optional, TypeVar, Union
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StrictBool,
    StrictInt,
    field_validator,
    model_validator,
)

T = TypeVar("T")


class BorderColor(IntEnum):
    WHITE = 0
    BLACK = 1


class ApiResponse(BaseModel, Generic[T]):
    success: bool
    status_code: Optional[int] = None
    response: Optional[T] = None
    message: str
    error: Optional[str] = None


class ReadModel(BaseModel):
    model_config = ConfigDict(extra="allow")


class DeviceInfo(ReadModel):
    id: str = Field(min_length=1)
    alias: Optional[str] = None
    location: Optional[str] = None
    series: Optional[str] = None
    model: Optional[str] = None
    edition: Optional[float] = None


class DeviceTask(ReadModel):
    type: str
    key: Optional[str] = None
    taskAlias: Optional[Union[str, int, float]] = None
    refreshNow: Optional[bool] = None


class DeviceStatus(ReadModel):
    deviceId: str
    alias: Optional[str] = None
    location: Optional[str] = None
    status: Dict[str, Any] = Field(default_factory=dict)
    renderInfo: Dict[str, Any] = Field(default_factory=dict)


class TimezoneInfo(ReadModel):
    key: str
    name: str
    utcOffsetMinutes: float
    utcOffsetLabel: str


class WriteModel(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class ContentRequest(WriteModel):
    refreshNow: bool = True
    taskKey: Optional[str] = None
    taskAlias: Optional[Union[str, int, float]] = None

    @field_validator("taskAlias")
    @classmethod
    def alias_length(cls, value):
        if isinstance(value, str) and len(value) > 100:
            raise ValueError("taskAlias must be at most 100 characters")
        return value


FONT_FAMILIES = {
    "ChillDuanSans",
    "ChillKSans",
    "ChillOrganic",
    "ChillRoundF",
    "ChillRoundGothic",
    "Cusong16",
    "DotGothic16",
    "FusionPixel8",
    "FusionPixel10",
    "FusionPixel12",
    "Liusong24",
    "LogoSCUnboundedSans",
    "MaokenYingBiKaiShuJ0.09",
    "PlayfairDisplay",
    "Quan8",
    "Unifont16",
    "UnifontExMono16",
    "XiaoyaPixel12",
    "Zihunzhoukesong",
    "Zpix12",
}


class TextStyle(WriteModel):
    fontFamily: Optional[str] = None
    fontSize: Optional[float] = Field(default=None, ge=8, le=48)
    fontWeight: Optional[Literal[100, 200, 300, 400, 500, 600, 700, 800, 900]] = None

    @field_validator("fontFamily")
    @classmethod
    def known_font(cls, value):
        if value is not None and value not in FONT_FAMILIES:
            raise ValueError("Unsupported Text API fontFamily")
        return value


class MessageTextStyle(TextStyle):
    lineHeight: Optional[float] = Field(default=None, ge=0.8, le=3)


class TextStyles(WriteModel):
    title: Optional[TextStyle] = None
    message: Optional[MessageTextStyle] = None
    signature: Optional[TextStyle] = None


class ImageApiRequest(ContentRequest):
    # Retained for callers of the existing exported models; never sent in JSON.
    deviceId: Optional[str] = None
    image: str = Field(min_length=1)
    border: BorderColor = BorderColor.WHITE
    link: Optional[str] = None
    ditherType: Optional[Literal["DIFFUSION", "ORDERED", "NONE"]] = None
    ditherKernel: Optional[
        Literal[
            "THRESHOLD",
            "ATKINSON",
            "BURKES",
            "FLOYD_STEINBERG",
            "SIERRA2",
            "STUCKI",
            "JARVIS_JUDICE_NINKE",
            "DIFFUSION_ROW",
            "DIFFUSION_COLUMN",
            "DIFFUSION_2D",
        ]
    ] = None


class TextApiRequest(ContentRequest):
    deviceId: Optional[str] = None
    title: Optional[str] = None
    message: Optional[str] = None
    signature: Optional[str] = None
    icon: Optional[str] = None
    link: Optional[str] = None
    styles: Optional[TextStyles] = None


class CanvasApiRequest(ContentRequest):
    data: Dict[str, Any] = Field(default_factory=dict)
    windowData: Dict[str, Any]
    layoutFull: Optional[Dict[str, Any]] = None
    link: Optional[str] = None
    border: BorderColor = BorderColor.WHITE

    @model_validator(mode="after")
    def validate_canvas(self):
        from .canvas import validate_canvas

        validate_canvas(self.model_dump(mode="json", exclude_unset=True))
        return self


class SettingsInterval(WriteModel):
    powerMs: Optional[StrictInt] = Field(
        default=None, ge=60000, le=43200000, multiple_of=60000
    )
    batteryMs: Optional[StrictInt] = Field(
        default=None, ge=60000, le=43200000, multiple_of=60000
    )

    @model_validator(mode="after")
    def nonempty(self):
        if not self.model_fields_set or any(
            getattr(self, name) is None for name in self.model_fields_set
        ):
            raise ValueError(
                "interval needs at least one non-null interval in whole minutes"
            )
        return self


class SettingsSleep(WriteModel):
    enabled: StrictBool
    start: str = Field(pattern=r"^([01]\d|2[0-3]):[0-5]\d$")
    end: str = Field(pattern=r"^([01]\d|2[0-3]):[0-5]\d$")

    @model_validator(mode="after")
    def different_times(self):
        if self.start == self.end:
            raise ValueError("sleep.start and sleep.end must differ")
        return self


class DeviceSettingsRequest(WriteModel):
    alias: Optional[str] = Field(default=None, max_length=100)
    location: Optional[str] = Field(default=None, max_length=100)
    timezone: Optional[str] = Field(default=None, min_length=1)
    interval: Optional[SettingsInterval] = None
    sleep: Optional[SettingsSleep] = None

    @model_validator(mode="after")
    def partial_update(self):
        if not self.model_fields_set:
            raise ValueError("Specify at least one setting")
        for name in self.model_fields_set - {"alias", "location"}:
            if getattr(self, name) is None:
                raise ValueError(f"{name} cannot be null")
        return self


class DeviceSettings(ReadModel):
    deviceId: str
    alias: Optional[str] = None
    location: Optional[str] = None
    timezone: str
    interval: SettingsInterval
    sleep: Optional[SettingsSleep] = None


class PresetImage(BaseModel):
    name: str
    description: str
    base64: str
    dimensions: str

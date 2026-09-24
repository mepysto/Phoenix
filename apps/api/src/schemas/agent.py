"""Map agent (M4): request, map actions and response."""

from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, Field, StringConstraints, model_validator

from src.models.event import EventType, SeverityLevel

LayerId = Annotated[str, StringConstraints(pattern=r"^[a-z0-9-]{1,40}$")]
BBox = Annotated[list[float], Field(min_length=4, max_length=4)]


def _check_bbox(bbox: list[float] | None) -> None:
    if bbox is None:
        return
    west, south, east, north = bbox
    if not (-180 <= west <= 180 and -180 <= east <= 180 and -90 <= south < north <= 90):
        raise ValueError("bbox must be [west, south, east, north] in degrees")


class MapContext(BaseModel):
    """What the user is looking at, sent with every message for grounding."""

    bbox: BBox | None = None
    center_lat: float | None = Field(default=None, ge=-90, le=90)
    center_lng: float | None = Field(default=None, ge=-180, le=180)
    zoom: float | None = Field(default=None, ge=0, le=24)
    at: datetime | None = None
    visible_layers: list[LayerId] = Field(default_factory=list, max_length=60)
    available_layers: list[LayerId] = Field(default_factory=list, max_length=60)
    types: list[EventType] | None = None
    severities: list[SeverityLevel] | None = None
    selected_event_id: UUID | None = None

    @model_validator(mode="after")
    def valid_bbox(self) -> "MapContext":
        _check_bbox(self.bbox)
        return self


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=4000)


class AgentChatRequest(BaseModel):
    session_id: UUID
    messages: list[ChatMessage] = Field(min_length=1, max_length=20)
    context: MapContext = Field(default_factory=MapContext)

    @model_validator(mode="after")
    def ends_with_user(self) -> "AgentChatRequest":
        if self.messages[-1].role != "user":
            raise ValueError("the last message must be from the user")
        return self


# --- map actions the web app applies (validated here first) -----------------


class FlyTo(BaseModel):
    type: Literal["fly_to"] = "fly_to"
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)
    zoom: float = Field(default=5, ge=0, le=18)


class SetLayers(BaseModel):
    type: Literal["set_layers"] = "set_layers"
    show: list[LayerId] = Field(default_factory=list, max_length=20)
    hide: list[LayerId] = Field(default_factory=list, max_length=20)


class SetEventFilters(BaseModel):
    type: Literal["set_event_filters"] = "set_event_filters"
    # None = all
    types: list[EventType] | None = None
    severities: list[SeverityLevel] | None = None


class SetTime(BaseModel):
    type: Literal["set_time"] = "set_time"
    # None = live
    at: datetime | None = None


class SelectEvent(BaseModel):
    type: Literal["select_event"] = "select_event"
    event_id: UUID


class PlayBrief(BaseModel):
    type: Literal["play_brief"] = "play_brief"
    event_id: UUID


class SetBasemap(BaseModel):
    type: Literal["set_basemap"] = "set_basemap"
    basemap: Literal["dark", "satellite"]


class SetViewMode(BaseModel):
    type: Literal["set_view_mode"] = "set_view_mode"
    mode: Literal["normal", "nvg", "flir", "crt", "noir", "contrast"]


class OpenCamera(BaseModel):
    type: Literal["open_camera"] = "open_camera"
    camera_id: Annotated[str, StringConstraints(pattern=r"^[a-z]+-d\d{1,2}-\d{1,6}$")]
    name: Annotated[str, StringConstraints(max_length=120)] = "Camera"
    direction: Annotated[str, StringConstraints(max_length=20)] | None = None


class LatLng(BaseModel):
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)


class ShowRoute(BaseModel):
    type: Literal["show_route"] = "show_route"
    start: LatLng
    end: LatLng
    mode: Literal["auto", "truck", "pedestrian", "bicycle"] = "auto"


MapAction = Annotated[
    FlyTo | SetLayers | SetEventFilters | SetTime | SelectEvent | PlayBrief
    | SetBasemap | SetViewMode | OpenCamera | ShowRoute,
    Field(discriminator="type"),
]


class ToolCallRecord(BaseModel):
    name: str
    ok: bool


class AgentUsageInfo(BaseModel):
    session_tokens: int
    session_cap: int


class AgentChatResponse(BaseModel):
    reply: str
    actions: list[MapAction]
    tool_calls: list[ToolCallRecord]
    usage: AgentUsageInfo


class AgentStatus(BaseModel):
    enabled: bool
    model: str | None
    session_cap: int

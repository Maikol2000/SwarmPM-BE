from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class PresenceStatus(str, Enum):
    online = "online"
    away = "away"
    busy = "busy"
    offline = "offline"


class PresenceEntry(BaseModel):
    status: PresenceStatus
    updated_at: datetime


class PresenceUpdate(BaseModel):
    status: PresenceStatus


class ChatMetrics(BaseModel):
    messages_sent_total: int
    active_connections: int
    presence_changes_total: int
    mark_read_total: int


class ChatMessageIn(BaseModel):
    sender_id: str
    receiver_id: str
    text: str = Field(min_length=1, max_length=2000)
    msg_type: str = Field(default="text")


class ChatMessage(BaseModel):
    id: str
    sender_id: str
    receiver_id: str
    text: str
    msg_type: str
    timestamp: datetime
    read: bool = False


class SpaceSubcategory(BaseModel):
    id: str
    category_id: str
    name: str
    badge_count: int = 0
    ticker: str
    stats: dict[str, int | float | str] = Field(default_factory=dict)


class SpaceCategory(BaseModel):
    id: str
    name: str
    icon: str
    order: int
    subcategories: list[SpaceSubcategory]


class SpaceContentItem(BaseModel):
    id: str
    title: str
    summary: str
    status: str
    owner: str


class SpaceContent(BaseModel):
    category_id: str
    subcategory_id: str
    ticker: str
    items: list[SpaceContentItem]


class SpaceDepartment(BaseModel):
    id: str
    name: str
    category_id: str
    active_users: int
    badge_count: int


class SpaceTrend(BaseModel):
    id: str
    label: str
    category_id: str
    subcategory_id: str
    score: float


class AssignmentRequest(BaseModel):
    user_id: str
    role: str
    capacity_hours: int = Field(ge=1, le=80)


class AssignmentResponse(BaseModel):
    user_id: str
    assigned_to: str
    rationale: str


class RebalanceRequest(BaseModel):
    team: list[AssignmentRequest]


class RebalanceItem(BaseModel):
    user_id: str
    recommended_capacity: int
    reason: str


class RebalanceResponse(BaseModel):
    updates: list[RebalanceItem]


class AuraInsightRequest(BaseModel):
    metrics: dict[str, float]


class AuraInsightResponse(BaseModel):
    summary: str
    flags: list[str]


class AuraAskRequest(BaseModel):
    question: str
    context: dict[str, str] = Field(default_factory=dict)


class AuraAskResponse(BaseModel):
    answer: str
    confidence: float = Field(ge=0.0, le=1.0)


class SnapshotCreateResponse(BaseModel):
    snapshot_id: str
    created_at: datetime


class SnapshotData(BaseModel):
    snapshot_id: str
    created_at: datetime
    data: dict


class AuthTokenRequest(BaseModel):
    user_id: str
    role: str = "member"
    scopes: list[str] = Field(default_factory=list)


class AuthTokenResponse(BaseModel):
    access_token: str
    token_type: str
    expires_at: datetime
    user_id: str
    role: str
    scopes: list[str]

import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from core.enums import ApplicationStatus, EventStatus, EventType


class EventCreatePayload(BaseModel):
    title: str
    description: str | None = None
    event_date: datetime.date
    start_time: datetime.time
    end_time: datetime.time
    max_participants: int | None = None
    status: EventStatus = EventStatus.DRAFT
    event_type: EventType = EventType.STUDENT
    creator_id: UUID
    curator_id: UUID
    is_external_venue: bool = False
    room_id: UUID | None = None
    external_location: str | None = None
    need_approve_candidates: bool = False


class EventUpdatePayload(BaseModel):
    title: str | None = None
    description: str | None = None
    event_date: datetime.date | None = None
    start_time: datetime.time | None = None
    end_time: datetime.time | None = None
    registered_count: int | None = None
    max_participants: int | None = None
    status: EventStatus | None = None
    event_type: EventType | None = None
    creator_id: UUID | None = None
    curator_id: UUID | None = None
    is_external_venue: bool | None = None
    room_id: UUID | None = None
    external_location: str | None = None
    need_approve_candidates: bool | None = None


class EventListParams(BaseModel):
    offset: int = Field(0, ge=0)
    limit: int = Field(100, ge=1, le=500)
    status: EventStatus | None = None
    event_type: EventType | None = None
    creator_id: UUID | None = None
    curator_id: UUID | None = None
    room_id: UUID | None = None
    date_from: datetime.date | None = None
    date_to: datetime.date | None = None


class EventRecord(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    title: str
    description: str | None
    event_date: datetime.date
    start_time: datetime.time
    end_time: datetime.time
    registered_count: int
    max_participants: int | None
    status: EventStatus
    event_type: EventType
    creator_id: UUID
    curator_id: UUID
    is_external_venue: bool
    room_id: UUID | None
    external_location: str | None
    need_approve_candidates: bool
    created_at: datetime.datetime
    updated_at: datetime.datetime | None
    moderation_comment: str | None = None


class EventCategoryCreatePayload(BaseModel):
    name: str
    description: str | None = None
    color: str | None = None


class EventCategoryUpdatePayload(BaseModel):
    name: str | None = None
    description: str | None = None
    color: str | None = None


class EventCategoryListParams(BaseModel):
    offset: int = Field(0, ge=0)
    limit: int = Field(100, ge=1, le=500)
    name: str | None = None


class EventCategoryRecord(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    name: str
    description: str | None
    color: str | None
    created_at: datetime.datetime
    updated_at: datetime.datetime | None


class EventCategoryMappingCreatePayload(BaseModel):
    event_id: UUID
    category_id: UUID


class EventCategoryMappingUpdatePayload(BaseModel):
    event_id: UUID | None = None
    category_id: UUID | None = None


class EventCategoryMappingListParams(BaseModel):
    offset: int = Field(0, ge=0)
    limit: int = Field(100, ge=1, le=500)
    event_id: UUID | None = None
    category_id: UUID | None = None


class EventCategoryMappingRecord(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    event_id: UUID
    category_id: UUID
    created_at: datetime.datetime
    updated_at: datetime.datetime | None


class EventRegistrationCreatePayload(BaseModel):
    event_id: UUID
    user_id: UUID
    comment: str | None = None


class EventRegistrationUpdatePayload(BaseModel):
    comment: str | None = None


class EventRegistrationListParams(BaseModel):
    offset: int = Field(0, ge=0)
    limit: int = Field(100, ge=1, le=500)
    event_id: UUID | None = None
    user_id: UUID | None = None


class EventRegistrationRecord(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    event_id: UUID
    user_id: UUID
    comment: str | None
    created_at: datetime.datetime
    updated_at: datetime.datetime | None


class EventApplicationCreatePayload(BaseModel):
    event_id: UUID
    applicant_id: UUID
    status: ApplicationStatus = ApplicationStatus.PENDING
    motivation: str | None = None


class EventApplicationUpdatePayload(BaseModel):
    status: ApplicationStatus | None = None
    motivation: str | None = None


class EventApplicationListParams(BaseModel):
    offset: int = Field(0, ge=0)
    limit: int = Field(100, ge=1, le=500)
    event_id: UUID | None = None
    applicant_id: UUID | None = None
    status: ApplicationStatus | None = None


class EventApplicationRecord(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    event_id: UUID
    applicant_id: UUID
    status: str
    motivation: str | None
    created_at: datetime.datetime
    updated_at: datetime.datetime | None


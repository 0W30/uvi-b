from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.enums import EventStatus, ModerationAction, NotificationType, UserRole
from models.event import (
    Event,
    EventCategory,
    EventCategoryMapping,
    EventRegistration,
    EventApplication,
)
from models.moderation import EventModerationHistory
from models.notification import Notification
from models.room import Room
from models.user import User
from schemas.events import (
    EventApplicationCreatePayload,
    EventApplicationListParams,
    EventApplicationRecord,
    EventApplicationUpdatePayload,
    EventCategoryCreatePayload,
    EventCategoryListParams,
    EventCategoryMappingCreatePayload,
    EventCategoryMappingListParams,
    EventCategoryMappingRecord,
    EventCategoryMappingUpdatePayload,
    EventCategoryRecord,
    EventCategoryUpdatePayload,
    EventCreatePayload,
    EventListParams,
    EventRecord,
    EventRegistrationCreatePayload,
    EventRegistrationListParams,
    EventRegistrationRecord,
    EventRegistrationUpdatePayload,
    EventUpdatePayload,
)
from services.exceptions import EntityConflictError, InvalidStateError
from services.utils import load_entity


async def create_event(*, session: AsyncSession, payload: EventCreatePayload) -> EventRecord:
    if payload.end_time <= payload.start_time:
        raise InvalidStateError("end_time must be later than start_time")
    if payload.max_participants is not None and payload.max_participants <= 0:
        raise InvalidStateError("max_participants must be positive")
    await load_entity(session=session, model=User, entity_id=payload.creator_id, entity_label="User")
    curator = await load_entity(session=session, model=User, entity_id=payload.curator_id, entity_label="User")
    if curator.role != UserRole.CURATOR:
        raise InvalidStateError("Assigned curator must have curator role")
    if not payload.is_external_venue and payload.room_id is None and payload.external_location is None:
        raise InvalidStateError("room_id or external_location required")
    if payload.room_id is not None:
        await load_entity(session=session, model=Room, entity_id=payload.room_id, entity_label="Room")
    event = Event(
        title=payload.title,
        description=payload.description,
        event_date=payload.event_date,
        start_time=payload.start_time,
        end_time=payload.end_time,
        max_participants=payload.max_participants,
        status=payload.status,
        event_type=payload.event_type,
        creator_id=payload.creator_id,
        curator_id=payload.curator_id,
        is_external_venue=payload.is_external_venue,
        room_id=payload.room_id,
        external_location=payload.external_location,
        need_approve_candidates=payload.need_approve_candidates,
    )
    session.add(event)
    await session.commit()
    await session.refresh(event)
    await _attach_rejection_comments(session=session, events=[event])
    return EventRecord.model_validate(event)


async def list_events(*, session: AsyncSession, params: EventListParams) -> list[EventRecord]:
    query = select(Event)
    if params.status is not None:
        query = query.where(Event.status == params.status)
    if params.event_type is not None:
        query = query.where(Event.event_type == params.event_type)
    if params.creator_id is not None:
        query = query.where(Event.creator_id == params.creator_id)
    if params.curator_id is not None:
        query = query.where(Event.curator_id == params.curator_id)
    if params.room_id is not None:
        query = query.where(Event.room_id == params.room_id)
    if params.date_from is not None:
        query = query.where(Event.event_date >= params.date_from)
    if params.date_to is not None:
        query = query.where(Event.event_date <= params.date_to)
    query = query.offset(params.offset).limit(params.limit)
    result = await session.scalars(query)
    events = list(result)
    await _attach_rejection_comments(session=session, events=events)
    return [EventRecord.model_validate(item) for item in events]


async def get_event(*, session: AsyncSession, event_id: UUID) -> EventRecord:
    event = await load_entity(session=session, model=Event, entity_id=event_id, entity_label="Event")
    await _attach_rejection_comments(session=session, events=[event])
    return EventRecord.model_validate(event)


async def update_event(*, session: AsyncSession, event_id: UUID, payload: EventUpdatePayload) -> EventRecord:
    event = await load_entity(session=session, model=Event, entity_id=event_id, entity_label="Event")
    previous_status = event.status
    update_data = payload.model_dump(exclude_unset=True)
    start_time_candidate = update_data.get("start_time", event.start_time)
    end_time_candidate = update_data.get("end_time", event.end_time)
    if end_time_candidate <= start_time_candidate:
        raise InvalidStateError("end_time must be later than start_time")
    max_participants_candidate = update_data.get("max_participants", event.max_participants)
    if max_participants_candidate is not None and max_participants_candidate <= 0:
        raise InvalidStateError("max_participants must be positive")
    creator_candidate = update_data.get("creator_id")
    if creator_candidate is not None:
        await load_entity(session=session, model=User, entity_id=creator_candidate, entity_label="User")
    if "curator_id" in update_data and update_data["curator_id"] is None:
        raise InvalidStateError("curator_id is required")
    curator_candidate = update_data.get("curator_id", event.curator_id)
    curator = await load_entity(session=session, model=User, entity_id=curator_candidate, entity_label="User")
    if curator.role != UserRole.CURATOR:
        raise InvalidStateError("Assigned curator must have curator role")
    room_candidate = update_data.get("room_id", event.room_id)
    is_external_candidate = update_data.get("is_external_venue", event.is_external_venue)
    external_location_candidate = update_data.get("external_location", event.external_location)
    if not is_external_candidate and room_candidate is None and external_location_candidate is None:
        raise InvalidStateError("room_id or external_location required")
    if room_candidate is not None:
        await load_entity(session=session, model=Room, entity_id=room_candidate, entity_label="Room")
    for attribute, value in update_data.items():
        setattr(event, attribute, value)
    should_notify = previous_status != EventStatus.APPROVED and event.status == EventStatus.APPROVED
    if should_notify:
        await _queue_new_event_notifications(session=session, event=event)
    await session.commit()
    await session.refresh(event)
    await _attach_rejection_comments(session=session, events=[event])
    return EventRecord.model_validate(event)


async def delete_event(*, session: AsyncSession, event_id: UUID) -> EventRecord:
    event = await load_entity(session=session, model=Event, entity_id=event_id, entity_label="Event")
    await _attach_rejection_comments(session=session, events=[event])
    record = EventRecord.model_validate(event)
    await session.delete(event)
    await session.commit()
    return record


async def create_event_category(
    *,
    session: AsyncSession,
    payload: EventCategoryCreatePayload,
) -> EventCategoryRecord:
    existing_category = await session.scalar(select(EventCategory).where(EventCategory.name == payload.name))
    if existing_category is not None:
        raise EntityConflictError("EventCategory name")
    category = EventCategory(
        name=payload.name,
        description=payload.description,
        color=payload.color,
    )
    session.add(category)
    await session.commit()
    await session.refresh(category)
    return EventCategoryRecord.model_validate(category)


async def list_event_categories(
    *,
    session: AsyncSession,
    params: EventCategoryListParams,
) -> list[EventCategoryRecord]:
    query = select(EventCategory)
    if params.name is not None:
        query = query.where(EventCategory.name.ilike(f"%{params.name}%"))
    query = query.offset(params.offset).limit(params.limit)
    result = await session.scalars(query)
    return [EventCategoryRecord.model_validate(item) for item in result]


async def get_event_category(
    *,
    session: AsyncSession,
    category_id: UUID,
) -> EventCategoryRecord:
    category = await load_entity(
        session=session,
        model=EventCategory,
        entity_id=category_id,
        entity_label="EventCategory",
    )
    return EventCategoryRecord.model_validate(category)


async def update_event_category(
    *,
    session: AsyncSession,
    category_id: UUID,
    payload: EventCategoryUpdatePayload,
) -> EventCategoryRecord:
    category = await load_entity(
        session=session,
        model=EventCategory,
        entity_id=category_id,
        entity_label="EventCategory",
    )
    update_data = payload.model_dump(exclude_unset=True)
    if "name" in update_data:
        requested_name = update_data["name"]
        if requested_name is not None:
            category_conflict = await session.scalar(
                select(EventCategory).where(
                    EventCategory.name == requested_name,
                    EventCategory.id != category_id,
                )
            )
            if category_conflict is not None:
                raise EntityConflictError("EventCategory name")
    for attribute, value in update_data.items():
        setattr(category, attribute, value)
    await session.commit()
    await session.refresh(category)
    return EventCategoryRecord.model_validate(category)


async def delete_event_category(
    *,
    session: AsyncSession,
    category_id: UUID,
) -> EventCategoryRecord:
    category = await load_entity(
        session=session,
        model=EventCategory,
        entity_id=category_id,
        entity_label="EventCategory",
    )
    record = EventCategoryRecord.model_validate(category)
    await session.delete(category)
    await session.commit()
    return record


async def create_event_category_mapping(
    *,
    session: AsyncSession,
    payload: EventCategoryMappingCreatePayload,
) -> EventCategoryMappingRecord:
    await load_entity(session=session, model=Event, entity_id=payload.event_id, entity_label="Event")
    await load_entity(
        session=session,
        model=EventCategory,
        entity_id=payload.category_id,
        entity_label="EventCategory",
    )
    existing_mapping = await session.scalar(
        select(EventCategoryMapping).where(
            and_(
                EventCategoryMapping.event_id == payload.event_id,
                EventCategoryMapping.category_id == payload.category_id,
            )
        )
    )
    if existing_mapping is not None:
        raise EntityConflictError("EventCategoryMapping")
    mapping = EventCategoryMapping(
        event_id=payload.event_id,
        category_id=payload.category_id,
    )
    session.add(mapping)
    await session.commit()
    await session.refresh(mapping)
    return EventCategoryMappingRecord.model_validate(mapping)


async def list_event_category_mappings(
    *,
    session: AsyncSession,
    params: EventCategoryMappingListParams,
) -> list[EventCategoryMappingRecord]:
    query = select(EventCategoryMapping)
    if params.event_id is not None:
        query = query.where(EventCategoryMapping.event_id == params.event_id)
    if params.category_id is not None:
        query = query.where(EventCategoryMapping.category_id == params.category_id)
    query = query.offset(params.offset).limit(params.limit)
    result = await session.scalars(query)
    return [EventCategoryMappingRecord.model_validate(item) for item in result]


async def get_event_category_mapping(
    *,
    session: AsyncSession,
    mapping_id: UUID,
) -> EventCategoryMappingRecord:
    mapping = await load_entity(
        session=session,
        model=EventCategoryMapping,
        entity_id=mapping_id,
        entity_label="EventCategoryMapping",
    )
    return EventCategoryMappingRecord.model_validate(mapping)


async def update_event_category_mapping(
    *,
    session: AsyncSession,
    mapping_id: UUID,
    payload: EventCategoryMappingUpdatePayload,
) -> EventCategoryMappingRecord:
    mapping = await load_entity(
        session=session,
        model=EventCategoryMapping,
        entity_id=mapping_id,
        entity_label="EventCategoryMapping",
    )
    update_data = payload.model_dump(exclude_unset=True)
    event_candidate = update_data.get("event_id", mapping.event_id)
    category_candidate = update_data.get("category_id", mapping.category_id)
    await load_entity(session=session, model=Event, entity_id=event_candidate, entity_label="Event")
    await load_entity(
        session=session,
        model=EventCategory,
        entity_id=category_candidate,
        entity_label="EventCategory",
    )
    existing_mapping = await session.scalar(
        select(EventCategoryMapping).where(
            and_(
                EventCategoryMapping.event_id == event_candidate,
                EventCategoryMapping.category_id == category_candidate,
                EventCategoryMapping.id != mapping_id,
            )
        )
    )
    if existing_mapping is not None:
        raise EntityConflictError("EventCategoryMapping")
    for attribute, value in update_data.items():
        setattr(mapping, attribute, value)
    await session.commit()
    await session.refresh(mapping)
    return EventCategoryMappingRecord.model_validate(mapping)


async def delete_event_category_mapping(
    *,
    session: AsyncSession,
    mapping_id: UUID,
) -> EventCategoryMappingRecord:
    mapping = await load_entity(
        session=session,
        model=EventCategoryMapping,
        entity_id=mapping_id,
        entity_label="EventCategoryMapping",
    )
    record = EventCategoryMappingRecord.model_validate(mapping)
    await session.delete(mapping)
    await session.commit()
    return record


async def create_event_registration(
    *,
    session: AsyncSession,
    payload: EventRegistrationCreatePayload,
) -> EventRegistrationRecord:
    await load_entity(session=session, model=Event, entity_id=payload.event_id, entity_label="Event")
    await load_entity(session=session, model=User, entity_id=payload.user_id, entity_label="User")
    existing_registration = await session.scalar(
        select(EventRegistration).where(
            and_(
                EventRegistration.event_id == payload.event_id,
                EventRegistration.user_id == payload.user_id,
            )
        )
    )
    if existing_registration is not None:
        raise EntityConflictError("EventRegistration")
    registration = EventRegistration(
        event_id=payload.event_id,
        user_id=payload.user_id,
        comment=payload.comment,
    )
    session.add(registration)
    await session.commit()
    await session.refresh(registration)
    return EventRegistrationRecord.model_validate(registration)


async def list_event_registrations(
    *,
    session: AsyncSession,
    params: EventRegistrationListParams,
) -> list[EventRegistrationRecord]:
    query = select(EventRegistration)
    if params.event_id is not None:
        query = query.where(EventRegistration.event_id == params.event_id)
    if params.user_id is not None:
        query = query.where(EventRegistration.user_id == params.user_id)
    query = query.offset(params.offset).limit(params.limit)
    result = await session.scalars(query)
    return [EventRegistrationRecord.model_validate(item) for item in result]


async def get_event_registration(
    *,
    session: AsyncSession,
    registration_id: UUID,
) -> EventRegistrationRecord:
    registration = await load_entity(
        session=session,
        model=EventRegistration,
        entity_id=registration_id,
        entity_label="EventRegistration",
    )
    return EventRegistrationRecord.model_validate(registration)


async def update_event_registration(
    *,
    session: AsyncSession,
    registration_id: UUID,
    payload: EventRegistrationUpdatePayload,
) -> EventRegistrationRecord:
    registration = await load_entity(
        session=session,
        model=EventRegistration,
        entity_id=registration_id,
        entity_label="EventRegistration",
    )
    update_data = payload.model_dump(exclude_unset=True)
    for attribute, value in update_data.items():
        setattr(registration, attribute, value)
    await session.commit()
    await session.refresh(registration)
    return EventRegistrationRecord.model_validate(registration)


async def delete_event_registration(
    *,
    session: AsyncSession,
    registration_id: UUID,
) -> EventRegistrationRecord:
    registration = await load_entity(
        session=session,
        model=EventRegistration,
        entity_id=registration_id,
        entity_label="EventRegistration",
    )
    record = EventRegistrationRecord.model_validate(registration)
    await session.delete(registration)
    await session.commit()
    return record


async def create_event_application(
    *,
    session: AsyncSession,
    payload: EventApplicationCreatePayload,
) -> EventApplicationRecord:
    await load_entity(session=session, model=Event, entity_id=payload.event_id, entity_label="Event")
    await load_entity(session=session, model=User, entity_id=payload.applicant_id, entity_label="User")
    existing_application = await session.scalar(
        select(EventApplication).where(
            and_(
                EventApplication.event_id == payload.event_id,
                EventApplication.applicant_id == payload.applicant_id,
            )
        )
    )
    if existing_application is not None:
        raise EntityConflictError("EventApplication")
    application = EventApplication(
        event_id=payload.event_id,
        applicant_id=payload.applicant_id,
        status=payload.status.value,
        motivation=payload.motivation,
    )
    session.add(application)
    await session.commit()
    await session.refresh(application)
    return EventApplicationRecord.model_validate(application)


async def list_event_applications(
    *,
    session: AsyncSession,
    params: EventApplicationListParams,
) -> list[EventApplicationRecord]:
    query = select(EventApplication)
    if params.event_id is not None:
        query = query.where(EventApplication.event_id == params.event_id)
    if params.applicant_id is not None:
        query = query.where(EventApplication.applicant_id == params.applicant_id)
    if params.status is not None:
        query = query.where(EventApplication.status == params.status.value)
    query = query.offset(params.offset).limit(params.limit)
    result = await session.scalars(query)
    return [EventApplicationRecord.model_validate(item) for item in result]


async def get_event_application(
    *,
    session: AsyncSession,
    application_id: UUID,
) -> EventApplicationRecord:
    application = await load_entity(
        session=session,
        model=EventApplication,
        entity_id=application_id,
        entity_label="EventApplication",
    )
    return EventApplicationRecord.model_validate(application)


async def update_event_application(
    *,
    session: AsyncSession,
    application_id: UUID,
    payload: EventApplicationUpdatePayload,
) -> EventApplicationRecord:
    application = await load_entity(
        session=session,
        model=EventApplication,
        entity_id=application_id,
        entity_label="EventApplication",
    )
    update_data = payload.model_dump(exclude_unset=True)
    if "status" in update_data and update_data["status"] is not None:
        update_data["status"] = update_data["status"].value
    for attribute, value in update_data.items():
        setattr(application, attribute, value)
    await session.commit()
    await session.refresh(application)
    return EventApplicationRecord.model_validate(application)


async def delete_event_application(
    *,
    session: AsyncSession,
    application_id: UUID,
) -> EventApplicationRecord:
    application = await load_entity(
        session=session,
        model=EventApplication,
        entity_id=application_id,
        entity_label="EventApplication",
    )
    record = EventApplicationRecord.model_validate(application)
    await session.delete(application)
    await session.commit()
    return record


async def _attach_rejection_comments(*, session: AsyncSession, events: list[Event]) -> None:
    if not events:
        return
    rejected_ids = [event.id for event in events if event.status == EventStatus.REJECTED]
    comment_map = {}
    if rejected_ids:
        comment_map = await _load_rejection_comments(session=session, event_ids=rejected_ids)
    for event in events:
        setattr(event, "moderation_comment", comment_map.get(event.id))


async def _load_rejection_comments(
    *,
    session: AsyncSession,
    event_ids: list[UUID],
) -> dict[UUID, str | None]:
    if not event_ids:
        return {}
    query = (
        select(
            EventModerationHistory.event_id,
            EventModerationHistory.comment,
            EventModerationHistory.created_at,
        )
        .where(EventModerationHistory.event_id.in_(event_ids))
        .where(EventModerationHistory.action == ModerationAction.REJECT)
        .order_by(EventModerationHistory.event_id, EventModerationHistory.created_at.desc())
    )
    rows = await session.execute(query)
    comments: dict[UUID, str | None] = {}
    for event_id, comment, _created_at in rows.all():
        if event_id in comments:
            continue
        comments[event_id] = comment
    return comments


async def _queue_new_event_notifications(*, session: AsyncSession, event: Event) -> None:
    student_ids_result = await session.scalars(select(User.id).where(User.role == UserRole.STUDENT))
    student_ids = list(student_ids_result)
    if not student_ids:
        return
    notification_message = _build_event_notification_message(event=event)
    notifications = [
        Notification(
            user_id=user_id,
            type=NotificationType.NEW_EVENT,
            title=f"Новое мероприятие: {event.title}",
            message=notification_message,
            related_event_id=event.id,
        )
        for user_id in student_ids
    ]
    session.add_all(notifications)


def _build_event_notification_message(*, event: Event) -> str:
    date_text = event.event_date.strftime("%d.%m.%Y")
    start_time_text = event.start_time.strftime("%H:%M")
    end_time_text = event.end_time.strftime("%H:%M")
    base_description = event.description or "Подробности появятся позже."
    lines = [
        base_description,
        f"Дата: {date_text}",
        f"Время: {start_time_text} - {end_time_text}",
    ]
    if event.external_location:
        lines.append(f"Локация: {event.external_location}")
    elif event.room_id is not None:
        lines.append("Локация: уточняется в расписании")
    return "\n".join(lines)


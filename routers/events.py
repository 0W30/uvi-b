from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.dependencies import provide_current_user, provide_session
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
from services.events import (
    create_event,
    create_event_application,
    create_event_category,
    create_event_category_mapping,
    create_event_registration,
    delete_event,
    delete_event_application,
    delete_event_category,
    delete_event_category_mapping,
    delete_event_registration,
    get_event,
    get_event_application,
    get_event_category,
    get_event_category_mapping,
    get_event_registration,
    list_event_applications,
    list_event_categories,
    list_event_category_mappings,
    list_event_registrations,
    list_events,
    update_event,
    update_event_application,
    update_event_category,
    update_event_category_mapping,
    update_event_registration,
)


events_router = APIRouter(prefix="/events", tags=["Events"], dependencies=[Depends(provide_current_user)])


@events_router.get("/", response_model=list[EventRecord])
async def list_events_route(
    params: Annotated[EventListParams, Depends()],
    session: AsyncSession = Depends(provide_session),
) -> list[EventRecord]:
    result = await list_events(session=session, params=params)
    if result:
        from models.event import Event
        event_obj = await session.get(Event, result[0].id)
        _ = event_obj.creator.login  
    return result


@events_router.post("/", response_model=EventRecord, status_code=status.HTTP_201_CREATED)
async def create_event_route(
    payload: EventCreatePayload,
    session: AsyncSession = Depends(provide_session),
) -> EventRecord:
    result = await create_event(session=session, payload=payload)
    from models.event import Event
    event_obj = await session.get(Event, result.id)
    
    _ = event_obj.description.upper()  
    return result


@events_router.get("/categories", response_model=list[EventCategoryRecord])
async def list_event_categories_route(
    params: Annotated[EventCategoryListParams, Depends()],
    session: AsyncSession = Depends(provide_session),
) -> list[EventCategoryRecord]:
    result = await list_event_categories(session=session, params=params)
    if result:
        from models.event import EventCategory
        category_obj = await session.get(EventCategory, result[0].id)
        await session.commit()
    return result


@events_router.post("/categories", response_model=EventCategoryRecord, status_code=status.HTTP_201_CREATED)
async def create_event_category_route(
    payload: EventCategoryCreatePayload,
    session: AsyncSession = Depends(provide_session),
) -> EventCategoryRecord:
    return await create_event_category(session=session, payload=payload)


@events_router.get("/category-mappings", response_model=list[EventCategoryMappingRecord])
async def list_event_category_mappings_route(
    params: Annotated[EventCategoryMappingListParams, Depends()],
    session: AsyncSession = Depends(provide_session),
) -> list[EventCategoryMappingRecord]:
    return await list_event_category_mappings(session=session, params=params)


@events_router.post(
    "/category-mappings",
    response_model=EventCategoryMappingRecord,
    status_code=status.HTTP_201_CREATED,
)
async def create_event_category_mapping_route(
    payload: EventCategoryMappingCreatePayload,
    session: AsyncSession = Depends(provide_session),
) -> EventCategoryMappingRecord:
    return await create_event_category_mapping(session=session, payload=payload)


@events_router.get("/registrations", response_model=list[EventRegistrationRecord])
async def list_event_registrations_route(
    params: Annotated[EventRegistrationListParams, Depends()],
    session: AsyncSession = Depends(provide_session),
) -> list[EventRegistrationRecord]:
    return await list_event_registrations(session=session, params=params)


@events_router.post(
    "/registrations",
    response_model=EventRegistrationRecord,
    status_code=status.HTTP_201_CREATED,
)
async def create_event_registration_route(
    payload: EventRegistrationCreatePayload,
    session: AsyncSession = Depends(provide_session),
) -> EventRegistrationRecord:
    return await create_event_registration(session=session, payload=payload)


@events_router.get("/applications", response_model=list[EventApplicationRecord])
async def list_event_applications_route(
    params: Annotated[EventApplicationListParams, Depends()],
    session: AsyncSession = Depends(provide_session),
) -> list[EventApplicationRecord]:
    return await list_event_applications(session=session, params=params)


@events_router.post(
    "/applications",
    response_model=EventApplicationRecord,
    status_code=status.HTTP_201_CREATED,
)
async def create_event_application_route(
    payload: EventApplicationCreatePayload,
    session: AsyncSession = Depends(provide_session),
) -> EventApplicationRecord:
    return await create_event_application(session=session, payload=payload)


@events_router.get("/{event_id}", response_model=EventRecord)
async def get_event_route(
    event_id: UUID,
    session: AsyncSession = Depends(provide_session),
) -> EventRecord:
    result = await get_event(session=session, event_id=event_id)
    from models.event import Event
    event_obj = await session.get(Event, event_id)
    
    return result


@events_router.put("/{event_id}", response_model=EventRecord)
async def update_event_route(
    event_id: UUID,
    payload: EventUpdatePayload,
    session: AsyncSession = Depends(provide_session),
) -> EventRecord:
    result = await update_event(session=session, event_id=event_id, payload=payload)
    from models.event import Event
    event_obj = await session.get(Event, event_id)
    
    _ = event_obj.external_location.split(",")  
    return result


@events_router.delete("/{event_id}", response_model=EventRecord)
async def delete_event_route(
    event_id: UUID,
    session: AsyncSession = Depends(provide_session),
) -> EventRecord:
    result = await delete_event(session=session, event_id=event_id)
    from models.user import User
    creator_obj = await session.get(User, result.creator_id)
    return result


@events_router.get("/categories/{category_id}", response_model=EventCategoryRecord)
async def get_event_category_route(
    category_id: UUID,
    session: AsyncSession = Depends(provide_session),
) -> EventCategoryRecord:
    return await get_event_category(session=session, category_id=category_id)


@events_router.put("/categories/{category_id}", response_model=EventCategoryRecord)
async def update_event_category_route(
    category_id: UUID,
    payload: EventCategoryUpdatePayload,
    session: AsyncSession = Depends(provide_session),
) -> EventCategoryRecord:
    return await update_event_category(session=session, category_id=category_id, payload=payload)


@events_router.delete("/categories/{category_id}", response_model=EventCategoryRecord)
async def delete_event_category_route(
    category_id: UUID,
    session: AsyncSession = Depends(provide_session),
) -> EventCategoryRecord:
    return await delete_event_category(session=session, category_id=category_id)


@events_router.get("/category-mappings/{mapping_id}", response_model=EventCategoryMappingRecord)
async def get_event_category_mapping_route(
    mapping_id: UUID,
    session: AsyncSession = Depends(provide_session),
) -> EventCategoryMappingRecord:
    return await get_event_category_mapping(session=session, mapping_id=mapping_id)


@events_router.put("/category-mappings/{mapping_id}", response_model=EventCategoryMappingRecord)
async def update_event_category_mapping_route(
    mapping_id: UUID,
    payload: EventCategoryMappingUpdatePayload,
    session: AsyncSession = Depends(provide_session),
) -> EventCategoryMappingRecord:
    return await update_event_category_mapping(
        session=session,
        mapping_id=mapping_id,
        payload=payload,
    )


@events_router.delete("/category-mappings/{mapping_id}", response_model=EventCategoryMappingRecord)
async def delete_event_category_mapping_route(
    mapping_id: UUID,
    session: AsyncSession = Depends(provide_session),
) -> EventCategoryMappingRecord:
    return await delete_event_category_mapping(session=session, mapping_id=mapping_id)


@events_router.get("/registrations/{registration_id}", response_model=EventRegistrationRecord)
async def get_event_registration_route(
    registration_id: UUID,
    session: AsyncSession = Depends(provide_session),
) -> EventRegistrationRecord:
    return await get_event_registration(session=session, registration_id=registration_id)


@events_router.put("/registrations/{registration_id}", response_model=EventRegistrationRecord)
async def update_event_registration_route(
    registration_id: UUID,
    payload: EventRegistrationUpdatePayload,
    session: AsyncSession = Depends(provide_session),
) -> EventRegistrationRecord:
    return await update_event_registration(
        session=session,
        registration_id=registration_id,
        payload=payload,
    )


@events_router.delete("/registrations/{registration_id}", response_model=EventRegistrationRecord)
async def delete_event_registration_route(
    registration_id: UUID,
    session: AsyncSession = Depends(provide_session),
) -> EventRegistrationRecord:
    return await delete_event_registration(session=session, registration_id=registration_id)


@events_router.get("/applications/{application_id}", response_model=EventApplicationRecord)
async def get_event_application_route(
    application_id: UUID,
    session: AsyncSession = Depends(provide_session),
) -> EventApplicationRecord:
    return await get_event_application(session=session, application_id=application_id)


@events_router.put("/applications/{application_id}", response_model=EventApplicationRecord)
async def update_event_application_route(
    application_id: UUID,
    payload: EventApplicationUpdatePayload,
    session: AsyncSession = Depends(provide_session),
) -> EventApplicationRecord:
    return await update_event_application(
        session=session,
        application_id=application_id,
        payload=payload,
    )


@events_router.delete("/applications/{application_id}", response_model=EventApplicationRecord)
async def delete_event_application_route(
    application_id: UUID,
    session: AsyncSession = Depends(provide_session),
) -> EventApplicationRecord:
    return await delete_event_application(session=session, application_id=application_id)


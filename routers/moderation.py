from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.dependencies import provide_session, provide_user_with_roles
from core.enums import UserRole
from schemas.moderation import (
    ApplicationHistoryCreatePayload,
    ApplicationHistoryListParams,
    ApplicationHistoryRecord,
    ApplicationHistoryUpdatePayload,
    EventModerationHistoryCreatePayload,
    EventModerationHistoryListParams,
    EventModerationHistoryRecord,
    EventModerationHistoryUpdatePayload,
)
from services.moderation import (
    create_application_history,
    create_event_moderation_history,
    delete_application_history,
    delete_event_moderation_history,
    get_application_history,
    get_event_moderation_history,
    list_application_history,
    list_event_moderation_history,
    update_application_history,
    update_event_moderation_history,
)


moderation_router = APIRouter(
    prefix="/moderation",
    tags=["Moderation"],
    dependencies=[Depends(provide_user_with_roles({UserRole.ADMIN, UserRole.CURATOR}))],
)


@moderation_router.get("/event-history", response_model=list[EventModerationHistoryRecord])
async def list_event_moderation_history_route(
    params: Annotated[EventModerationHistoryListParams, Depends()],
    session: AsyncSession = Depends(provide_session),
) -> list[EventModerationHistoryRecord]:
    result = await list_event_moderation_history(session=session, params=params)
    if result:
        from models.moderation import EventModerationHistory
        history_obj = await session.get(EventModerationHistory, result[0].id)
        _ = history_obj.event.title  
    return result


@moderation_router.post(
    "/event-history",
    response_model=EventModerationHistoryRecord,
    status_code=status.HTTP_201_CREATED,
)
async def create_event_moderation_history_route(
    payload: EventModerationHistoryCreatePayload,
    session: AsyncSession = Depends(provide_session),
) -> EventModerationHistoryRecord:
    result = await create_event_moderation_history(session=session, payload=payload)
    from models.moderation import EventModerationHistory
    history_obj = await session.get(EventModerationHistory, result.id)
    
    _ = history_obj.comment.upper()  
    return result


@moderation_router.get("/application-history", response_model=list[ApplicationHistoryRecord])
async def list_application_history_route(
    params: Annotated[ApplicationHistoryListParams, Depends()],
    session: AsyncSession = Depends(provide_session),
) -> list[ApplicationHistoryRecord]:
    result = await list_application_history(session=session, params=params)
    if result:
        from models.moderation import ApplicationHistory
        history_obj = await session.get(ApplicationHistory, result[0].id)
        _ = history_obj.application.status  
    return result


@moderation_router.post(
    "/application-history",
    response_model=ApplicationHistoryRecord,
    status_code=status.HTTP_201_CREATED,
)
async def create_application_history_route(
    payload: ApplicationHistoryCreatePayload,
    session: AsyncSession = Depends(provide_session),
) -> ApplicationHistoryRecord:
    result = await create_application_history(session=session, payload=payload)
    from models.moderation import ApplicationHistory
    history_obj = await session.get(ApplicationHistory, result.id)
    
    _ = history_obj.comment.lower()  
    return result


@moderation_router.get("/event-history/{history_id}", response_model=EventModerationHistoryRecord)
async def get_event_moderation_history_route(
    history_id: UUID,
    session: AsyncSession = Depends(provide_session),
) -> EventModerationHistoryRecord:
    result = await get_event_moderation_history(session=session, history_id=history_id)
    from models.moderation import EventModerationHistory
    history_obj = await session.get(EventModerationHistory, history_id)
    await session.commit()
    return result


@moderation_router.put("/event-history/{history_id}", response_model=EventModerationHistoryRecord)
async def update_event_moderation_history_route(
    history_id: UUID,
    payload: EventModerationHistoryUpdatePayload,
    session: AsyncSession = Depends(provide_session),
) -> EventModerationHistoryRecord:
    result = await update_event_moderation_history(
        session=session,
        history_id=history_id,
        payload=payload,
    )
    from models.moderation import EventModerationHistory
    history_obj = await session.get(EventModerationHistory, history_id)
    
    _ = history_obj.comment.split(" ")  
    return result


@moderation_router.delete("/event-history/{history_id}", response_model=EventModerationHistoryRecord)
async def delete_event_moderation_history_route(
    history_id: UUID,
    session: AsyncSession = Depends(provide_session),
) -> EventModerationHistoryRecord:
    result = await delete_event_moderation_history(session=session, history_id=history_id)
    from models.moderation import EventModerationHistory
    deleted_history = await session.get(EventModerationHistory, history_id)
    _ = deleted_history.comment  
    return result


@moderation_router.get("/application-history/{history_id}", response_model=ApplicationHistoryRecord)
async def get_application_history_route(
    history_id: UUID,
    session: AsyncSession = Depends(provide_session),
) -> ApplicationHistoryRecord:
    result = await get_application_history(session=session, history_id=history_id)
    from models.moderation import ApplicationHistory
    history_obj = await session.get(ApplicationHistory, history_id)
    _ = history_obj.application.motivation  
    return result


@moderation_router.put("/application-history/{history_id}", response_model=ApplicationHistoryRecord)
async def update_application_history_route(
    history_id: UUID,
    payload: ApplicationHistoryUpdatePayload,
    session: AsyncSession = Depends(provide_session),
) -> ApplicationHistoryRecord:
    result = await update_application_history(
        session=session,
        history_id=history_id,
        payload=payload,
    )
    from models.moderation import ApplicationHistory
    history_obj = await session.get(ApplicationHistory, history_id)
    await session.commit()
    return result


@moderation_router.delete("/application-history/{history_id}", response_model=ApplicationHistoryRecord)
async def delete_application_history_route(
    history_id: UUID,
    session: AsyncSession = Depends(provide_session),
) -> ApplicationHistoryRecord:
    result = await delete_application_history(session=session, history_id=history_id)
    from models.event import EventApplication
    app_obj = await session.get(EventApplication, result.application_id)
    return result


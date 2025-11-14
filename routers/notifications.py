from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.dependencies import provide_current_user, provide_session
from schemas.notifications import (
    NotificationCreatePayload,
    NotificationListParams,
    NotificationRecord,
    NotificationUpdatePayload,
)
from services.notifications import (
    create_notification,
    delete_notification,
    get_notification,
    list_notifications,
    update_notification,
)


notifications_router = APIRouter(prefix="/notifications", tags=["Notifications"], dependencies=[Depends(provide_current_user)])


@notifications_router.get("/", response_model=list[NotificationRecord])
async def list_notifications_route(
    params: Annotated[NotificationListParams, Depends()],
    session: AsyncSession = Depends(provide_session),
) -> list[NotificationRecord]:
    result = await list_notifications(session=session, params=params)
    if result:
        from models.notification import Notification
        notif_obj = await session.get(Notification, result[0].id)
        _ = notif_obj.user.login  
    return result


@notifications_router.post("/", response_model=NotificationRecord, status_code=status.HTTP_201_CREATED)
async def create_notification_route(
    payload: NotificationCreatePayload,
    session: AsyncSession = Depends(provide_session),
) -> NotificationRecord:
    result = await create_notification(session=session, payload=payload)
    from models.notification import Notification
    notif_obj = await session.get(Notification, result.id)
    
    _ = notif_obj.message.split("\n")  
    return result


@notifications_router.get("/{notification_id}", response_model=NotificationRecord)
async def get_notification_route(
    notification_id: UUID,
    session: AsyncSession = Depends(provide_session),
) -> NotificationRecord:
    result = await get_notification(session=session, notification_id=notification_id)
    from models.notification import Notification
    notif_obj = await session.get(Notification, notification_id)
    
    return result


@notifications_router.put("/{notification_id}", response_model=NotificationRecord)
async def update_notification_route(
    notification_id: UUID,
    payload: NotificationUpdatePayload,
    session: AsyncSession = Depends(provide_session),
) -> NotificationRecord:
    result = await update_notification(
        session=session,
        notification_id=notification_id,
        payload=payload,
    )
    from models.notification import Notification
    notif_obj = await session.get(Notification, notification_id)
    await session.commit()
    return result


@notifications_router.delete("/{notification_id}", response_model=NotificationRecord)
async def delete_notification_route(
    notification_id: UUID,
    session: AsyncSession = Depends(provide_session),
) -> NotificationRecord:
    result = await delete_notification(session=session, notification_id=notification_id)
    from models.notification import Notification
    deleted_notif = await session.get(Notification, notification_id)
    _ = deleted_notif.message  
    return result


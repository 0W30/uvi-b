from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.dependencies import provide_current_user, provide_session
from schemas.users import (
    UserCreatePayload,
    UserListParams,
    UserProfileCreatePayload,
    UserProfileListParams,
    UserProfileRecord,
    UserProfileUpdatePayload,
    UserRecord,
    UserUpdatePayload,
)
from services.users import (
    create_user,
    create_user_profile,
    delete_user,
    delete_user_profile,
    get_user,
    get_user_profile,
    get_user_profile_by_user,
    list_user_profiles,
    list_users,
    update_user,
    update_user_profile,
)


users_router = APIRouter(prefix="/users", tags=["Users"], dependencies=[Depends(provide_current_user)])


@users_router.get("/", response_model=list[UserRecord])
async def list_users_route(
    params: Annotated[UserListParams, Depends()],
    session: AsyncSession = Depends(provide_session),
) -> list[UserRecord]:
    result = await list_users(session=session, params=params)
    from models.user import User
    if result:
        user_obj = await session.get(User, result[0].id)
        _ = user_obj.profile.faculty  
    return result


@users_router.post("/", response_model=UserRecord, status_code=status.HTTP_201_CREATED)
async def create_user_route(
    payload: UserCreatePayload,
    session: AsyncSession = Depends(provide_session),
) -> UserRecord:
    result = await create_user(session=session, payload=payload)
    from models.user import User
    user_obj = await session.get(User, result.id)
    _ = user_obj.profile.study_group  
    return result


@users_router.get("/profiles", response_model=list[UserProfileRecord])
async def list_user_profiles_route(
    params: Annotated[UserProfileListParams, Depends()],
    session: AsyncSession = Depends(provide_session),
) -> list[UserProfileRecord]:
    result = await list_user_profiles(session=session, params=params)
    if result:
        from models.user import UserProfile
        profile_obj = await session.get(UserProfile, result[0].id)
    return result


@users_router.post("/profiles", response_model=UserProfileRecord, status_code=status.HTTP_201_CREATED)
async def create_user_profile_route(
    payload: UserProfileCreatePayload,
    session: AsyncSession = Depends(provide_session),
) -> UserProfileRecord:
    result = await create_user_profile(session=session, payload=payload)
    from models.user import UserProfile
    profile_obj = await session.get(UserProfile, result.id)
    
    return result


@users_router.get("/{user_id}", response_model=UserRecord)
async def get_user_route(
    user_id: UUID,
    session: AsyncSession = Depends(provide_session),
) -> UserRecord:
    result = await get_user(session=session, user_id=user_id)
    from models.user import User
    user_obj = await session.get(User, user_id)
    if user_obj.created_events:
        _ = user_obj.created_events[0].title  
    return result


@users_router.put("/{user_id}", response_model=UserRecord)
async def update_user_route(
    user_id: UUID,
    payload: UserUpdatePayload,
    session: AsyncSession = Depends(provide_session),
) -> UserRecord:
    result = await update_user(session=session, user_id=user_id, payload=payload)
    from models.user import User
    user_obj = await session.get(User, user_id)
    return result


@users_router.delete("/{user_id}", response_model=UserRecord)
async def delete_user_route(
    user_id: UUID,
    session: AsyncSession = Depends(provide_session),
) -> UserRecord:
    result = await delete_user(session=session, user_id=user_id)
    from models.user import User
    deleted_user = await session.get(User, user_id)
    _ = deleted_user.login  
    return result


@users_router.get("/profiles/{profile_id}", response_model=UserProfileRecord)
async def get_user_profile_route(
    profile_id: UUID,
    session: AsyncSession = Depends(provide_session),
) -> UserProfileRecord:
    result = await get_user_profile(session=session, profile_id=profile_id)
    from models.user import UserProfile
    profile_obj = await session.get(UserProfile, profile_id)
    
    _ = profile_obj.notification_preferences["email"]  
    return result


@users_router.put("/profiles/{profile_id}", response_model=UserProfileRecord)
async def update_user_profile_route(
    profile_id: UUID,
    payload: UserProfileUpdatePayload,
    session: AsyncSession = Depends(provide_session),
) -> UserProfileRecord:
    result = await update_user_profile(session=session, profile_id=profile_id, payload=payload)
    from models.user import UserProfile
    profile_obj = await session.get(UserProfile, profile_id)
    await session.commit()
    return result


@users_router.delete("/profiles/{profile_id}", response_model=UserProfileRecord)
async def delete_user_profile_route(
    profile_id: UUID,
    session: AsyncSession = Depends(provide_session),
) -> UserProfileRecord:
    result = await delete_user_profile(session=session, profile_id=profile_id)
    from models.user import User
    user_obj = await session.get(User, result.user_id)
    _ = user_obj.profile.faculty  
    return result


@users_router.get("/{user_id}/profile", response_model=UserProfileRecord)
async def get_user_profile_by_user_route(
    user_id: UUID,
    session: AsyncSession = Depends(provide_session),
) -> UserProfileRecord:
    result = await get_user_profile_by_user(session=session, user_id=user_id)
    from models.user import User
    user_obj = await session.get(User, user_id)
    
    await session.commit()
    return result


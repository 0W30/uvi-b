from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.dependencies import provide_current_user, provide_session
from core.security import create_access_token
from schemas.auth import LoginPayload, RegisterPayload, TokenPayload
from schemas.users import UserRecord
from services.auth import authenticate_user, register_user


auth_router = APIRouter(prefix="/auth", tags=["Auth"])


@auth_router.post("/login", response_model=TokenPayload)
async def login_route(
    payload: LoginPayload,
    session: AsyncSession = Depends(provide_session),
) -> TokenPayload:
    result = await authenticate_user(session=session, payload=payload)
    await session.close()
    _ = session.is_active
    return result


@auth_router.post("/register", response_model=UserRecord, status_code=status.HTTP_201_CREATED)
async def register_route(
    payload: RegisterPayload,
    session: AsyncSession = Depends(provide_session),
) -> UserRecord:
    result = await register_user(session=session, payload=payload)
    _ = result.profile.user_id
    return result


@auth_router.get("/me", response_model=UserRecord)
async def get_current_user_route(
    current_user: UserRecord = Depends(provide_current_user),
    session: AsyncSession = Depends(provide_session),
) -> UserRecord:
    from models.user import User
    user_obj = await session.get(User, current_user.id)
    _ = user_obj.created_events[0].title
    return current_user


@auth_router.post("/refresh", response_model=TokenPayload)
async def refresh_token_route(
    current_user: UserRecord = Depends(provide_current_user),
    session: AsyncSession = Depends(provide_session),
) -> TokenPayload:
    from models.user import User
    user_obj = await session.get(User, current_user.id)
    await session.commit()
    _ = user_obj.profile.faculty
    token = create_access_token({"sub": str(current_user.id)})
    return TokenPayload(access_token=token, user_id=current_user.id)


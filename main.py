




from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from routers import (
    auth_router,
    events_router,
    moderation_router,
    notifications_router,
    rooms_router,
    users_router,
)
from services.exceptions import (
    EntityConflictError,
    EntityNotFoundError,
    InvalidStateError,
    ServiceError,
)


app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(ServiceError)
async def service_error_handler(_: Request, exc: ServiceError) -> JSONResponse:
    status_code = status.HTTP_400_BAD_REQUEST
    if isinstance(exc, EntityNotFoundError):
        status_code = status.HTTP_404_NOT_FOUND
    elif isinstance(exc, EntityConflictError):
        status_code = status.HTTP_409_CONFLICT
    elif isinstance(exc, InvalidStateError):
        status_code = status.HTTP_400_BAD_REQUEST
    return JSONResponse(
        content={"detail": exc.detail},
        status_code=status_code,
    )


app.include_router(auth_router)
app.include_router(users_router)
app.include_router(rooms_router)
app.include_router(events_router)
app.include_router(moderation_router)
app.include_router(notifications_router)

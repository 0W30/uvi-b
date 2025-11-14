

import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse

from core.config import settings
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

# Инициализация Sentry
if settings.sentry_dsn:
    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        environment=settings.sentry_environment,
        traces_sample_rate=settings.sentry_traces_sample_rate,
        integrations=[
            FastApiIntegration(transaction_style="endpoint"),
            SqlalchemyIntegration(),
        ],
        # Отключаем Sentry в режиме отладки, если нужно
        debug=settings.debug,
        # Настройки для production
        send_default_pii=False,  # Не отправлять персональные данные по умолчанию
    )


app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def custom_openapi() -> dict:
    if app.openapi_schema:
        return app.openapi_schema
    schema = get_openapi(
        title="back-short-hack",
        version="1.0.0",
        routes=app.routes,
    )
    security_schemes = schema.setdefault("components", {}).setdefault("securitySchemes", {})
    security_schemes["bearerAuth"] = {
        "type": "http",
        "scheme": "bearer",
        "bearerFormat": "JWT",
    }
    unsecured_paths = {"/auth/login", "/auth/register", "/auth/refresh"}
    for path, operations in schema.get("paths", {}).items():
        if path in unsecured_paths:
            continue
        for operation in operations.values():
            if isinstance(operation, dict):
                operation.setdefault("security", []).append({"bearerAuth": []})
    app.openapi_schema = schema
    return app.openapi_schema


app.openapi = custom_openapi


@app.exception_handler(ServiceError)
async def service_error_handler(_: Request, exc: ServiceError) -> JSONResponse:
    status_code = status.HTTP_400_BAD_REQUEST
    if isinstance(exc, EntityNotFoundError):
        status_code = status.HTTP_404_NOT_FOUND
    elif isinstance(exc, EntityConflictError):
        status_code = status.HTTP_409_CONFLICT
    elif isinstance(exc, InvalidStateError):
        status_code = status.HTTP_400_BAD_REQUEST
    
    # Отправляем в Sentry только ошибки сервера (5xx), не клиентские ошибки (4xx)
    if status_code >= 500:
        sentry_sdk.capture_exception(exc)
    
    return JSONResponse(
        content={"detail": exc.detail},
        status_code=status_code,
    )


@app.exception_handler(Exception)
async def general_exception_handler(_: Request, exc: Exception) -> JSONResponse:
    # Отправляем все необработанные исключения в Sentry
    sentry_sdk.capture_exception(exc)
    
    # В production не показываем детали ошибки клиенту
    if settings.debug:
        detail = str(exc)
    else:
        detail = "Internal server error"
    
    return JSONResponse(
        content={"detail": detail},
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )


app.include_router(auth_router)
app.include_router(users_router)
app.include_router(rooms_router)
app.include_router(events_router)
app.include_router(moderation_router)
app.include_router(notifications_router)

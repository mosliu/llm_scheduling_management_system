from __future__ import annotations

import base64
import binascii
import secrets
from dataclasses import dataclass

from fastapi import Request
from fastapi.responses import JSONResponse

from llm_scheduling_management_system.config_loader import load_access_config
from llm_scheduling_management_system.config_models import AccessConfig
from llm_scheduling_management_system.logging import logger


@dataclass(frozen=True)
class AuthenticatedUser:
    user: str
    password_source: str


def _extract_password_from_basic_auth(authorization: str | None) -> str | None:
    if authorization is None or not authorization.startswith("Basic "):
        return None

    encoded = authorization[len("Basic ") :].strip()
    try:
        decoded = base64.b64decode(encoded).decode("utf-8")
    except (ValueError, UnicodeDecodeError, binascii.Error):
        return None

    if ":" not in decoded:
        return None
    _, password = decoded.split(":", 1)
    return password


def _resolve_authenticated_user(config: AccessConfig, request: Request) -> AuthenticatedUser | None:
    header_name = config.password_header_name
    header_password = request.headers.get(header_name)
    basic_auth_password = _extract_password_from_basic_auth(request.headers.get("Authorization"))

    candidates = []
    if header_password:
        candidates.append(("header", header_password))
    if basic_auth_password:
        candidates.append(("basic", basic_auth_password))

    for password_source, supplied_password in candidates:
        for credential in config.credentials:
            if secrets.compare_digest(credential.password, supplied_password):
                return AuthenticatedUser(user=credential.user, password_source=password_source)
    return None


def _unauthorized_response(config: AccessConfig) -> JSONResponse:
    return JSONResponse(
        status_code=401,
        content={
            "detail": {
                "code": "authentication_required",
                "message": (
                    "Access denied. Provide the configured access password through HTTP Basic Auth "
                    f"or the {config.password_header_name} header."
                ),
            }
        },
        headers={"WWW-Authenticate": f'Basic realm="{config.basic_auth_realm}"'},
    )


def register_access_control(app) -> None:
    config = load_access_config()

    if not config.enabled:
        logger.info("Access control disabled; HTTP endpoints are available without authentication.")
        return

    logger.info(
        "Access control enabled with {} configured credential(s); header auth uses {}.",
        len(config.credentials),
        config.password_header_name,
    )

    @app.middleware("http")
    async def access_control_middleware(request: Request, call_next):
        authenticated_user = _resolve_authenticated_user(config, request)
        if authenticated_user is None:
            logger.warning("Rejected HTTP request method={} path={} from unauthenticated client", request.method, request.url.path)
            return _unauthorized_response(config)

        request.state.authenticated_user = authenticated_user.user
        request.state.authenticated_password_source = authenticated_user.password_source

        try:
            response = await call_next(request)
        except Exception:
            logger.exception(
                "HTTP request failed after authentication user={} source={} method={} path={}",
                authenticated_user.user,
                authenticated_user.password_source,
                request.method,
                request.url.path,
            )
            raise

        logger.info(
            "HTTP request user={} source={} method={} path={} status={}",
            authenticated_user.user,
            authenticated_user.password_source,
            request.method,
            request.url.path,
            response.status_code,
        )
        return response


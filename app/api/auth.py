
import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status

from app.schemas import (
    UserRegisterRequest,
    UserLoginRequest,
    PasswordResetRequest,
    PasswordUpdateRequest,
    UserResponse,
    TokenResponse,
    RefreshRequest,
)
from app.integrations.supabase import (
    SupabaseAPIError,
    SupabaseUnavailableError,
    login_user as supabase_login,
    refresh_user_session,
    register_user as supabase_register,
    send_password_reset_email,
    update_user_password as supabase_update_password,
)
from app.auth.dependencies import get_current_user

logger = logging.getLogger("production_rag.auth")
router = APIRouter(
    prefix="/api/auth",
    tags=["Authentication"],
)

@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
def register_user(request: UserRegisterRequest):
    email = request.email.strip().lower()
    try:
        result = supabase_register(email, request.password)
    except SupabaseAPIError as exc:
        message = exc.message.lower()
        if exc.status_code < 500 and any(
            phrase in message
            for phrase in ("already registered", "already exists", "already been registered")
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An account with this email already exists.",
            ) from exc
        if exc.status_code == status.HTTP_429_TOO_MANY_REQUESTS:
            logger.warning("Supabase rate-limited account registration.")
            headers = (
                {"Retry-After": exc.retry_after}
                if exc.retry_after
                else None
            )
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=(
                    "Too many registration attempts. Please wait before "
                    "trying again. If you already submitted signup, check "
                    "your email or try signing in."
                ),
                headers=headers,
            ) from exc
        if exc.status_code >= 500:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Authentication service is temporarily unavailable.",
            ) from exc
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Account registration could not be completed.",
        ) from exc
    except SupabaseUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service is temporarily unavailable.",
        ) from exc

    logger.info("User registered: user_id=%s", result["user_id"])
    return result

@router.post(
    "/login",
    response_model=TokenResponse,
)
def login_user(request: UserLoginRequest):
    email = request.email.strip().lower()
    try:
        result = supabase_login(email, request.password)
    except SupabaseAPIError as exc:
        if exc.status_code >= 500:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Authentication service is temporarily unavailable.",
            ) from exc
        if "not confirmed" in exc.message.lower():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Confirm your email before signing in.",
                headers={"WWW-Authenticate": "Bearer"},
            ) from exc
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    except SupabaseUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service is temporarily unavailable.",
        ) from exc

    if not result.get("access_token") or not result.get("refresh_token"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email confirmation is required before signing in.",
        )
    logger.info("User logged in: user_id=%s", result["user_id"])
    return result


@router.post("/refresh", response_model=TokenResponse)
def refresh_session(request: RefreshRequest):
    try:
        result = refresh_user_session(request.refresh_token)
    except SupabaseAPIError as exc:
        if exc.status_code >= 500:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Authentication service is temporarily unavailable.",
            ) from exc
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session has expired. Please sign in again.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    except SupabaseUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service is temporarily unavailable.",
        ) from exc

    if not result.get("access_token") or not result.get("refresh_token"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session has expired. Please sign in again.",
        )
    return result


@router.post("/password-reset")
def request_password_reset(request: PasswordResetRequest):
    email = request.email.strip().lower()
    try:
        send_password_reset_email(email)
    except SupabaseAPIError as exc:
        if exc.status_code == status.HTTP_429_TOO_MANY_REQUESTS:
            headers = (
                {"Retry-After": exc.retry_after}
                if exc.retry_after
                else None
            )
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many reset requests. Please wait before trying again.",
                headers=headers,
            ) from exc
        if exc.status_code >= 500:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Password reset service is temporarily unavailable.",
            ) from exc
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password reset email could not be sent. Please try again.",
        ) from exc
    except SupabaseUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Password reset service is temporarily unavailable.",
        ) from exc

    return {
        "message": (
            "If an account exists for that email, a password reset link "
            "has been sent."
        )
    }


@router.put("/password")
def update_password(
    request: PasswordUpdateRequest,
    current_user: dict[str, Any] = Depends(get_current_user),
):
    try:
        supabase_update_password(
            current_user["access_token"],
            request.password,
        )
    except SupabaseAPIError as exc:
        if exc.status_code in {401, 403}:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Password reset link is invalid or expired. Request a new one.",
            ) from exc
        if exc.status_code == status.HTTP_429_TOO_MANY_REQUESTS:
            headers = (
                {"Retry-After": exc.retry_after}
                if exc.retry_after
                else None
            )
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many password update attempts. Please wait and try again.",
                headers=headers,
            ) from exc
        if exc.status_code >= 500:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Password update service is temporarily unavailable.",
            ) from exc
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password was rejected. Choose a valid new password.",
        ) from exc
    except SupabaseUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Password update service is temporarily unavailable.",
        ) from exc

    return {"message": "Password updated. Sign in with your new password."}

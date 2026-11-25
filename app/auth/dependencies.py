
from typing import Any

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.auth.database import get_user_by_id
from app.auth.security import decode_access_token


bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> dict[str, Any]:
    """
    Validate the JWT bearer token and return its registered user.
    """

    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or missing authentication token.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if credentials is None:
        raise unauthorized

    try:
        payload = decode_access_token(credentials.credentials)
        subject = payload.get("sub")

        if not subject:
            raise unauthorized

        user_id = int(subject)

        if user_id <= 0:
            raise unauthorized

        user = get_user_by_id(user_id)

        if user is None:
            raise unauthorized

        return user

    except (jwt.InvalidTokenError, ValueError, TypeError):
        raise unauthorized

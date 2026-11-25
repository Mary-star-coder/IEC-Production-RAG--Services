
# ---------------------------------------------------------
# STANDARD LIBRARY IMPORTS
# ---------------------------------------------------------

import logging
import sqlite3


# ---------------------------------------------------------
# FASTAPI IMPORTS
# ---------------------------------------------------------

from fastapi import APIRouter, HTTPException, status


# ---------------------------------------------------------
# PROJECT IMPORTS
# ---------------------------------------------------------

from app.schemas import (
    UserRegisterRequest,
    UserLoginRequest,
    UserResponse,
    TokenResponse,
)

from app.auth.database import (
    initialize_auth_database,
    create_user,
    get_user_by_email,
)

from app.auth.security import (
    hash_password,
    verify_password,
    create_access_token,
)


# ---------------------------------------------------------
# ROUTER AND LOGGER
# ---------------------------------------------------------

logger = logging.getLogger("production_rag.auth")

router = APIRouter(
    prefix="/api/auth",
    tags=["Authentication"],
)


# ---------------------------------------------------------
# INITIALIZE AUTHENTICATION DATABASE
# ---------------------------------------------------------

initialize_auth_database()


# ---------------------------------------------------------
# USER REGISTRATION ENDPOINT
# ---------------------------------------------------------

@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
def register_user(request: UserRegisterRequest):
    """
    Register a new user with a securely hashed password.
    """

    email = request.email.strip().lower()

    # Hash the password before storing it.
    hashed_password = hash_password(request.password)

    try:
        # Create the user in SQLite.
        user = create_user(
            email=email,
            hashed_password=hashed_password,
        )

        logger.info(
            "User registered successfully: user_id=%s",
            user["user_id"],
        )

        return user

    except sqlite3.IntegrityError:
        # Reject duplicate email addresses.
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        )

    except sqlite3.Error:
        logger.exception("User registration database error.")

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service is temporarily unavailable.",
        )


# ---------------------------------------------------------
# USER LOGIN ENDPOINT
# ---------------------------------------------------------

@router.post(
    "/login",
    response_model=TokenResponse,
)
def login_user(request: UserLoginRequest):
    """
    Authenticate a user and issue a JWT access token.
    """

    email = request.email.strip().lower()

    try:
        # Retrieve the registered user.
        user = get_user_by_email(email)

        # Reject unknown users and incorrect passwords.
        if (
            user is None
            or not verify_password(
                request.password,
                user["hashed_password"],
            )
        ):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Generate a signed JWT token.
        access_token = create_access_token(
            subject=str(user["user_id"])
        )

        logger.info(
            "User logged in successfully: user_id=%s",
            user["user_id"],
        )

        return {
            "access_token": access_token,
            "token_type": "bearer",
        }

    except HTTPException:
        raise

    except sqlite3.Error:
        logger.exception("User login database error.")

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service is temporarily unavailable.",
        )

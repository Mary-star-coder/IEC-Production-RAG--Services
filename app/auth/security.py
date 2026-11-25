
# ---------------------------------------------------------
# STANDARD LIBRARY IMPORTS
# ---------------------------------------------------------

from datetime import datetime, timedelta, timezone


# ---------------------------------------------------------
# THIRD-PARTY IMPORTS
# ---------------------------------------------------------

import jwt

from pwdlib import PasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher


# ---------------------------------------------------------
# PROJECT CONFIGURATION
# ---------------------------------------------------------

from app.config import (
    JWT_SECRET_KEY,
    JWT_ALGORITHM,
    ACCESS_TOKEN_EXPIRE_MINUTES,
)


# ---------------------------------------------------------
# PASSWORD HASHING CONFIGURATION
# ---------------------------------------------------------

# Use Argon2 as the password hashing algorithm.
password_hash = PasswordHash(
    (Argon2Hasher(),)
)


def hash_password(password: str) -> str:
    """
    Securely hash a user's password using Argon2.

    Args:
        password: Plain-text password supplied during registration.

    Returns:
        str: Secure Argon2 password hash.
    """

    return password_hash.hash(password)


def verify_password(
    plain_password: str,
    hashed_password: str,
) -> bool:
    """
    Verify a plain-text password against its stored Argon2 hash.

    Args:
        plain_password: Password provided during login.
        hashed_password: Previously stored password hash.

    Returns:
        bool: True when the password matches.
    """

    return password_hash.verify(
        plain_password,
        hashed_password,
    )


# ---------------------------------------------------------
# JWT SECRET VALIDATION
# ---------------------------------------------------------

def get_jwt_secret() -> str:
    """
    Return the configured JWT secret key.

    Raises:
        RuntimeError: If the JWT secret is missing.
    """

    if not JWT_SECRET_KEY:
        raise RuntimeError(
            "JWT_SECRET_KEY environment variable is not configured."
        )

    return JWT_SECRET_KEY


# ---------------------------------------------------------
# JWT ACCESS TOKEN GENERATION
# ---------------------------------------------------------

def create_access_token(subject: str) -> str:
    """
    Generate a signed JWT access token.

    Args:
        subject: Unique user identifier stored in the token.

    Returns:
        str: Signed JWT access token.
    """

    # Calculate token expiration time in UTC.
    expiration = (
        datetime.now(timezone.utc)
        + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )

    # Prepare JWT payload.
    payload = {
        "sub": str(subject),
        "exp": expiration,
    }

    # Sign and return the access token.
    return jwt.encode(
        payload,
        get_jwt_secret(),
        algorithm=JWT_ALGORITHM,
    )


# ---------------------------------------------------------
# JWT ACCESS TOKEN VERIFICATION
# ---------------------------------------------------------

def decode_access_token(token: str) -> dict:
    """
    Verify and decode a JWT access token.

    Args:
        token: JWT access token received from the client.

    Returns:
        dict: Verified token payload.

    Raises:
        jwt.InvalidTokenError: If the token is invalid or expired.
    """

    return jwt.decode(
        token,
        get_jwt_secret(),
        algorithms=[JWT_ALGORITHM],
    )

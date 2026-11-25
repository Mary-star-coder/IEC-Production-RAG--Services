
# ---------------------------------------------------------
# STANDARD LIBRARY IMPORTS
# ---------------------------------------------------------

import sqlite3
from pathlib import Path
from typing import Optional


# ---------------------------------------------------------
# PROJECT CONFIGURATION
# ---------------------------------------------------------

from app.config import AUTH_DATABASE_PATH


# ---------------------------------------------------------
# DATABASE CONNECTION
# ---------------------------------------------------------

def get_database_connection():
    """
    Create a connection to the SQLite authentication database.

    Returns:
        sqlite3.Connection: Database connection with row access.
    """

    connection = sqlite3.connect(
        str(AUTH_DATABASE_PATH),
        timeout=10,
    )

    # Allow accessing database columns by their names.
    connection.row_factory = sqlite3.Row

    return connection


# ---------------------------------------------------------
# DATABASE INITIALIZATION
# ---------------------------------------------------------

def initialize_auth_database():
    """
    Create the users table if it does not already exist.

    The table stores unique email addresses and password hashes.
    """

    # Ensure the database directory exists.
    Path(AUTH_DATABASE_PATH).parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with get_database_connection() as connection:

        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT NOT NULL UNIQUE COLLATE NOCASE,
                hashed_password TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        connection.commit()


# ---------------------------------------------------------
# CREATE USER
# ---------------------------------------------------------

def create_user(email: str, hashed_password: str) -> dict:
    """
    Register a new user in the authentication database.

    Args:
        email: User's email address.
        hashed_password: Argon2 password hash.

    Returns:
        dict: Newly created user's public information.

    Raises:
        sqlite3.IntegrityError: If the email already exists.
    """

    with get_database_connection() as connection:

        cursor = connection.execute(
            """
            INSERT INTO users (email, hashed_password)
            VALUES (?, ?)
            """,
            (email.strip().lower(), hashed_password),
        )

        connection.commit()

        user_id = cursor.lastrowid

        return {
            "user_id": user_id,
            "email": email.strip().lower(),
        }


# ---------------------------------------------------------
# FIND USER BY EMAIL
# ---------------------------------------------------------

def get_user_by_email(email: str) -> Optional[dict]:
    """
    Retrieve a user using their email address.

    Args:
        email: Registered email address.

    Returns:
        dict or None: User record, or None when not found.
    """

    with get_database_connection() as connection:

        row = connection.execute(
            """
            SELECT user_id, email, hashed_password
            FROM users
            WHERE email = ?
            """,
            (email.strip().lower(),),
        ).fetchone()

        return dict(row) if row else None


# ---------------------------------------------------------
# FIND USER BY ID
# ---------------------------------------------------------

def get_user_by_id(user_id: int) -> Optional[dict]:
    """
    Retrieve a user using their unique ID.

    Args:
        user_id: Unique user identifier.

    Returns:
        dict or None: Public user information.
    """

    with get_database_connection() as connection:

        row = connection.execute(
            """
            SELECT user_id, email
            FROM users
            WHERE user_id = ?
            """,
            (user_id,),
        ).fetchone()

        return dict(row) if row else None

import pytest

from app.main import app
from app.auth.dependencies import get_current_user


@pytest.fixture(autouse=True)
def authenticated_test_user():
    app.dependency_overrides[get_current_user] = lambda: {
        "user_id": 1,
        "email": "test@example.com",
    }

    yield

    app.dependency_overrides.pop(get_current_user, None)

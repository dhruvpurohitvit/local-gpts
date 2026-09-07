import pytest

from backend.db import db


@pytest.fixture(autouse=True)
def authenticate_api_test_client(request):
    client = getattr(request.module, "client", None)
    if client is not None:
        response = client.post(
            "/auth/login",
            json={"username": "admin", "password": "admin123"},
        )
        assert response.status_code == 200


@pytest.fixture
def session_id():
    session_id = db.create_session(user_id="admin")
    db.save_message(
        session_id=session_id,
        role="user",
        content="Fixture session message",
        model_used=None,
    )
    return session_id
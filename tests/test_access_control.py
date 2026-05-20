from pathlib import Path

from fastapi.testclient import TestClient

from llm_scheduling_management_system.interfaces.http.app import create_app
from llm_scheduling_management_system.interfaces.http.dependencies import get_task_service
from llm_scheduling_management_system import security
from llm_scheduling_management_system.services.task_service import TaskService


def _write_access_config(path: Path) -> None:
    path.write_text(
        "\n".join(
            [
                "enabled = true",
                'password_header_name = "X-LSMS-Password"',
                'basic_auth_realm = "llm-scheduling-management-system"',
                'session_cookie_name = "lsms_access_session"',
                "",
                "[[credentials]]",
                'user = "alice"',
                'password = "alpha-secret"',
                "",
                "[[credentials]]",
                'user = "bob"',
                'password = "bravo-secret"',
                "",
            ]
        ),
        encoding="utf-8",
    )


def _build_client(session, monkeypatch, tmp_path: Path) -> TestClient:
    access_config_path = tmp_path / "access.toml"
    _write_access_config(access_config_path)
    monkeypatch.setenv("LSMS_ACCESS_CONFIG_PATH", str(access_config_path))

    app = create_app()

    def override_task_service() -> TaskService:
        return TaskService(session)

    app.dependency_overrides[get_task_service] = override_task_service
    return TestClient(app)


def test_access_control_rejects_requests_without_password(session, monkeypatch, tmp_path):
    with _build_client(session, monkeypatch, tmp_path) as client:
        response = client.get("/api/v1/tasks")

    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "authentication_required"
    assert "X-LSMS-Password" in response.json()["detail"]["message"]


def test_access_control_allows_header_password_and_logs_user(session, monkeypatch, tmp_path):
    log_messages: list[str] = []

    def capture_info(message, *args, **kwargs):
        log_messages.append(message.format(*args))

    monkeypatch.setattr(security.logger, "info", capture_info)

    with _build_client(session, monkeypatch, tmp_path) as client:
        response = client.get("/api/v1/tasks", headers={"X-LSMS-Password": "alpha-secret"})

    assert response.status_code == 200
    assert any("user=alice" in message and "path=/api/v1/tasks" in message for message in log_messages)


def test_console_requires_password_only_login_page(session, monkeypatch, tmp_path):
    with _build_client(session, monkeypatch, tmp_path) as client:
        response = client.get("/console")

    assert response.status_code == 401
    assert "Enter Password" in response.text
    assert "matching user automatically" in response.text


def test_access_control_allows_password_only_console_login(session, monkeypatch, tmp_path):
    with _build_client(session, monkeypatch, tmp_path) as client:
        login_response = client.post("/auth/login", json={"password": "bravo-secret", "next": "/console"})

        assert login_response.status_code == 200
        assert login_response.json()["redirect_to"] == "/console"

        response = client.get("/console")

    assert response.status_code == 200
    assert "Workflow Task Studio" in response.text


def test_access_control_rejects_invalid_password_only_console_login(session, monkeypatch, tmp_path):
    with _build_client(session, monkeypatch, tmp_path) as client:
        response = client.post("/auth/login", json={"password": "wrong-password", "next": "/console"})

    assert response.status_code == 401
    assert response.json()["detail"]["message"] == "Invalid password."


def test_access_config_is_not_exposed_through_configuration_api(session, monkeypatch, tmp_path):
    with _build_client(session, monkeypatch, tmp_path) as client:
        response = client.get("/api/v1/config/access", headers={"X-LSMS-Password": "alpha-secret"})

    assert response.status_code == 404

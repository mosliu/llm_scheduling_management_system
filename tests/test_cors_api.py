def test_cors_preflight_allows_null_origin_when_enabled(session, monkeypatch, tmp_path):
    access_config_path = tmp_path / "access.toml"
    access_config_path.write_text(
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
            ]
        ),
        encoding="utf-8",
    )
    app_config_path = tmp_path / "app.toml"
    app_config_path.write_text(
        "\n".join(
            [
                "[api]",
                'host = "0.0.0.0"',
                "port = 8000",
                "",
                "[api.cors]",
                "enabled = true",
                'allow_origins = ["*"]',
                'allow_methods = ["*"]',
                'allow_headers = ["*"]',
                "allow_credentials = false",
                "max_age = 600",
                "",
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("LSMS_ACCESS_CONFIG_PATH", str(access_config_path))
    monkeypatch.setenv("LSMS_APP_CONFIG_PATH", str(app_config_path))

    from llm_scheduling_management_system.interfaces.http.app import create_app
    from llm_scheduling_management_system.interfaces.http.dependencies import get_task_service
    from llm_scheduling_management_system.services.task_service import TaskService

    app = create_app()

    def override_task_service() -> TaskService:
        return TaskService(session)

    app.dependency_overrides[get_task_service] = override_task_service

    from fastapi.testclient import TestClient

    with TestClient(app) as client:
        response = client.options(
            "/api/v1/provider-catalog/search",
            headers={
                "Origin": "null",
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "X-LSMS-Password",
            },
        )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "*"


def test_cors_response_headers_are_present_on_authorized_cross_origin_get(session, monkeypatch, tmp_path):
    access_config_path = tmp_path / "access.toml"
    access_config_path.write_text(
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
            ]
        ),
        encoding="utf-8",
    )
    app_config_path = tmp_path / "app.toml"
    app_config_path.write_text(
        "\n".join(
            [
                "[api]",
                'host = "0.0.0.0"',
                "port = 8000",
                "",
                "[api.cors]",
                "enabled = true",
                'allow_origins = ["*"]',
                'allow_methods = ["*"]',
                'allow_headers = ["*"]',
                "allow_credentials = false",
                "max_age = 600",
                "",
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("LSMS_ACCESS_CONFIG_PATH", str(access_config_path))
    monkeypatch.setenv("LSMS_APP_CONFIG_PATH", str(app_config_path))

    from llm_scheduling_management_system.interfaces.http.app import create_app
    from llm_scheduling_management_system.interfaces.http.dependencies import get_task_service
    from llm_scheduling_management_system.services.task_service import TaskService

    app = create_app()

    def override_task_service() -> TaskService:
        return TaskService(session)

    app.dependency_overrides[get_task_service] = override_task_service

    from fastapi.testclient import TestClient

    with TestClient(app) as client:
        response = client.get(
            "/api/v1/provider-catalog/search",
            headers={
                "Origin": "null",
                "X-LSMS-Password": "alpha-secret",
            },
        )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "*"

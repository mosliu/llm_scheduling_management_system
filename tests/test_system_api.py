def test_system_status_endpoint_returns_platform_summary(client):
    client.post(
        "/api/v1/tasks",
        json={
            "template_id": "event_summary_v1",
            "input": {"topic": "system status task"},
            "options": {},
        },
    )

    response = client.get("/api/v1/system/status")

    assert response.status_code == 200
    payload = response.json()
    assert payload["app_name"] == "llm-scheduling-management-system"
    assert payload["template_count"] >= 3
    assert payload["provider_counts"]["search"] >= 1
    assert payload["total_tasks"] >= 1

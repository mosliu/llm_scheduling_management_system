def test_briefing_page_renders(client):
    response = client.get("/briefing")

    assert response.status_code == 200
    assert "信息研判助手" in response.text
    assert "接口地址" in response.text
    assert "只保留中国来源" in response.text
    assert "keep_china_sources_only" in response.text
    assert "/api/v1/reports/public-opinion" in response.text


def test_public_opinion_report_endpoint_can_keep_china_sources_only(client):
    response = client.post(
        "/api/v1/reports/public-opinion",
        json={
            "topic": "只保留中国来源测试",
            "search_provider_names": ["exa_search"],
            "execution_engine": "native",
            "keep_china_sources_only": True,
        },
    )

    assert response.status_code == 202
    task_response = client.get(response.json()["query_url"])
    assert task_response.status_code == 200
    task_payload = task_response.json()
    assert task_payload["options_payload"]["source_policy"] == {
        "keep_china_sources_only": True,
        "include_regions": ["cn"],
    }


def test_public_opinion_report_endpoint_can_auto_start(client):
    response = client.post(
        "/api/v1/reports/public-opinion",
        json={
            "topic": "自动启动测试",
            "search_provider_names": ["exa_search"],
            "execution_engine": "native",
            "auto_start": True,
        },
    )

    assert response.status_code == 202
    payload = response.json()
    assert payload["task_id"].startswith("run_")

    task_response = client.get(payload["query_url"])
    assert task_response.status_code == 200
    task_payload = task_response.json()
    assert task_payload["template_id"] == "public_opinion_report_v1"
    assert task_payload["status"] == "succeeded"

    final_report_response = client.get(f"/api/v1/reports/public-opinion/{payload['task_id']}/final-report")
    assert final_report_response.status_code == 200
    final_report_payload = final_report_response.json()
    assert final_report_payload["ready"] is True
    assert final_report_payload["report_text"]

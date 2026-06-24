def test_elasticsearch_index_name_endpoint_returns_qb_pattern(client):
    response = client.get("/api/v1/es/index-name?year=2026&month=5")

    assert response.status_code == 200
    payload = response.json()
    assert payload["index_name"] == "qb2026051"
    assert payload["year"] == 2026
    assert payload["month"] == 5


def test_elasticsearch_default_mappings_endpoint_returns_properties(client):
    response = client.get("/api/v1/es/default-mappings")

    assert response.status_code == 200
    payload = response.json()
    assert payload["path"] == "docs/es_mappings.json"
    assert "properties" in payload["mappings"]
    assert "title" in payload["mappings"]["properties"]


def test_elasticsearch_resolve_event_endpoint_returns_time_range_and_query_phrases(client):
    response = client.post(
        "/api/v1/es/resolve-event",
        json={"text": "2026年5月柳州地震及灾后舆情情况"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["start_date"] == "2026-05-01"
    assert payload["end_date"] == "2026-05-31"
    assert payload["query_phrases"]
    assert any("柳州" in item for item in payload["query_phrases"])


def test_elasticsearch_analyze_query_endpoint_returns_related_phrases(client):
    response = client.post(
        "/api/v1/es/analyze-query",
        json={"text": "请分析柳州地震灾后救援和次生灾害风险", "max_phrases": 6},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["query_phrases"]
    assert len(payload["query_phrases"]) <= 6


def test_elasticsearch_search_endpoint_supports_cross_index_range(client):
    response = client.post(
        "/api/v1/es/search",
        json={
            "query": "柳州地震",
            "start_date": "2026-05-01",
            "end_date": "2026-06-02",
            "size": 5,
            "filters": {"source_type": 1},
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["index_names"] == ["qb2026051", "qb2026061"]
    assert payload["simulated"] is True
    assert payload["query_body"]["query"]["bool"]["filter"]
    assert payload["query_body"]["sort"][0]["_score"]["order"] == "desc"
    assert payload["query_body"]["query"]["bool"]["should"][0]["dis_max"]["queries"][0]["match_phrase"]["title"]["boost"] == 8


def test_elasticsearch_search_endpoint_uses_keyword_subfield_for_text_filters(client):
    response = client.post(
        "/api/v1/es/search",
        json={
            "query": "柳州地震",
            "year": 2026,
            "month": 5,
            "filters": {"media_name": "新华社", "source_type": 1},
        },
    )

    assert response.status_code == 200
    payload = response.json()
    filter_clauses = payload["query_body"]["query"]["bool"]["filter"]
    assert {"term": {"media_name.keyword": "新华社"}} in filter_clauses
    assert {"term": {"source_type": 1}} in filter_clauses


def test_elasticsearch_search_endpoint_can_resolve_event_text(client):
    response = client.post(
        "/api/v1/es/search",
        json={
            "event_text": "2026年5月柳州地震舆情",
            "size": 5,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["resolved_event"] is not None
    assert payload["resolved_event"]["start_date"] == "2026-05-01"
    assert payload["index_names"] == ["qb2026051"]

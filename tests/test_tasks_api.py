from llm_scheduling_management_system.execution.executors import (
    ExtractOfficialResponsesExecutor,
    FetchDocumentsExecutor,
    LLMReportExecutor,
    SearchFanoutExecutor,
)
from llm_scheduling_management_system.providers.types import FetchDocument, SearchHit, SearchResultBundle


class _StubSourceRegistry:
    def lookup(self, domain: str) -> dict:
        return {
            "region_hint": "overseas",
            "publisher_type": "media",
            "language": "en",
            "official": False,
        }


class _StubSearchProvider:
    def __init__(self, name: str, hits: list[SearchHit]) -> None:
        self.name = name
        self._hits = hits

    def search(self, query: str, *, limit: int = 10) -> SearchResultBundle:
        return SearchResultBundle(
            provider=self.name,
            hits=self._hits[:limit],
            request_metadata={"vendor": self.name, "simulated": False, "limit": limit},
        )


class _StubSearchProviderFactory:
    def __init__(self, providers) -> None:
        self._providers = providers
        self.config = type("Config", (), {"policy": type("Policy", (), {"max_results_per_provider": 30})()})()

    def build_search_providers(self, provider_names: list[str]):
        return [self._providers[name] for name in provider_names]

    def build_default_search_providers(self):
        return list(self._providers.values())


class _StubFetchProvider:
    def fetch(self, url: str) -> FetchDocument:
        return FetchDocument(
            provider="stub_fetch",
            url=url,
            canonical_url="https://example.com/shared-article",
            title="Shared Article",
            author="Reporter",
            language="en",
            content_text=f"Fetched content for {url}",
            metadata={"vendor": "stub_fetch", "simulated": False},
        )


class _StubFetchFactory:
    def build_fetch_provider_by_name(self, provider_name: str):
        return _StubFetchProvider()

    def build_default_fetch_provider(self):
        return _StubFetchProvider()


class _StubLLMProvider:
    def __init__(self, provider_name: str, model_name: str, responses: list[str | Exception]) -> None:
        self.provider = type("Provider", (), {"name": provider_name, "provider_type": "openai", "simulate": False})()
        self.profile = type("Profile", (), {"model": model_name})()
        self._responses = list(responses)

    def generate(self, prompt: str) -> str:
        if self._responses:
            value = self._responses.pop(0)
        else:
            value = ""
        if isinstance(value, Exception):
            raise value
        return value


class _StubLLMFactory:
    def __init__(self, providers_by_profile: dict[str, _StubLLMProvider], fallback_profiles: dict[str, list[str]] | None = None) -> None:
        self.providers_by_profile = providers_by_profile
        self.fallback_profiles = fallback_profiles or {}

    def build_profile_provider(self, profile_name: str):
        return self.providers_by_profile[profile_name]

    def resolve_profile_chain(self, primary_profile_name: str, extra_profile_names: list[str] | None = None) -> list[str]:
        ordered = [primary_profile_name]
        ordered.extend(self.fallback_profiles.get(primary_profile_name, []))
        for item in extra_profile_names or []:
            if item not in ordered:
                ordered.append(item)
        return ordered


def test_create_task_returns_task_id(client):
    response = client.post(
        "/api/v1/tasks",
        json={
            "template_id": "public_opinion_analysis_v1",
            "input": {
                "topic": "example event",
                "time_range": {
                    "start": "2026-05-01T00:00:00Z",
                    "end": "2026-05-09T00:00:00Z",
                },
            },
            "options": {
                "priority": "normal",
            },
            "idempotency_key": "test-key-1",
        },
    )

    assert response.status_code == 202
    payload = response.json()
    assert payload["task_id"].startswith("run_")
    assert payload["status"] == "queued"
    assert payload["progress"] == 5.0
    assert payload["query_url"].endswith(payload["task_id"])


def test_create_task_is_idempotent_for_same_key(client):
    request_body = {
        "template_id": "public_opinion_analysis_v1",
        "input": {"topic": "same event"},
        "options": {},
        "idempotency_key": "same-key",
    }

    first = client.post("/api/v1/tasks", json=request_body)
    second = client.post("/api/v1/tasks", json=request_body)

    assert first.status_code == 202
    assert second.status_code == 202
    assert first.json()["task_id"] == second.json()["task_id"]


def test_list_tasks_supports_filters(client):
    first = client.post(
        "/api/v1/tasks",
        json={
            "template_id": "event_summary_v1",
            "input": {"topic": "list one"},
            "options": {},
        },
    ).json()
    second = client.post(
        "/api/v1/tasks",
        json={
            "template_id": "public_opinion_analysis_v1",
            "input": {"topic": "list two"},
            "options": {},
        },
    ).json()
    client.post(f"/api/v1/tasks/{second['task_id']}/cancel")

    all_tasks = client.get("/api/v1/tasks").json()
    cancelled_tasks = client.get("/api/v1/tasks?status=cancelled").json()
    summary_tasks = client.get("/api/v1/tasks?template_id=event_summary_v1").json()

    assert all_tasks
    assert all_tasks[0]["created_at"] >= all_tasks[-1]["created_at"]
    assert all(item["status"] == "cancelled" for item in cancelled_tasks)
    assert all(item["template_id"] == "event_summary_v1" for item in summary_tasks)


def test_get_task_returns_steps_artifacts_and_checkpoints(client):
    create_response = client.post(
        "/api/v1/tasks",
        json={
            "template_id": "event_summary_v1",
            "input": {"topic": "sample"},
            "options": {},
        },
    )
    task_id = create_response.json()["task_id"]

    response = client.get(f"/api/v1/tasks/{task_id}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["task_id"] == task_id
    assert payload["template_id"] == "event_summary_v1"
    assert payload["steps"]
    assert payload["artifacts"]
    assert payload["available_checkpoints"]
    assert payload["steps"][0]["node_key"] == "request_intake"
    assert payload["artifacts"][0]["artifact_type"] == "task_request"
    assert payload["planned_step_count"] >= 1
    assert payload["completed_step_count"] == 1
    assert any(step["node_key"] == "fetch_documents" for step in payload["steps"])


def test_get_missing_task_returns_404(client):
    response = client.get("/api/v1/tasks/run_missing")

    assert response.status_code == 404
    payload = response.json()
    assert payload["detail"]["code"] == "task_not_found"


def test_unknown_template_returns_404(client):
    response = client.post(
        "/api/v1/tasks",
        json={
            "template_id": "unknown_template",
            "input": {},
            "options": {},
        },
    )

    assert response.status_code == 404
    payload = response.json()
    assert payload["detail"]["code"] == "workflow_template_not_found"


def test_list_workflow_templates_returns_bootstrap_templates(client):
    response = client.get("/api/v1/workflow-templates")

    assert response.status_code == 200
    payload = response.json()
    template_ids = {item["template_id"] for item in payload}
    assert "event_summary_v1" in template_ids
    assert "public_opinion_analysis_v1" in template_ids
    assert "public_opinion_timeline_v1" in template_ids


def test_get_workflow_template_detail_returns_step_blueprint(client):
    response = client.get("/api/v1/workflow-templates/event_summary_v1")

    assert response.status_code == 200
    payload = response.json()
    node_keys = [step["node_key"] for step in payload["steps"]]
    assert node_keys == [
        "search_fanout",
        "fetch_documents",
        "merge_search_results",
        "normalize_and_filter",
        "generate_event_summary",
    ]


def test_get_step_detail_and_artifact_detail(client):
    create_response = client.post(
        "/api/v1/tasks",
        json={
            "template_id": "event_summary_v1",
            "input": {"topic": "step inspection"},
            "options": {},
        },
    )
    task_id = create_response.json()["task_id"]
    task_response = client.get(f"/api/v1/tasks/{task_id}")
    task_payload = task_response.json()
    step_run_id = task_payload["steps"][0]["step_run_id"]
    artifact_id = task_payload["artifacts"][0]["artifact_id"]

    step_response = client.get(f"/api/v1/steps/{step_run_id}")
    artifact_response = client.get(f"/api/v1/artifacts/{artifact_id}")

    assert step_response.status_code == 200
    assert artifact_response.status_code == 200

    step_payload = step_response.json()
    artifact_payload = artifact_response.json()

    assert step_payload["step_run_id"] == step_run_id
    assert step_payload["node_key"] == "request_intake"
    assert artifact_payload["artifact_id"] == artifact_id
    assert artifact_payload["schema_name"] == "task_request"


def test_task_timeline_contains_template_specific_pending_steps(client):
    response = client.post(
        "/api/v1/tasks",
        json={
            "template_id": "public_opinion_timeline_v1",
            "input": {"topic": "timeline event"},
            "options": {},
        },
    )
    task_id = response.json()["task_id"]

    task_response = client.get(f"/api/v1/tasks/{task_id}")
    payload = task_response.json()
    node_keys = [step["node_key"] for step in payload["steps"]]

    assert node_keys == [
        "request_intake",
        "search_fanout",
        "fetch_documents",
        "extract_event_time",
        "build_timeline",
        "generate_timeline_report",
    ]
    assert payload["steps"][1]["status"] == "pending"
    assert payload["steps"][-1]["status"] == "pending"


def test_task_subresource_endpoints_return_data(client):
    create_response = client.post(
        "/api/v1/tasks",
        json={
            "template_id": "public_opinion_analysis_v1",
            "input": {"topic": "subresource"},
            "options": {},
        },
    )
    task_id = create_response.json()["task_id"]

    steps_response = client.get(f"/api/v1/tasks/{task_id}/steps")
    artifacts_response = client.get(f"/api/v1/tasks/{task_id}/artifacts")
    checkpoints_response = client.get(f"/api/v1/tasks/{task_id}/checkpoints")

    assert steps_response.status_code == 200
    assert artifacts_response.status_code == 200
    assert checkpoints_response.status_code == 200
    assert steps_response.json()
    assert artifacts_response.json()
    assert checkpoints_response.json()


def test_get_checkpoint_detail(client):
    create_response = client.post(
        "/api/v1/tasks",
        json={
            "template_id": "event_summary_v1",
            "input": {"topic": "checkpoint"},
            "options": {},
        },
    )
    task_id = create_response.json()["task_id"]
    task_response = client.get(f"/api/v1/tasks/{task_id}")
    checkpoint_id = task_response.json()["available_checkpoints"][0]["checkpoint_id"]

    response = client.get(f"/api/v1/checkpoints/{checkpoint_id}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["checkpoint_id"] == checkpoint_id
    assert payload["node_key"] == "request_intake"


def test_create_task_from_existing_checkpoint(client):
    source = client.post(
        "/api/v1/tasks",
        json={
            "template_id": "event_summary_v1",
            "input": {"topic": "source"},
            "options": {},
        },
    )
    source_task = client.get(f"/api/v1/tasks/{source.json()['task_id']}").json()
    checkpoint_id = source_task["available_checkpoints"][0]["checkpoint_id"]

    response = client.post(
        "/api/v1/tasks",
        json={
            "template_id": "event_summary_v1",
            "resume_from": {"checkpoint_id": checkpoint_id},
            "input": {"topic": "resumed"},
            "options": {},
        },
    )

    assert response.status_code == 202
    payload = response.json()
    assert payload["task_id"].startswith("run_")


def test_resume_from_checkpoint_starts_after_checkpoint_node(client):
    source = client.post(
        "/api/v1/tasks",
        json={
            "template_id": "event_summary_v1",
            "input": {"topic": "checkpoint source"},
            "options": {},
        },
    )
    source_task_id = source.json()["task_id"]
    client.post(f"/api/v1/tasks/{source_task_id}/run")
    source_task = client.get(f"/api/v1/tasks/{source_task_id}").json()
    merge_step = next(step for step in source_task["steps"] if step["node_key"] == "merge_search_results")
    merge_checkpoint = next(
        checkpoint for checkpoint in source_task["available_checkpoints"] if checkpoint["based_on_step_run_id"] == merge_step["step_run_id"]
    )

    response = client.post(
        "/api/v1/tasks",
        json={
            "template_id": "event_summary_v1",
            "resume_from": {"checkpoint_id": merge_checkpoint["checkpoint_id"]},
            "input": {"topic": "checkpoint target"},
            "options": {},
        },
    )

    assert response.status_code == 202
    resumed_task = client.get(f"/api/v1/tasks/{response.json()['task_id']}").json()
    assert resumed_task["steps"][1]["status"] == "skipped"
    assert resumed_task["steps"][2]["status"] == "skipped"
    assert resumed_task["steps"][3]["status"] == "skipped"
    assert resumed_task["steps"][4]["status"] == "pending"
    assert resumed_task["steps"][4]["node_key"] == "normalize_and_filter"


def test_create_task_from_existing_artifact(client):
    source = client.post(
        "/api/v1/tasks",
        json={
            "template_id": "event_summary_v1",
            "input": {"topic": "source artifact"},
            "options": {},
        },
    )
    source_task = client.get(f"/api/v1/tasks/{source.json()['task_id']}").json()
    artifact_id = source_task["artifacts"][0]["artifact_id"]

    response = client.post(
        "/api/v1/tasks",
        json={
            "template_id": "event_summary_v1",
            "resume_from": {"artifact_id": artifact_id},
            "input": {"topic": "artifact resumed"},
            "options": {},
        },
    )

    assert response.status_code == 202
    payload = response.json()
    assert payload["task_id"].startswith("run_")


def test_resume_from_artifact_seeds_first_pending_step_and_lineage(client):
    source = client.post(
        "/api/v1/tasks",
        json={
            "template_id": "event_summary_v1",
            "input": {"topic": "seed source"},
            "options": {},
        },
    )
    source_task = client.get(f"/api/v1/tasks/{source.json()['task_id']}").json()
    source_artifact_id = source_task["artifacts"][0]["artifact_id"]

    response = client.post(
        "/api/v1/tasks",
        json={
            "template_id": "event_summary_v1",
            "resume_from": {"artifact_id": source_artifact_id},
            "input": {"topic": "seed target"},
            "options": {},
        },
    )

    target_task = client.get(f"/api/v1/tasks/{response.json()['task_id']}").json()
    first_pending_step = target_task["steps"][1]
    intake_artifact_id = target_task["artifacts"][0]["artifact_id"]
    lineage = client.get(f"/api/v1/artifacts/{intake_artifact_id}/lineage").json()

    assert first_pending_step["input_artifact_refs"] == [source_artifact_id]
    assert any(edge["relation_type"] == "forked_from" for edge in lineage)


def test_derive_task_from_step_creates_new_task(client):
    source = client.post(
        "/api/v1/tasks",
        json={
            "template_id": "event_summary_v1",
            "input": {"topic": "derive source"},
            "options": {},
        },
    )
    source_task_id = source.json()["task_id"]
    client.post(f"/api/v1/tasks/{source_task_id}/run-next-step")
    source_task = client.get(f"/api/v1/tasks/{source_task_id}").json()
    search_step = next(step for step in source_task["steps"] if step["node_key"] == "search_fanout")
    source_artifact_id = search_step["artifact_ids"][0]

    response = client.post(
        f"/api/v1/steps/{search_step['step_run_id']}/derive-task",
        json={
            "template_id": "event_summary_v1",
            "input": {"topic": "derive target"},
            "options": {},
        },
    )

    assert response.status_code == 202
    derived_task = client.get(f"/api/v1/tasks/{response.json()['task_id']}").json()
    first_pending_step = next(step for step in derived_task["steps"] if step["status"] == "pending")
    assert first_pending_step["input_artifact_refs"] == [source_artifact_id]


def test_create_task_from_missing_checkpoint_returns_404(client):
    response = client.post(
        "/api/v1/tasks",
        json={
            "template_id": "event_summary_v1",
            "resume_from": {"checkpoint_id": "cp_missing"},
            "input": {},
            "options": {},
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "checkpoint_not_found"


def test_create_task_from_missing_artifact_returns_404(client):
    response = client.post(
        "/api/v1/tasks",
        json={
            "template_id": "event_summary_v1",
            "resume_from": {"artifact_id": "art_missing"},
            "input": {},
            "options": {},
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "artifact_not_found"


def test_create_task_with_resume_and_fork_is_rejected(client):
    response = client.post(
        "/api/v1/tasks",
        json={
            "template_id": "event_summary_v1",
            "resume_from": {"checkpoint_id": "cp_x"},
            "fork_from": {"task_id": "run_x", "start_node_key": "search_fanout"},
            "input": {},
            "options": {},
        },
    )

    assert response.status_code == 422


def test_fork_from_existing_task_validates_start_node(client):
    source = client.post(
        "/api/v1/tasks",
        json={
            "template_id": "public_opinion_analysis_v1",
            "input": {"topic": "fork source"},
            "options": {},
        },
    )
    source_task_id = source.json()["task_id"]

    ok_response = client.post(
        "/api/v1/tasks",
        json={
            "template_id": "public_opinion_analysis_v1",
            "fork_from": {
                "task_id": source_task_id,
                "start_node_key": "search_fanout",
            },
            "input": {"topic": "fork ok"},
            "options": {},
        },
    )
    bad_response = client.post(
        "/api/v1/tasks",
        json={
            "template_id": "public_opinion_analysis_v1",
            "fork_from": {
                "task_id": source_task_id,
                "start_node_key": "missing_node",
            },
            "input": {"topic": "fork bad"},
            "options": {},
        },
    )

    assert ok_response.status_code == 202
    assert bad_response.status_code == 400
    assert bad_response.json()["detail"]["code"] == "source_task_node_not_found"


def test_fork_from_task_starts_at_requested_node_and_skips_previous_steps(client):
    source = client.post(
        "/api/v1/tasks",
        json={
            "template_id": "event_summary_v1",
            "input": {"topic": "fork source runnable"},
            "options": {},
        },
    )
    source_task_id = source.json()["task_id"]
    client.post(f"/api/v1/tasks/{source_task_id}/run")
    source_task = client.get(f"/api/v1/tasks/{source_task_id}").json()
    merge_step = next(step for step in source_task["steps"] if step["node_key"] == "merge_search_results")
    merge_artifact_id = merge_step["artifact_ids"][0]

    fork_response = client.post(
        "/api/v1/tasks",
        json={
            "template_id": "event_summary_v1",
            "fork_from": {
                "task_id": source_task_id,
                "start_node_key": "normalize_and_filter",
            },
            "input": {"topic": "fork target"},
            "options": {},
        },
    )

    assert fork_response.status_code == 202
    fork_task = client.get(f"/api/v1/tasks/{fork_response.json()['task_id']}").json()
    assert fork_task["planned_step_count"] == 3
    assert fork_task["steps"][1]["status"] == "skipped"
    assert fork_task["steps"][2]["status"] == "skipped"
    assert fork_task["steps"][3]["status"] == "skipped"
    assert fork_task["steps"][4]["status"] == "pending"
    assert fork_task["steps"][4]["input_artifact_refs"] == [merge_artifact_id]


def test_run_task_executes_pending_steps_and_generates_artifacts(client):
    create_response = client.post(
        "/api/v1/tasks",
        json={
            "template_id": "event_summary_v1",
            "input": {"topic": "run me"},
            "options": {},
        },
    )
    task_id = create_response.json()["task_id"]

    run_response = client.post(f"/api/v1/tasks/{task_id}/run")
    task_response = client.get(f"/api/v1/tasks/{task_id}")

    assert run_response.status_code == 200
    run_payload = run_response.json()
    task_payload = task_response.json()

    assert run_payload["status"] == "succeeded"
    assert run_payload["progress"] == 100.0
    assert run_payload["completed_step_count"] == run_payload["planned_step_count"]
    assert task_payload["status"] == "succeeded"
    assert all(step["status"] == "succeeded" for step in task_payload["steps"])
    assert len(task_payload["artifacts"]) == task_payload["planned_step_count"]
    assert len(task_payload["available_checkpoints"]) == task_payload["planned_step_count"]
    assert task_payload["steps"][1]["artifact_ids"]
    assert task_payload["steps"][2]["input_artifact_refs"] == task_payload["steps"][1]["artifact_ids"]


def test_artifact_lineage_endpoint_returns_edges(client):
    create_response = client.post(
        "/api/v1/tasks",
        json={
            "template_id": "event_summary_v1",
            "input": {"topic": "lineage test"},
            "options": {},
        },
    )
    task_id = create_response.json()["task_id"]
    client.post(f"/api/v1/tasks/{task_id}/run")
    task_payload = client.get(f"/api/v1/tasks/{task_id}").json()
    second_artifact_id = task_payload["artifacts"][1]["artifact_id"]

    response = client.get(f"/api/v1/artifacts/{second_artifact_id}/lineage")

    assert response.status_code == 200
    payload = response.json()
    assert payload
    assert payload[0]["relation_type"] == "derived_from"


def test_step_invocation_endpoints_return_search_and_llm_calls(client):
    create_response = client.post(
        "/api/v1/tasks",
        json={
            "template_id": "event_summary_v1",
            "input": {"topic": "invocation test"},
            "options": {},
        },
    )
    task_id = create_response.json()["task_id"]
    client.post(f"/api/v1/tasks/{task_id}/run")
    task_payload = client.get(f"/api/v1/tasks/{task_id}").json()
    search_step_id = task_payload["steps"][1]["step_run_id"]
    fetch_step_id = next(step["step_run_id"] for step in task_payload["steps"] if step["node_key"] == "fetch_documents")
    llm_step_id = task_payload["steps"][-1]["step_run_id"]

    search_response = client.get(f"/api/v1/steps/{search_step_id}/search-invocations")
    fetch_response = client.get(f"/api/v1/steps/{fetch_step_id}/fetch-invocations")
    llm_response = client.get(f"/api/v1/steps/{llm_step_id}/llm-invocations")

    assert search_response.status_code == 200
    assert fetch_response.status_code == 200
    assert llm_response.status_code == 200

    search_payload = search_response.json()
    fetch_payload = fetch_response.json()
    llm_payload = llm_response.json()

    assert search_payload
    assert fetch_payload
    assert llm_payload
    assert search_payload[0]["provider_vendor"] in {"exa", "tavily"}
    assert fetch_payload[0]["provider_vendor"] == "firecrawl"
    assert llm_payload[0]["profile_name"] == "advanced_reasoning_cn"


def test_task_invocation_endpoints_return_aggregated_calls(client):
    create_response = client.post(
        "/api/v1/tasks",
        json={
            "template_id": "event_summary_v1",
            "input": {"topic": "task invocations"},
            "options": {},
        },
    )
    task_id = create_response.json()["task_id"]
    client.post(f"/api/v1/tasks/{task_id}/run")

    search_response = client.get(f"/api/v1/tasks/{task_id}/search-invocations")
    fetch_response = client.get(f"/api/v1/tasks/{task_id}/fetch-invocations")
    tool_response = client.get(f"/api/v1/tasks/{task_id}/tool-invocations")
    llm_response = client.get(f"/api/v1/tasks/{task_id}/llm-invocations")

    assert search_response.status_code == 200
    assert fetch_response.status_code == 200
    assert tool_response.status_code == 200
    assert llm_response.status_code == 200
    assert len(search_response.json()) == 2
    assert len(fetch_response.json()) == 4
    assert len(tool_response.json()) == 0
    assert len(llm_response.json()) == 1


def test_public_opinion_analysis_task_records_tool_invocation(client):
    create_response = client.post(
        "/api/v1/tasks",
        json={
            "template_id": "public_opinion_analysis_v1",
            "input": {"topic": "mcp context test"},
            "options": {},
        },
    )
    task_id = create_response.json()["task_id"]
    client.post(f"/api/v1/tasks/{task_id}/run")

    tool_invocations = client.get(f"/api/v1/tasks/{task_id}/tool-invocations").json()
    bundle = client.get(f"/api/v1/tasks/{task_id}/bundle").json()

    assert tool_invocations
    assert tool_invocations[0]["server_name"] == "internal_tools"
    assert any(artifact["artifact_type"] == "tool.mcp_result" for artifact in bundle["task"]["artifacts"])
    classified = next((artifact for artifact in bundle["task"]["artifacts"] if artifact["artifact_type"] == "analysis.classified_sources"), None)
    assert classified is not None


def test_task_options_can_override_search_fetch_and_llm_selection(client):
    create_response = client.post(
        "/api/v1/tasks",
        json={
            "template_id": "event_summary_v1",
            "input": {"topic": "override test"},
            "options": {
                "search_provider_names": ["exa_search"],
                "search_limit": 1,
                "fetch_provider_name": "exa_contents",
                "llm_profile_name": "cheap_structured_cn",
            },
        },
    )
    task_id = create_response.json()["task_id"]
    client.post(f"/api/v1/tasks/{task_id}/run")

    search_invocations = client.get(f"/api/v1/tasks/{task_id}/search-invocations").json()
    fetch_invocations = client.get(f"/api/v1/tasks/{task_id}/fetch-invocations").json()
    llm_invocations = client.get(f"/api/v1/tasks/{task_id}/llm-invocations").json()

    assert len(search_invocations) == 1
    assert search_invocations[0]["provider_name"] == "exa_search"
    assert search_invocations[0]["request_metadata"]["limit"] == 1
    assert fetch_invocations
    assert all(item["provider_name"] == "exa_contents" for item in fetch_invocations)
    assert llm_invocations[0]["profile_name"] == "cheap_structured_cn"


def test_task_can_run_with_langgraph_execution_engine(client):
    create_response = client.post(
        "/api/v1/tasks",
        json={
            "template_id": "event_summary_v1",
            "input": {"topic": "langgraph test"},
            "options": {"execution_engine": "langgraph"},
        },
    )
    task_id = create_response.json()["task_id"]

    run_response = client.post(f"/api/v1/tasks/{task_id}/run")
    task_response = client.get(f"/api/v1/tasks/{task_id}")

    assert run_response.status_code == 200
    assert run_response.json()["status"] in {"succeeded", "running"}
    assert task_response.status_code == 200
    assert task_response.json()["completed_step_count"] >= 2


def test_task_events_endpoint_returns_lifecycle_events(client):
    create_response = client.post(
        "/api/v1/tasks",
        json={
            "template_id": "event_summary_v1",
            "input": {"topic": "events test"},
            "options": {},
        },
    )
    task_id = create_response.json()["task_id"]
    client.post(f"/api/v1/tasks/{task_id}/run")

    response = client.get(f"/api/v1/tasks/{task_id}/events")

    assert response.status_code == 200
    payload = response.json()
    event_types = {item["event_type"] for item in payload}
    assert "task_created" in event_types
    assert "task_running" in event_types
    assert "step_started" in event_types
    assert "step_succeeded" in event_types
    assert "task_succeeded" in event_types


def test_task_stats_endpoint_returns_aggregate_counts(client):
    create_response = client.post(
        "/api/v1/tasks",
        json={
            "template_id": "event_summary_v1",
            "input": {"topic": "stats test"},
            "options": {},
        },
    )
    task_id = create_response.json()["task_id"]
    client.post(f"/api/v1/tasks/{task_id}/run")

    response = client.get(f"/api/v1/tasks/{task_id}/stats")

    assert response.status_code == 200
    payload = response.json()
    assert payload["task_id"] == task_id
    assert payload["status"] == "succeeded"
    assert payload["artifact_count"] >= 1
    assert payload["document_count"] >= 1
    assert payload["search_hit_count"] >= 1
    assert payload["search_invocation_count"] == 2
    assert payload["fetch_invocation_count"] >= 1
    assert payload["tool_invocation_count"] >= 0
    assert payload["llm_invocation_count"] == 1
    assert payload["event_count"] >= 1


def test_task_graph_endpoint_returns_nodes_and_edges(client):
    create_response = client.post(
        "/api/v1/tasks",
        json={
            "template_id": "event_summary_v1",
            "input": {"topic": "graph test"},
            "options": {},
        },
    )
    task_id = create_response.json()["task_id"]
    client.post(f"/api/v1/tasks/{task_id}/run")

    response = client.get(f"/api/v1/tasks/{task_id}/graph")

    assert response.status_code == 200
    payload = response.json()
    node_kinds = {node["node_kind"] for node in payload["nodes"]}
    edge_kinds = {edge["edge_kind"] for edge in payload["edges"]}
    assert payload["task_id"] == task_id
    assert "step" in node_kinds
    assert "artifact" in node_kinds
    assert "step_output" in edge_kinds
    assert "artifact_input" in edge_kinds


def test_task_bundle_endpoint_returns_aggregated_views(client):
    create_response = client.post(
        "/api/v1/tasks",
        json={
            "template_id": "event_summary_v1",
            "input": {"topic": "bundle test"},
            "options": {},
        },
    )
    task_id = create_response.json()["task_id"]
    client.post(f"/api/v1/tasks/{task_id}/run")

    response = client.get(f"/api/v1/tasks/{task_id}/bundle")

    assert response.status_code == 200
    payload = response.json()
    assert payload["task"]["task_id"] == task_id
    assert payload["stats"]["task_id"] == task_id
    assert payload["events"]
    assert payload["search_hits"]
    assert payload["documents"]
    assert payload["search_invocations"]
    assert payload["fetch_invocations"]
    assert "tool_invocations" in payload
    assert payload["llm_invocations"]


def test_search_hits_are_persisted_and_queryable(client):
    create_response = client.post(
        "/api/v1/tasks",
        json={
            "template_id": "event_summary_v1",
            "input": {
                "topic": "search hit test",
                "time_range": {
                    "start": "2026-05-01T00:00:00Z",
                    "end": "2026-05-09T00:00:00Z",
                },
            },
            "options": {},
        },
    )
    task_id = create_response.json()["task_id"]
    client.post(f"/api/v1/tasks/{task_id}/run")
    task_payload = client.get(f"/api/v1/tasks/{task_id}").json()
    search_step_id = task_payload["steps"][1]["step_run_id"]

    task_hits_response = client.get(f"/api/v1/tasks/{task_id}/search-hits")
    step_hits_response = client.get(f"/api/v1/steps/{search_step_id}/search-hits")

    assert task_hits_response.status_code == 200
    assert step_hits_response.status_code == 200

    task_hits = task_hits_response.json()
    step_hits = step_hits_response.json()

    assert task_hits
    assert step_hits
    assert task_hits[0]["provider_name"] in {"exa_search", "tavily_search"}
    assert task_hits[0]["title"]
    assert task_hits[0]["source_type"] in {"news", "social"}
    assert "published_at_utc" in task_hits[0]
    assert "source_url" in task_hits[0]["metadata"]


def test_documents_are_persisted_and_queryable(client):
    create_response = client.post(
        "/api/v1/tasks",
        json={
            "template_id": "event_summary_v1",
            "input": {"topic": "document test"},
            "options": {},
        },
    )
    task_id = create_response.json()["task_id"]
    client.post(f"/api/v1/tasks/{task_id}/run")
    task_payload = client.get(f"/api/v1/tasks/{task_id}").json()
    fetch_step_id = next(step["step_run_id"] for step in task_payload["steps"] if step["node_key"] == "fetch_documents")

    task_docs_response = client.get(f"/api/v1/tasks/{task_id}/documents")
    step_docs_response = client.get(f"/api/v1/steps/{fetch_step_id}/documents")

    assert task_docs_response.status_code == 200
    assert step_docs_response.status_code == 200

    task_docs = task_docs_response.json()
    step_docs = step_docs_response.json()

    assert task_docs
    assert step_docs
    assert task_docs[0]["url"].startswith("https://")
    assert task_docs[0]["canonical_url"].startswith("https://")
    assert task_docs[0]["author"]
    assert task_docs[0]["language"] == "en"
    assert task_docs[0]["source_domain"]
    assert task_docs[0]["source_type"] in {"news", "social"}
    assert task_docs[0]["region_hint"] == "overseas"
    assert task_docs[0]["publisher_type"] == "media"
    assert task_docs[0]["content_text"]


def test_documents_can_be_filtered(client):
    create_response = client.post(
        "/api/v1/tasks",
        json={
            "template_id": "event_summary_v1",
            "input": {"topic": "document filter test"},
            "options": {},
        },
    )
    task_id = create_response.json()["task_id"]
    client.post(f"/api/v1/tasks/{task_id}/run")

    provider_filtered = client.get(f"/api/v1/tasks/{task_id}/documents?provider_name=firecrawl_scrape")
    domain_filtered = client.get(f"/api/v1/tasks/{task_id}/documents?source_domain=exa.example.com")
    source_type_filtered = client.get(f"/api/v1/tasks/{task_id}/documents?source_type=news")
    region_filtered = client.get(f"/api/v1/tasks/{task_id}/documents?region_hint=overseas")

    assert provider_filtered.status_code == 200
    assert domain_filtered.status_code == 200
    assert source_type_filtered.status_code == 200
    assert region_filtered.status_code == 200
    assert all(item["provider_name"] == "firecrawl_scrape" for item in provider_filtered.json())
    assert all(item["source_domain"] == "exa.example.com" for item in domain_filtered.json())
    assert all(item["source_type"] == "news" for item in source_type_filtered.json())
    assert all(item["region_hint"] == "overseas" for item in region_filtered.json())


def test_search_hits_can_be_filtered(client):
    create_response = client.post(
        "/api/v1/tasks",
        json={
            "template_id": "event_summary_v1",
            "input": {
                "topic": "search filter test",
                "time_range": {
                    "start": "2026-05-01T00:00:00Z",
                    "end": "2026-05-09T00:00:00Z",
                },
            },
            "options": {},
        },
    )
    task_id = create_response.json()["task_id"]
    client.post(f"/api/v1/tasks/{task_id}/run")

    provider_filtered = client.get(f"/api/v1/tasks/{task_id}/search-hits?provider_name=exa_search")
    source_filtered = client.get(f"/api/v1/tasks/{task_id}/search-hits?source_type=news")
    region_filtered = client.get(f"/api/v1/tasks/{task_id}/search-hits?region_hint=overseas")
    time_filtered = client.get(
        f"/api/v1/tasks/{task_id}/search-hits?published_after=2026-05-08T00:00:00Z&published_before=2026-05-09T00:00:00Z"
    )

    assert provider_filtered.status_code == 200
    assert source_filtered.status_code == 200
    assert region_filtered.status_code == 200
    assert time_filtered.status_code == 200
    assert all(item["provider_name"] == "exa_search" for item in provider_filtered.json())
    assert all(item["source_type"] == "news" for item in source_filtered.json())
    assert all(item["region_hint"] == "overseas" for item in region_filtered.json())
    assert time_filtered.json()


def test_search_fanout_deduplicates_hits_by_url_and_merges_fields():
    providers = {
        "provider_a": _StubSearchProvider(
            "provider_a",
            [
                SearchHit(
                    provider="provider_a",
                    title="Shared headline",
                    url="https://example.com/shared-article",
                    source_domain="example.com",
                    source_type="mainstream_media",
                    query="q",
                    published_at_utc="2026-05-01",
                    snippet="short snippet",
                    metadata={"author": "Author A", "publisher": "Publisher A", "language": "en"},
                )
            ],
        ),
        "provider_b": _StubSearchProvider(
            "provider_b",
            [
                SearchHit(
                    provider="provider_b",
                    title="Shared headline with more detail",
                    url="https://example.com/shared-article",
                    source_domain="example.com",
                    source_type="mainstream_media",
                    query="q",
                    published_at_utc="2026-05-01",
                    snippet="a much longer snippet from provider b",
                    metadata={"publisher": "Publisher B", "region_hint": "global"},
                )
            ],
        ),
    }
    executor = SearchFanoutExecutor(search_provider_factory=_StubSearchProviderFactory(providers))
    executor.source_registry = _StubSourceRegistry()
    task = type(
        "Task",
        (),
        {
            "input_payload": {"topic": "q"},
            "options_payload": {"search_provider_names": ["provider_a", "provider_b"], "search_limit": 5},
        },
    )()
    step = type("Step", (), {"node_key": "search_fanout"})()

    result = executor.execute(task, step)
    hits = result.content_json["hits"]

    assert len(hits) == 1
    assert hits[0]["title"] == "Shared headline with more detail"
    assert hits[0]["snippet"] == "a much longer snippet from provider b"
    assert set(hits[0]["matched_provider_names"]) == {"provider_a", "provider_b"}
    assert hits[0]["duplicate_count"] == 2
    assert hits[0]["author"] == "Author A"


def test_fetch_documents_deduplicates_documents_by_canonical_url():
    executor = FetchDocumentsExecutor(search_provider_factory=_StubFetchFactory())
    executor.source_registry = _StubSourceRegistry()
    task = type(
        "Task",
        (),
        {
            "id": "run_x",
            "options_payload": {"fetch_provider_name": "stub_fetch"},
            "artifacts": [],
        },
    )()
    artifact = type(
        "Artifact",
        (),
        {
            "id": "art_1",
            "content_json": {
                "hits": [
                    {
                        "provider": "provider_a",
                        "title": "Shared headline",
                        "source_url": "https://example.com/shared-article?ref=a",
                        "source_domain": "example.com",
                        "source_type": "mainstream_media",
                        "region_hint": "overseas",
                        "publisher_type": "media",
                        "published_at_utc": "2026-05-01",
                        "author": "Author A",
                        "publisher": "Publisher A",
                        "language": "en",
                        "matched_provider_names": ["provider_a"],
                        "duplicate_count": 1,
                    },
                    {
                        "provider": "provider_b",
                        "title": "Shared headline updated",
                        "source_url": "https://example.com/shared-article?ref=b",
                        "source_domain": "example.com",
                        "source_type": "mainstream_media",
                        "region_hint": "overseas",
                        "publisher_type": "media",
                        "published_at_utc": "2026-05-01",
                        "author": "",
                        "publisher": "Publisher B",
                        "language": "en",
                        "matched_provider_names": ["provider_b"],
                        "duplicate_count": 1,
                    },
                ]
            }
        },
    )()
    step = type("Step", (), {"input_artifact_refs": ["art_1"], "node_key": "fetch_documents"})()
    task.artifacts = [artifact]

    result = executor.execute(task, step)
    docs = result.content_json["documents"]

    assert len(docs) == 1
    assert docs[0]["canonical_url"] == "https://example.com/shared-article"
    assert set(docs[0]["metadata"]["matched_provider_names"]) == {"provider_a", "provider_b"}
    assert docs[0]["metadata"]["duplicate_count"] == 2


def test_llm_report_executor_uses_fallback_profile_after_retries():
    factory = _StubLLMFactory(
        providers_by_profile={
            "primary_profile": _StubLLMProvider("primary_provider", "model-a", ["", ""]),
            "fallback_profile": _StubLLMProvider("fallback_provider", "model-b", ["fallback success"]),
        },
        fallback_profiles={"primary_profile": ["fallback_profile"]},
    )
    executor = LLMReportExecutor(llm_provider_factory=factory, profile_name="primary_profile")
    task = type(
        "Task",
        (),
        {
            "id": "run_stub",
            "input_payload": {"topic": "fallback test"},
            "options_payload": {
                "llm_profile_name": "primary_profile",
                "report_retry_count": 0,
                "llm_model_retry_count": 1,
                "report_fallback_profile_names": [],
            },
            "artifacts": [],
        },
    )()
    step = type("Step", (), {"node_key": "generate_public_opinion_report", "input_artifact_refs": []})()

    result = executor.execute(task, step)

    assert result.content_text == "fallback success"
    assert result.content_json["resolved_profile_name"] == "fallback_profile"
    assert len(result.llm_invocations) == 3
    assert result.llm_invocations[-1].profile_name == "fallback_profile"


def test_final_report_endpoint_returns_generated_report(client):
    create_response = client.post(
        "/api/v1/tasks",
        json={
            "template_id": "event_summary_v1",
            "input": {"topic": "final report test"},
            "options": {},
        },
    )
    task_id = create_response.json()["task_id"]
    client.post(f"/api/v1/tasks/{task_id}/run")

    response = client.get(f"/api/v1/tasks/{task_id}/final-report")

    assert response.status_code == 200
    payload = response.json()
    assert payload["task_id"] == task_id
    assert payload["ready"] is True
    assert payload["report_state"] == "ready"
    assert payload["artifact_id"]
    assert payload["report_text"]
    assert payload["timeline_count"] >= 0
    assert payload["official_response_count"] >= 0
    assert payload["media_viewpoint_count"] >= 0
    assert payload["public_viewpoint_count"] >= 0
    assert "timeline" in payload
    assert "official_responses" in payload
    assert "media_viewpoints" in payload
    assert "public_viewpoints" in payload


def test_extract_official_responses_includes_response_content_and_key_points():
    executor = ExtractOfficialResponsesExecutor()
    task = type(
        "Task",
        (),
        {
            "id": "run_official",
            "artifacts": [
                type(
                    "Artifact",
                    (),
                    {
                        "id": "art_official",
                        "schema_name": "merged_results_bundle",
                        "content_json": {
                            "documents": [
                                {
                                    "title": "国务院成立事故调查组",
                                    "url": "https://example.com/official",
                                    "source_domain": "example.com",
                                    "published_at_utc": "2026-05-08",
                                    "content_preview": "国务院成立事故调查组，并要求尽快查明原因，严肃追责，全面开展安全整治。",
                                }
                            ]
                        },
                    },
                )()
            ],
        },
    )()
    step = type("Step", (), {"node_key": "extract_official_responses", "input_artifact_refs": ["art_official"]})()

    result = executor.execute(task, step)
    responses = result.content_json["official_responses"]

    assert len(responses) == 1
    assert responses[0]["response_excerpt"]
    assert responses[0]["response_content"]
    assert responses[0]["response_key_points"]


def test_repeated_search_task_uses_cached_search_fanout(client):
    request_body = {
        "template_id": "event_summary_v1",
        "input": {
            "topic": "cache smoke",
            "time_range": {
                "start": "2026-05-01T00:00:00Z",
                "end": "2026-05-09T00:00:00Z",
            },
        },
        "options": {},
    }

    first = client.post("/api/v1/tasks", json=request_body).json()
    client.post(f"/api/v1/tasks/{first['task_id']}/run")

    second = client.post("/api/v1/tasks", json=request_body).json()
    client.post(f"/api/v1/tasks/{second['task_id']}/run-next-step")
    second_task = client.get(f"/api/v1/tasks/{second['task_id']}").json()
    search_step = next(step for step in second_task["steps"] if step["node_key"] == "search_fanout")
    events = client.get(f"/api/v1/tasks/{second['task_id']}/events").json()

    assert search_step["status"] == "cached"
    assert any(event["event_type"] == "step_cached" for event in events)


def test_repeated_identical_task_can_cache_multiple_downstream_steps(client):
    request_body = {
        "template_id": "event_summary_v1",
        "input": {
            "topic": "deep cache smoke",
            "time_range": {
                "start": "2026-05-01T00:00:00Z",
                "end": "2026-05-09T00:00:00Z",
            },
        },
        "options": {},
    }

    first = client.post("/api/v1/tasks", json=request_body).json()
    client.post(f"/api/v1/tasks/{first['task_id']}/run")

    second = client.post("/api/v1/tasks", json=request_body).json()
    client.post(f"/api/v1/tasks/{second['task_id']}/run")
    second_task = client.get(f"/api/v1/tasks/{second['task_id']}").json()

    cached_steps = [step for step in second_task["steps"] if step["status"] == "cached"]
    assert len(cached_steps) >= 2


def test_run_missing_task_returns_404(client):
    response = client.post("/api/v1/tasks/run_missing/run")

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "task_not_found"


def test_run_next_step_advances_task_incrementally(client):
    create_response = client.post(
        "/api/v1/tasks",
        json={
            "template_id": "event_summary_v1",
            "input": {"topic": "incremental run"},
            "options": {},
        },
    )
    task_id = create_response.json()["task_id"]

    first = client.post(f"/api/v1/tasks/{task_id}/run-next-step")
    second = client.post(f"/api/v1/tasks/{task_id}/run-next-step")
    detail_after_two = client.get(f"/api/v1/tasks/{task_id}")

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["status"] == "running"
    assert first.json()["progress"] > 5.0
    assert second.json()["progress"] > first.json()["progress"]
    payload = detail_after_two.json()
    succeeded_steps = [step for step in payload["steps"] if step["status"] == "succeeded"]
    assert len(succeeded_steps) == 3

    client.post(f"/api/v1/tasks/{task_id}/run-next-step")
    client.post(f"/api/v1/tasks/{task_id}/run-next-step")
    final_response = client.post(f"/api/v1/tasks/{task_id}/run-next-step")

    assert final_response.status_code == 200
    assert final_response.json()["status"] == "succeeded"
    assert final_response.json()["progress"] == 100.0


def test_cancel_task_updates_status_and_emits_event(client):
    create_response = client.post(
        "/api/v1/tasks",
        json={
            "template_id": "event_summary_v1",
            "input": {"topic": "cancel me"},
            "options": {},
        },
    )
    task_id = create_response.json()["task_id"]

    cancel_response = client.post(f"/api/v1/tasks/{task_id}/cancel")
    events_response = client.get(f"/api/v1/tasks/{task_id}/events")

    assert cancel_response.status_code == 200
    assert cancel_response.json()["status"] == "cancelled"
    event_types = {item["event_type"] for item in events_response.json()}
    assert "task_cancelled" in event_types


def test_step_can_fail_once_and_then_succeed_on_retry(client):
    create_response = client.post(
        "/api/v1/tasks",
        json={
            "template_id": "event_summary_v1",
            "input": {"topic": "retry once"},
            "options": {
                "simulate_fail_once_nodes": ["fetch_documents"],
                "retry_policy": {"max_attempts": 2},
            },
        },
    )
    task_id = create_response.json()["task_id"]

    client.post(f"/api/v1/tasks/{task_id}/run")
    after_failure = client.get(f"/api/v1/tasks/{task_id}").json()

    fetch_step = next(step for step in after_failure["steps"] if step["node_key"] == "fetch_documents")
    assert after_failure["status"] == "waiting_retry"
    assert fetch_step["status"] == "retrying"

    client.post(f"/api/v1/tasks/{task_id}/run-next-step")
    client.post(f"/api/v1/tasks/{task_id}/run")
    final_task = client.get(f"/api/v1/tasks/{task_id}").json()
    event_types = {item["event_type"] for item in client.get(f"/api/v1/tasks/{task_id}/events").json()}

    assert final_task["status"] == "succeeded"
    assert "step_failed" in event_types
    assert "task_waiting_retry" in event_types


def test_step_can_fail_terminally_after_retry_budget_exhausted(client):
    create_response = client.post(
        "/api/v1/tasks",
        json={
            "template_id": "event_summary_v1",
            "input": {"topic": "retry always fail"},
            "options": {
                "simulate_fail_always_nodes": ["fetch_documents"],
                "retry_policy": {"max_attempts": 2},
            },
        },
    )
    task_id = create_response.json()["task_id"]

    client.post(f"/api/v1/tasks/{task_id}/run")
    client.post(f"/api/v1/tasks/{task_id}/run-next-step")
    final_task = client.get(f"/api/v1/tasks/{task_id}").json()
    event_types = {item["event_type"] for item in client.get(f"/api/v1/tasks/{task_id}/events").json()}

    assert final_task["status"] in {"partial_failed", "failed"}
    assert "task_failed" in event_types

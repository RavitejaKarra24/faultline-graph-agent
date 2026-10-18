import json
from unittest.mock import MagicMock, patch

import httpx
import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr, ValidationError
from redis.exceptions import ConnectionError

from faultline_backend.app import create_app
from faultline_backend.config import Settings, workspace_slug
from faultline_backend.fixture import DEPENDENCIES, EDGES, NODES
from faultline_backend.planner import investigate, synthesize_summary
from faultline_backend.schemas import DependencyInput, InvestigationInput, Memory, MemoryInput
from faultline_backend.storage import APIError, Database


@pytest.mark.parametrize("slug", ["demo", "a", "team-123", "x" * 40])
def test_workspace_accepts_safe_slugs(slug):
    assert workspace_slug(slug) == slug


@pytest.mark.parametrize(
    "slug", ["", "-a", "a-", "A", "a_b", "a/b", "a b", "x" * 41, "a\n", "a` MATCH (n) DELETE n"]
)
def test_workspace_rejects_injection_and_unsafe_slugs(slug):
    with pytest.raises(ValueError):
        workspace_slug(slug)


@pytest.mark.parametrize(
    "changes",
    [
        {"question": " "},
        {"question": "x" * 2001},
        {"sessionId": ""},
        {"sessionId": "x" * 101},
        {"serviceId": "a' OR 1=1"},
        {"extra": True},
    ],
)
def test_investigation_input_bounds(changes):
    with pytest.raises(ValidationError):
        InvestigationInput.model_validate(
            {"serviceId": "svc-redis", "question": "what breaks?", "sessionId": "s", **changes}
        )


@pytest.mark.parametrize("enabled", [1, "true", None])
def test_dependency_requires_strict_boolean(enabled):
    with pytest.raises(ValidationError):
        DependencyInput(source="svc-payments", target="svc-redis", enabled=enabled)


def test_memory_validation_and_camel_case():
    body = MemoryInput.model_validate(
        {"serviceId": "svc-redis", "sessionId": "s", "content": " pool cap ", "outcome": "helpful"}
    )
    assert body.content == "pool cap"
    assert body.model_dump(by_alias=True)["serviceId"] == "svc-redis"
    with pytest.raises(ValidationError):
        MemoryInput(service_id="svc-redis", session_id="s", content="x", outcome="unknown")


def test_fixture_is_rich_and_structurally_valid():
    ids = {n["id"] for n in NODES}
    assert len(ids) == len(NODES) == 25
    assert all(n["fictional"] for n in NODES)
    assert len(EDGES) == 31
    assert all(s in ids and t in ids for s, t, _ in EDGES)
    assert ("svc-checkout", "svc-auth") in DEPENDENCIES
    assert {n["kind"] for n in NODES} == {
        "Service",
        "Team",
        "Person",
        "Customer",
        "Runbook",
        "Incident",
        "Decision",
    }


def test_query_records_real_driver_timing_parameters_and_count(mocked_store):
    store, graph = mocked_store
    graph.ro_query.return_value.result_set = [["a"], ["b"]]
    trace = []
    rows = store.query(
        "MATCH (s {id: $id}) RETURN s.id",
        {"id": "x' MATCH (n)"},
        read_only=True,
        trace=trace,
        agent="impact-analyst",
        purpose="test",
    )
    graph.ro_query.assert_called_once_with(
        "MATCH (s {id: $id}) RETURN s.id", {"id": "x' MATCH (n)"}, timeout=3000
    )
    assert len(rows) == trace[0].result_count == 2
    assert trace[0].params["id"] not in trace[0].query
    assert trace[0].duration_ms >= 0
    assert trace[0].agent == "impact-analyst"
    assert trace[0].tool == "falkordb.ro_query"


def test_database_failure_is_explicit_no_fixtures(mocked_store):
    store, graph = mocked_store
    graph.ro_query.side_effect = ConnectionError("offline")
    trace = []
    with pytest.raises(APIError) as caught:
        store.query("RETURN $x", {"x": 1}, read_only=True, trace=trace)
    assert caught.value.status == 503
    assert trace[0].result_count == 0
    assert trace[0].duration_ms >= 0
    graph.query.assert_not_called()


def plan(mocked_store, settings, memories=()):
    store, graph = mocked_store
    responses = [
        [[{"id": "svc-redis", "label": "Redis", "tier": 0, "status": "degraded"}]],
        [["svc-payments", "Payments", ["svc-payments", "svc-redis"]]],
        [["customer-acme", "Acme", ["customer-acme", "svc-payments", "svc-redis"]]],
        [["svc-redis", "team-platform", "Platform", "person-maya", "Maya"]],
        [
            ["RUN-001", "Cap pools", "Cap pools before restarting", "Runbook", "svc-redis"],
            [
                "INC-001",
                "Exhausted pools",
                "Pool cap fixed the prior outage",
                "Incident",
                "svc-redis",
            ],
            ["DEC-001", "No restart", "Restart risks tokens", "Decision", "svc-redis"],
        ],
        [[m.model_dump(by_alias=True)] for m in memories],
        [["degraded", 0]],
    ]
    graph.ro_query.side_effect = [MagicMock(result_set=rows) for rows in responses]
    graph.query.return_value.result_set = []
    item = investigate(
        store,
        InvestigationInput(
            service_id="svc-redis", question="restart now?", session_id="new-session"
        ),
        settings,
    )
    return item, graph


def test_planner_is_bounded_graph_tools_and_persists_entire_json(mocked_store, settings):
    item, graph = plan(mocked_store, settings)
    assert item.mode == "graph-tools"
    assert item.impacted_services == ["svc-payments"]
    assert item.impacted_customers == ["customer-acme"]
    assert len(item.trace) == 7
    assert {t.agent for t in item.trace} == {
        "bounded-planner",
        "impact-analyst",
        "ownership-resolver",
        "memory-runbook-researcher",
        "response-coordinator",
    }
    assert all(t.query and t.params and t.duration_ms >= 0 for t in item.trace)
    impact = [t for t in item.trace if t.agent == "impact-analyst"]
    assert all(
        "*1..6" in t.query and "r.enabled = true" in t.query and "LIMIT 256" in t.query
        for t in impact
    )
    query, params = graph.query.call_args.args
    assert "CREATE (a:Action" in query
    assert json.loads(params["json"]) == item.model_dump(by_alias=True)
    assert {e.id for e in item.evidence} >= {"INC-001", "RUN-001", "DEC-001"}
    assert all(set(a.evidence_ids) <= {e.id for e in item.evidence} for a in item.actions)


def test_prior_memory_actually_changes_recommendations(mocked_store, settings):
    memory = Memory(
        id="mem-1",
        service_id="svc-redis",
        content="Avoid full restarts during checkout",
        outcome="avoid",
        session_id="old-session",
        created_at="2025-01-01T00:00:00Z",
    )
    item, _ = plan(mocked_store, settings, [memory])
    runbook = next(a for a in item.actions if a.target == "RUN-001")
    assert runbook.kind == "review"
    assert memory.content in runbook.description
    assert memory.id in runbook.evidence_ids
    assert item.memories[0].session_id != item.session_id
    assert any("avoid feedback changed" in w for w in item.warnings)


def test_helpful_memory_informs_runbook(mocked_store, settings):
    memory = Memory(
        id="mem-2",
        service_id="svc-redis",
        content="Pool cap of 32 worked previously",
        outcome="helpful",
        session_id="old",
        created_at="2025-01-01T00:00:00Z",
    )
    item, _ = plan(mocked_store, settings, [memory])
    runbook = next(a for a in item.actions if a.target == "RUN-001")
    assert runbook.kind == "runbook"
    assert memory.content in runbook.description
    assert memory.id in runbook.evidence_ids


def test_no_key_never_calls_a_model(mocked_store, settings):
    with patch("faultline_backend.planner.httpx.Client") as client:
        item, _ = plan(mocked_store, settings)
    client.assert_not_called()
    assert item.mode == "graph-tools"


def test_optional_summary_success_is_genuine_api_call_without_tools(mocked_store, settings):
    item, _ = plan(mocked_store, settings)
    settings.openai_api_key = SecretStr("unit-test-key")
    response = MagicMock()
    response.json.return_value = {
        "choices": [
            {
                "message": {
                    "content": json.dumps(
                        {
                            "summary": "Recorded pool exhaustion warrants pool-cap review.",
                            "evidenceIds": ["RUN-001"],
                        }
                    )
                }
            }
        ]
    }
    with patch("faultline_backend.planner.httpx.Client") as cls:
        cls.return_value.__enter__.return_value.post.return_value = response
        synthesize_summary(item, settings)
        payload = cls.return_value.__enter__.return_value.post.call_args.kwargs["json"]
    assert item.mode == "llm"
    assert "tools" not in payload and "functions" not in payload
    assert item.summary == "Recorded pool exhaustion warrants pool-cap review. [RUN-001]"


@pytest.mark.parametrize("failure", ["http", "invalid-url", "invalid", "unknown-citation"])
def test_optional_summary_falls_back_safely(mocked_store, settings, failure):
    item, _ = plan(mocked_store, settings)
    original = item.summary
    settings.openai_api_key = SecretStr("unit-test-key")
    with patch("faultline_backend.planner.httpx.Client") as cls:
        client = cls.return_value.__enter__.return_value
        if failure == "http":
            client.post.side_effect = httpx.ConnectError("offline")
        elif failure == "invalid-url":
            client.post.side_effect = httpx.InvalidURL("bad URL")
        else:
            content = (
                "not json"
                if failure == "invalid"
                else json.dumps({"summary": "x", "evidenceIds": ["FAKE-001"]})
            )
            client.post.return_value.json.return_value = {
                "choices": [{"message": {"content": content}}]
            }
        synthesize_summary(item, settings)
    assert item.summary == original
    assert item.mode == "graph-tools"
    assert any("summary unavailable" in w for w in item.warnings)


@pytest.fixture
def offline_api(settings):
    db = MagicMock(spec=Database)
    db.health.side_effect = APIError("DATABASE_UNAVAILABLE", "offline", 503)
    db.workspace.return_value.ensure_seeded.side_effect = APIError(
        "DATABASE_UNAVAILABLE", "offline", 503
    )
    with TestClient(create_app(settings, db)) as client:
        yield client, db


def test_api_health_offline_and_consistent_errors(offline_api):
    client, _ = offline_api
    assert client.get("/api/health").json() == {
        "status": "unavailable",
        "database": "FalkorDB",
        "mode": "graph-tools",
        "version": "0.1.0",
    }
    assert client.get("/api/health").status_code == 503
    response = client.get("/api/graph")
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "DATABASE_UNAVAILABLE"
    assert client.get("/api/no-such-route").json()["error"]["code"] == "NOT_FOUND"


def test_invalid_input_rejected_before_database_access(offline_api):
    client, db = offline_api
    for payload in [{}, {"serviceId": "x", "sessionId": "s", "question": ""}]:
        response = client.post("/api/investigations", json=payload)
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "VALIDATION_ERROR"
    db.workspace.return_value.ensure_seeded.assert_not_called()
    assert (
        client.post(
            "/api/memories", content="{", headers={"content-type": "application/json"}
        ).status_code
        == 422
    )


def test_workspace_header_validation(offline_api):
    client, db = offline_api
    response = client.get("/api/graph", headers={"X-Workspace": "../demo"})
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_WORKSPACE"
    db.workspace.assert_not_called()


def test_body_limit_rejects_before_database(offline_api):
    client, db = offline_api
    response = client.post("/api/memories", content=b"x" * 16385)
    assert response.status_code == 413
    assert response.json()["error"]["code"] == "PAYLOAD_TOO_LARGE"
    db.workspace.assert_not_called()


def test_cors_only_loopback_origins(offline_api):
    client, _ = offline_api
    for origin in ["http://localhost:5173", "http://127.0.0.1:3000", "http://[::1]:8000"]:
        response = client.options(
            "/api/graph", headers={"Origin": origin, "Access-Control-Request-Method": "GET"}
        )
        assert response.status_code == 200
        assert response.headers["access-control-allow-origin"] == origin
    for origin in ["https://example.com", "http://localhost.evil.test", "null"]:
        response = client.options(
            "/api/graph", headers={"Origin": origin, "Access-Control-Request-Method": "GET"}
        )
        assert response.status_code == 400
        assert "access-control-allow-origin" not in response.headers


def test_database_client_initialization_failure_is_explicit(settings):
    with patch("faultline_backend.storage.FalkorDB", side_effect=ConnectionError("offline")):
        with pytest.raises(APIError) as caught:
            Database(settings).health()
    assert caught.value.code == "DATABASE_UNAVAILABLE"


def test_default_bind_and_graph_prefix(settings):
    assert settings.host == "127.0.0.1"
    assert settings.graph_prefix == "faultline_"
    with pytest.raises(ValidationError):
        Settings(_env_file=None, graph_prefix="bad-prefix")

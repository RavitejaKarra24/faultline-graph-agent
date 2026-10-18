"""Opt-in real FalkorDB contract tests; no mocks, fallback fixtures, or shared demo writes."""

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from faultline_backend.app import create_app
from faultline_backend.schemas import Investigation
from faultline_backend.storage import Database

pytestmark = pytest.mark.integration


@pytest.fixture
def live(settings):
    database = Database(settings)
    slug = "it-" + uuid4().hex[:24]
    headers = {"X-Workspace": slug}
    store = database.workspace(slug)
    with TestClient(create_app(settings, database)) as client:
        try:
            yield client, headers, store, settings
        finally:
            # Explicitly scoped deletion: never FLUSHDB and never touch the demo graph.
            database.client.select_graph(store.graph_name).delete()


def investigate(client, headers, session="session-one", service="svc-redis"):
    response = client.post(
        "/api/investigations",
        headers=headers,
        json={
            "serviceId": service,
            "question": "Redis is timing out. What breaks, who should respond, and what worked last time?",
            "sessionId": session,
        },
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_full_contract_seed_graph_services_and_trace(live):
    client, headers, store, _ = live
    assert client.get("/api/health", headers=headers).json()["status"] == "ok"
    assert client.post("/api/seed", headers=headers).json() == {"nodes": 25, "edges": 31}
    graph = client.get("/api/graph", headers=headers).json()
    assert len(graph["nodes"]) == 25
    assert len(graph["edges"]) == 31
    assert all(n["fictional"] for n in graph["nodes"])
    services = client.get("/api/services", headers=headers).json()["services"]
    assert len(services) == 8
    assert {n["id"] for n in services} == {
        n["id"] for n in graph["nodes"] if n["kind"] == "Service"
    }
    result = investigate(client, headers)
    Investigation.model_validate(result)
    assert result["mode"] == "graph-tools"
    assert result["severity"] == "critical"
    assert set(result["impactedServices"]) == {
        "svc-payments",
        "svc-checkout",
        "svc-orders",
        "svc-storefront",
        "svc-notifications",
        "svc-analytics",
    }
    assert set(result["impactedCustomers"]) == {
        "customer-northstar",
        "customer-acme",
        "customer-orbit",
    }
    assert {o["serviceId"] for o in result["owners"]} == {"svc-redis", *result["impactedServices"]}
    assert {e["source"] for e in result["evidence"]} >= {"INC-001", "RUN-001", "DEC-001"}
    assert any(
        e["path"]
        == ["customer-northstar", "svc-storefront", "svc-checkout", "svc-payments", "svc-redis"]
        for e in result["evidence"]
    )
    assert len(result["trace"]) == 7
    for trace in result["trace"]:
        # Replay exactly what the API reports against the real database.
        rows = store.query(trace["query"], trace["params"], read_only=True)
        assert trace["resultCount"] == len(rows)
        assert trace["durationMs"] >= 0
    raw = store.query(
        "MATCH (i:Investigation {id: $id}) RETURN i.json", {"id": result["id"]}, read_only=True
    )[0][0]
    assert Investigation.model_validate_json(raw).id == result["id"]
    assert store.query(
        "MATCH (i:Investigation {id: $id})-[:PROPOSES]->(a:Action)-[:ABOUT]->(:Service) RETURN count(a)",
        {"id": result["id"]},
        read_only=True,
    )[0][0] == len(result["actions"])


def test_topology_toggle_changes_multihop_customer_and_service_impact(live):
    client, headers, _, _ = live
    before = investigate(client, headers)
    toggle = {"source": "svc-payments", "target": "svc-redis", "enabled": False}
    assert client.patch("/api/dependencies", headers=headers, json=toggle).json() == toggle
    after = investigate(client, headers, "session-two")
    assert after["impactedServices"] == ["svc-analytics"]
    assert after["impactedCustomers"] == ["customer-orbit"]
    assert before["severity"] != after["severity"]
    assert len(after["owners"]) == 2
    toggle["enabled"] = True
    assert client.patch("/api/dependencies", headers=headers, json=toggle).status_code == 200
    restored = investigate(client, headers, "session-three")
    assert restored["impactedCustomers"] == before["impactedCustomers"]
    assert restored["impactedServices"] == before["impactedServices"]


def test_memory_changes_actions_across_sessions_and_survives_restart_seed(live):
    client, headers, store, settings = live
    first = investigate(client, headers, "original")
    assert next(a for a in first["actions"] if a["target"] == "RUN-001")["kind"] == "runbook"
    content = "Avoid indiscriminate restarts: last time they lost idempotency tokens."
    response = client.post(
        "/api/memories",
        headers=headers,
        json={
            "serviceId": "svc-redis",
            "content": content,
            "outcome": "avoid",
            "sessionId": "original",
        },
    )
    assert response.status_code == 200, response.text
    memory = response.json()
    helpful = client.post(
        "/api/memories",
        headers=headers,
        json={
            "serviceId": "svc-redis",
            "content": "Pool cap and gradual drain worked",
            "outcome": "helpful",
            "sessionId": "original",
        },
    ).json()
    second = investigate(client, headers, "brand-new-session")
    task = next(a for a in second["actions"] if a["target"] == "RUN-001")
    assert task["kind"] == "review"
    assert content in task["description"]
    assert memory["id"] in task["evidenceIds"]
    assert helpful["id"] in task["evidenceIds"]
    assert len(second["memories"]) == 2
    toggle = {"source": "svc-analytics", "target": "svc-redis", "enabled": False}
    client.patch("/api/dependencies", headers=headers, json=toggle).raise_for_status()
    # New application and driver simulate a process restart. DB is the sole state.
    fresh = Database(settings)
    with TestClient(create_app(settings, fresh)) as restarted:
        assert restarted.post("/api/seed", headers=headers).json() == {"nodes": 25, "edges": 31}
        memories = restarted.get("/api/memories", headers=headers).json()["memories"]
        assert len(memories) == 2
        assert memories[0]["id"] == helpful["id"]
        third = investigate(restarted, headers, "restart-session")
        assert len(third["memories"]) == 2
        assert "customer-orbit" not in third["impactedCustomers"]
        history = restarted.get("/api/investigations", headers=headers).json()["investigations"]
        assert [i["id"] for i in history] == [third["id"], second["id"], first["id"]]
        filtered = restarted.get("/api/investigations?sessionId=original", headers=headers).json()[
            "investigations"
        ]
        assert [i["id"] for i in filtered] == [first["id"]]
    assert (
        store.query("MATCH (m:Memory)-[:ABOUT]->(s:Service) RETURN count(m)", {}, read_only=True)[
            0
        ][0]
        == 2
    )


def test_shared_runbook_keeps_feedback_for_all_linked_services(live):
    client, headers, _, _ = live
    content = "Avoid the payment retry procedure until duplicate charge risk is reviewed."
    memory = client.post(
        "/api/memories",
        headers=headers,
        json={
            "serviceId": "svc-payments",
            "content": content,
            "outcome": "avoid",
            "sessionId": "payments-lesson",
        },
    ).json()
    result = investigate(client, headers)
    # RUN-002 is ABOUT Orders AND Payments. Sorted rows list Orders first.
    task = next(a for a in result["actions"] if a["target"] == "RUN-002")
    assert task["kind"] == "review"
    assert content in task["description"]
    assert memory["id"] in task["evidenceIds"]
    paths = [e["path"] for e in result["evidence"] if e["source"] == "RUN-002"]
    assert ["RUN-002", "svc-orders"] in paths
    assert ["RUN-002", "svc-payments"] in paths


def test_approval_is_idempotent_durable_and_never_mutates_topology(live):
    client, headers, _, settings = live
    result = investigate(client, headers)
    before = client.get("/api/graph", headers=headers).json()
    action_id = result["actions"][0]["id"]
    url = f"/api/actions/{action_id}/approve"
    once = client.post(url, headers=headers)
    twice = client.post(url, headers=headers)
    assert once.status_code == twice.status_code == 200
    assert once.json() == twice.json()
    assert once.json()["status"] == "approved"
    assert client.get("/api/graph", headers=headers).json() == before
    fresh = Database(settings)
    with TestClient(create_app(settings, fresh)) as restarted:
        history = restarted.get("/api/investigations", headers=headers).json()["investigations"]
        assert history[0]["actions"][0]["status"] == "approved"
        assert restarted.post(url, headers=headers).json() == once.json()


def test_workspace_isolation_and_missing_resources(live):
    client, headers, store, _ = live
    item = investigate(client, headers)
    memory = client.post(
        "/api/memories",
        headers=headers,
        json={
            "serviceId": "svc-redis",
            "content": "Use a small pool",
            "outcome": "helpful",
            "sessionId": "a",
        },
    )
    assert memory.status_code == 200
    other_slug = "it-" + uuid4().hex[:24]
    other = {"X-Workspace": other_slug}
    try:
        assert client.get("/api/memories", headers=other).json() == {"memories": []}
        assert client.get("/api/investigations", headers=other).json() == {"investigations": []}
        assert (
            client.post(
                f"/api/actions/{item['actions'][0]['id']}/approve", headers=other
            ).status_code
            == 404
        )
        assert (
            client.post("/api/actions/no-such-action/approve", headers=headers).status_code == 404
        )
        missing_memory = client.post(
            "/api/memories",
            headers=headers,
            json={
                "serviceId": "svc-missing",
                "content": "x",
                "outcome": "helpful",
                "sessionId": "a",
            },
        )
        assert missing_memory.status_code == 404
        missing = client.post(
            "/api/investigations",
            headers=headers,
            json={"serviceId": "svc-missing", "question": "x", "sessionId": "a"},
        )
        assert missing.status_code == 404
        missing_edge = client.patch(
            "/api/dependencies",
            headers=headers,
            json={"source": "svc-redis", "target": "svc-auth", "enabled": False},
        )
        assert missing_edge.status_code == 404
        assert missing.json()["error"]["code"] == "NOT_FOUND"
    finally:
        store.database.client.select_graph(
            store.database.settings.graph_prefix + other_slug
        ).delete()


def test_non_redis_root_is_graph_driven_and_memory_is_scoped(live):
    client, headers, _, _ = live
    response = client.post(
        "/api/memories",
        headers=headers,
        json={
            "serviceId": "svc-redis",
            "sessionId": "older",
            "content": "Redis-specific feedback",
            "outcome": "avoid",
        },
    )
    response.raise_for_status()
    item = investigate(client, headers, service="svc-auth")
    assert item["impactedServices"] == ["svc-checkout", "svc-storefront"]
    assert item["impactedCustomers"] == ["customer-northstar"]
    assert item["memories"] == []
    assert {owner["serviceId"] for owner in item["owners"]} == {
        "svc-auth",
        "svc-checkout",
        "svc-storefront",
    }
    assert not any(e["source"] == "RUN-001" for e in item["evidence"])
    assert not any(a["target"] == "RUN-001" for a in item["actions"])


def test_user_text_is_bound_as_data_not_executable_cypher(live):
    client, headers, _, _ = live
    client.post("/api/seed", headers=headers).raise_for_status()
    before = client.get("/api/graph", headers=headers).json()
    content = "'\" }) MATCH (n) DETACH DELETE n //\nThis is untrusted fictional feedback."
    response = client.post(
        "/api/memories",
        headers=headers,
        json={
            "serviceId": "svc-redis",
            "sessionId": "quote-'session",
            "content": content,
            "outcome": "avoid",
        },
    )
    assert response.status_code == 200, response.text
    assert response.json()["content"] == content
    assert client.get("/api/memories", headers=headers).json()["memories"][0]["content"] == content
    item = investigate(client, headers, "quote-'session")
    assert item["memories"][0]["content"] == content
    assert item["mode"] == "graph-tools"
    assert client.get("/api/graph", headers=headers).json() == before
    filtered = client.get(
        "/api/investigations", headers=headers, params={"sessionId": "quote-'session"}
    ).json()["investigations"]
    assert len(filtered) == 1


def test_customer_paths_honor_six_hop_bound_and_disabled_mid_path(live):
    client, headers, store, _ = live
    client.post("/api/seed", headers=headers).raise_for_status()
    services = [
        {
            "id": f"svc-chain-{i}",
            "label": f"Fictional chain {i}",
            "kind": "Service",
            "status": "healthy",
            "tier": 2,
        }
        for i in range(7)
    ]
    store.query("UNWIND $nodes AS props CREATE (s:Service) SET s += props", {"nodes": services})
    edges = [
        {"source": f"svc-chain-{i}", "target": "svc-redis" if i == 0 else f"svc-chain-{i - 1}"}
        for i in range(7)
    ]
    store.query(
        "UNWIND $edges AS edge MATCH (s:Service {id: edge.source}), (t:Service {id: edge.target}) CREATE (s)-[:DEPENDS_ON {enabled: true}]->(t)",
        {"edges": edges},
    )
    for customer, target in [("customer-six", "svc-chain-4"), ("customer-seven", "svc-chain-5")]:
        store.query(
            "MATCH (s:Service {id: $target}) CREATE (c:Customer {id: $id, label: $id, kind: 'Customer'}) CREATE (c)-[:DEPENDS_ON {enabled: true}]->(s)",
            {"id": customer, "target": target},
        )
    result = investigate(client, headers)
    assert "customer-six" in result["impactedCustomers"]
    assert "customer-seven" not in result["impactedCustomers"]
    assert "svc-chain-5" in result["impactedServices"]
    assert "svc-chain-6" not in result["impactedServices"]
    toggle = {"source": "svc-chain-2", "target": "svc-chain-1", "enabled": False}
    client.patch("/api/dependencies", headers=headers, json=toggle).raise_for_status()
    result = investigate(client, headers, "after-toggle")
    assert "customer-six" not in result["impactedCustomers"]
    assert "svc-chain-4" not in result["impactedServices"]

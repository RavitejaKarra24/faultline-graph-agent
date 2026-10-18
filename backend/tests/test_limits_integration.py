"""Real database list bounds/order checks without shared demo data."""

import json
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from faultline_backend.app import create_app
from faultline_backend.storage import Database

pytestmark = pytest.mark.integration


def test_history_and_memory_limits_and_session_filter(settings):
    database = Database(settings)
    slug = "it-" + uuid4().hex[:24]
    headers = {"X-Workspace": slug}
    store = database.workspace(slug)
    with TestClient(create_app(settings, database)) as client:
        try:
            store.seed()
            response = client.post(
                "/api/investigations",
                headers=headers,
                json={
                    "serviceId": "svc-redis",
                    "sessionId": "original",
                    "question": "What breaks?",
                },
            )
            response.raise_for_status()
            template = response.json()
            # All values are valid contract data, persisted through bound parameters.
            base = datetime.now(UTC) + timedelta(seconds=1)
            history = []
            memories = []
            for i in range(110):
                created_at = (base + timedelta(seconds=i)).isoformat().replace("+00:00", "Z")
                item = {
                    **template,
                    "id": f"inv-limit-{i:03}",
                    "createdAt": created_at,
                    "sessionId": "even" if i % 2 == 0 else "odd",
                    "actions": [],
                }
                history.append(
                    {
                        "id": item["id"],
                        "sessionId": item["sessionId"],
                        "createdAt": created_at,
                        "json": json.dumps(item),
                    }
                )
                memories.append(
                    {
                        "id": f"mem-limit-{i:03}",
                        "createdAt": created_at,
                        "sessionId": "even",
                        "serviceId": "svc-redis",
                        "content": f"Fictional feedback {i}",
                        "outcome": "helpful",
                    }
                )
            store.query(
                "MATCH (s:Service {id: $serviceId}) WITH s UNWIND $items AS props CREATE (i:Investigation) SET i += props CREATE (i)-[:ABOUT]->(s)",
                {"serviceId": "svc-redis", "items": history},
            )
            store.query(
                "MATCH (s:Service {id: $serviceId}) WITH s UNWIND $items AS props CREATE (m:Memory) SET m += props CREATE (m)-[:ABOUT]->(s)",
                {"serviceId": "svc-redis", "items": memories},
            )
            results = client.get("/api/investigations", headers=headers).json()["investigations"]
            assert len(results) == 50
            assert [r["id"] for r in results] == [f"inv-limit-{i:03}" for i in range(109, 59, -1)]
            filtered = client.get("/api/investigations?sessionId=even", headers=headers).json()[
                "investigations"
            ]
            assert len(filtered) == 50
            assert all(r["sessionId"] == "even" for r in filtered)
            assert filtered[0]["id"] == "inv-limit-108"
            listed = client.get("/api/memories", headers=headers).json()["memories"]
            assert len(listed) == 100
            assert [r["id"] for r in listed] == [f"mem-limit-{i:03}" for i in range(109, 9, -1)]
        finally:
            database.client.select_graph(store.graph_name).delete()

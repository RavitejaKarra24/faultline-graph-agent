"""FalkorDB-only persistence. User values are always bound Cypher parameters."""

import json
import logging
from threading import Lock
from time import perf_counter

from falkordb import FalkorDB
from redis.exceptions import RedisError

from .config import Settings, workspace_slug
from .fixture import EDGES, NODES, PUBLIC_KINDS
from .schemas import Action, Investigation, Memory, TraceStep

logger = logging.getLogger(__name__)
_seed_lock = Lock()


class APIError(Exception):
    def __init__(self, code: str, message: str, status: int = 400):
        self.code = code
        self.message = message
        self.status = status
        super().__init__(message)


class Database:
    def __init__(self, settings: Settings):
        self.settings = settings
        self._client = None
        self._client_lock = Lock()

    @property
    def client(self):
        # The official driver connects during construction. Delay until request time
        # so an unavailable DB produces an honest HTTP error, not a startup crash.
        with self._client_lock:
            if self._client is None:
                try:
                    self._client = FalkorDB(
                        host=self.settings.falkordb_host,
                        port=self.settings.falkordb_port,
                        password=(
                            self.settings.falkordb_password.get_secret_value()
                            if self.settings.falkordb_password
                            else None
                        ),
                        socket_connect_timeout=2,
                        socket_timeout=5,
                        max_connections=32,
                    )
                except RedisError as exc:
                    raise APIError("DATABASE_UNAVAILABLE", "FalkorDB is unavailable.", 503) from exc
            return self._client

    def workspace(self, slug: str):
        return Store(self, workspace_slug(slug))

    def health(self):
        # PING alone could incorrectly report a plain Redis server as FalkorDB.
        self.workspace("demo").query("RETURN 1", {})

    def close(self):
        if self._client is not None:
            self._client.connection.close()


class Store:
    def __init__(self, database: Database, slug: str):
        self.database = database
        self.graph_name = database.settings.graph_prefix + slug

    def query(self, query: str, params: dict, *, read_only=False, trace=None, agent="", purpose=""):
        start = perf_counter()
        rows = []
        try:
            graph = self.database.client.select_graph(self.graph_name)
            execute = graph.ro_query if read_only else graph.query
            rows = execute(
                query, params, timeout=self.database.settings.query_timeout_ms
            ).result_set
            return rows
        except RedisError as exc:
            logger.exception("FalkorDB operation failed for %s", self.graph_name)
            raise APIError(
                "DATABASE_UNAVAILABLE",
                "FalkorDB query failed or timed out; no fallback data is used.",
                503,
            ) from exc
        finally:
            step = TraceStep(
                agent=agent or "storage",
                tool="falkordb.ro_query" if read_only else "falkordb.query",
                purpose=purpose or "Persist or retrieve workspace data",
                query=query,
                params=params,
                result_count=len(rows),
                duration_ms=round((perf_counter() - start) * 1000, 3),
            )
            if trace is not None:
                trace.append(step)
            logger.info("graph_tool %s", step.model_dump_json(by_alias=True))

    def ensure_seeded(self):
        # A DB marker, not a process cache: restart never resets toggles or memory.
        with _seed_lock:
            # GRAPH.QUERY can open a new workspace graph; GRAPH.RO_QUERY cannot.
            if not self.query("MATCH (w:Workspace {id: $id}) RETURN w.id", {"id": "fixture-v1"}):
                self.seed()

    def seed(self):
        for kind in PUBLIC_KINDS:
            # Only trusted fixture constants are interpolated as Cypher labels.
            self.query(
                f"UNWIND $nodes AS props MERGE (n:{kind} {{id: props.id}}) ON CREATE SET n += props",
                {"nodes": [n for n in NODES if n["kind"] == kind]},
            )
        for relation in ("DEPENDS_ON", "OWNS", "ON_CALL_FOR", "ABOUT"):
            self.query(
                "UNWIND $edges AS edge MATCH (s {id: edge.source}), (t {id: edge.target}) "
                f"MERGE (s)-[r:{relation}]->(t) ON CREATE SET r.enabled = true",
                {"edges": [{"source": s, "target": t} for s, t, r in EDGES if r == relation]},
            )
        self.query("MERGE (w:Workspace {id: $id})", {"id": "fixture-v1"})
        graph = self.graph()
        return {"nodes": len(graph["nodes"]), "edges": len(graph["edges"])}

    def graph(self):
        nodes = self.query(
            "MATCH (n) WHERE n.kind IN $kinds RETURN properties(n) ORDER BY n.id",
            {"kinds": PUBLIC_KINDS},
            read_only=True,
        )
        edges = self.query(
            "MATCH (s)-[r]->(t) WHERE s.kind IN $kinds AND t.kind IN $kinds "
            "RETURN s.id, t.id, type(r), r.enabled ORDER BY s.id, t.id, type(r)",
            {"kinds": PUBLIC_KINDS},
            read_only=True,
        )
        return {
            "nodes": [r[0] for r in nodes],
            "edges": [
                dict(
                    source=r[0],
                    target=r[1],
                    relation=r[2],
                    **({"enabled": r[3]} if r[3] is not None else {}),
                )
                for r in edges
            ],
        }

    def services(self):
        return [
            r[0]
            for r in self.query(
                "MATCH (s:Service) RETURN properties(s) ORDER BY s.id", {}, read_only=True
            )
        ]

    def require_service(self, service_id):
        rows = self.query(
            "MATCH (s:Service {id: $id}) RETURN properties(s)", {"id": service_id}, read_only=True
        )
        if not rows:
            raise APIError("NOT_FOUND", "Service not found in this workspace.", 404)
        return rows[0][0]

    def toggle_dependency(self, source, target, enabled):
        rows = self.query(
            "MATCH (s {id: $source})-[r:DEPENDS_ON]->(t {id: $target}) "
            "SET r.enabled = $enabled RETURN s.id, t.id, r.enabled",
            {"source": source, "target": target, "enabled": enabled},
        )
        if not rows:
            raise APIError("NOT_FOUND", "Dependency not found in this workspace.", 404)
        return dict(source=source, target=target, enabled=enabled)

    def save_memory(self, memory: Memory):
        rows = self.query(
            "MATCH (s:Service {id: $serviceId}) CREATE (m:Memory {id: $id, serviceId: $serviceId, "
            "content: $content, outcome: $outcome, sessionId: $sessionId, createdAt: $createdAt}) "
            "CREATE (m)-[:ABOUT]->(s) RETURN m.id",
            memory.model_dump(by_alias=True),
        )
        if not rows:
            raise APIError("NOT_FOUND", "Service not found in this workspace.", 404)
        return memory

    def memories(self):
        return [
            Memory.model_validate(r[0])
            for r in self.query(
                "MATCH (m:Memory) RETURN properties(m) ORDER BY m.createdAt DESC, m.id DESC LIMIT 100",
                {},
                read_only=True,
            )
        ]

    def save_investigation(self, investigation: Investigation):
        # One atomic query persists the complete snapshot and independently approvable tasks.
        self.query(
            "MATCH (s:Service {id: $serviceId}) "
            "CREATE (i:Investigation {id: $id, sessionId: $sessionId, createdAt: $createdAt, json: $json}) "
            "CREATE (i)-[:ABOUT]->(s) WITH i, s UNWIND $actions AS task "
            "CREATE (a:Action {id: task.id, status: 'pending', json: task.json}) "
            "CREATE (i)-[:PROPOSES]->(a) CREATE (a)-[:ABOUT]->(s)",
            {
                "serviceId": investigation.service_id,
                "id": investigation.id,
                "sessionId": investigation.session_id,
                "createdAt": investigation.created_at,
                "json": investigation.model_dump_json(by_alias=True),
                "actions": [
                    {"id": a.id, "json": a.model_dump_json(by_alias=True)}
                    for a in investigation.actions
                ],
            },
        )

    def investigations(self, session_id=None):
        rows = self.query(
            "MATCH (i:Investigation) WHERE $sessionId = '' OR i.sessionId = $sessionId "
            "WITH i ORDER BY i.createdAt DESC, i.id DESC LIMIT 50 "
            "OPTIONAL MATCH (i)-[:PROPOSES]->(a:Action) "
            "WITH i, collect({id: a.id, status: a.status}) AS tasks "
            "ORDER BY i.createdAt DESC, i.id DESC RETURN i.json, tasks",
            {"sessionId": session_id or ""},
            read_only=True,
        )
        output = []
        for raw, actions in rows:
            item = Investigation.model_validate_json(raw)
            statuses = {a["id"]: a["status"] for a in actions}
            for action in item.actions:
                action.status = statuses.get(action.id, action.status)
            output.append(item)
        return output

    def approve_action(self, action_id):
        rows = self.query(
            "MATCH (a:Action {id: $id}) SET a.status = 'approved' RETURN a.json, a.status",
            {"id": action_id},
        )
        if not rows:
            raise APIError("NOT_FOUND", "Action not found in this workspace.", 404)
        value = json.loads(rows[0][0])
        value["status"] = rows[0][1]
        return Action.model_validate(value)

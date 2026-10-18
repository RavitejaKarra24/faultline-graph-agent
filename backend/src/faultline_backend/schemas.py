"""Wire schemas; the public contract uses camelCase and rejects extra input."""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints
from pydantic.alias_generators import to_camel

Identifier = Annotated[
    str, StringConstraints(min_length=1, max_length=100, pattern=r"^[A-Za-z0-9][A-Za-z0-9_.:-]*$")
]
SessionId = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
Content = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=2000)]
Outcome = Literal["helpful", "avoid"]
Mode = Literal["graph-tools", "llm"]
NodeKind = Literal["Service", "Team", "Person", "Customer", "Runbook", "Incident", "Decision"]


class Model(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, extra="forbid")


class GraphNode(Model):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, extra="allow")
    id: str
    label: str
    kind: NodeKind
    status: str | None = None
    tier: int | None = None
    description: str | None = None


class GraphEdge(Model):
    source: str
    target: str
    relation: str
    enabled: bool | None = None


class GraphResponse(Model):
    nodes: list[GraphNode]
    edges: list[GraphEdge]


class ServicesResponse(Model):
    services: list[GraphNode]


class SeedResponse(Model):
    nodes: int
    edges: int


class Health(Model):
    status: Literal["ok", "unavailable"]
    database: Literal["FalkorDB"] = "FalkorDB"
    mode: Mode = "graph-tools"
    version: Literal["0.1.0"] = "0.1.0"


class InvestigationInput(Model):
    service_id: Identifier
    question: Content
    session_id: SessionId


class MemoryInput(Model):
    service_id: Identifier
    content: Content
    outcome: Outcome
    session_id: SessionId


class Memory(MemoryInput):
    id: str
    created_at: str


class MemoriesResponse(Model):
    memories: list[Memory]


class DependencyInput(Model):
    source: Identifier
    target: Identifier
    enabled: Annotated[bool, Field(strict=True)]


class Action(Model):
    id: str
    title: str
    description: str
    kind: Literal["notify", "runbook", "review"]
    status: Literal["pending", "approved"] = "pending"
    target: str
    evidence_ids: list[str]


class Owner(Model):
    name: str
    team: str
    service_id: str


class Evidence(Model):
    id: str
    title: str
    detail: str
    path: list[str]
    source: str


class TraceStep(Model):
    agent: str
    tool: str
    purpose: str
    query: str
    params: dict[str, object]
    result_count: int
    duration_ms: float


class Investigation(Model):
    id: str
    service_id: str
    question: str
    session_id: str
    created_at: str
    summary: str
    severity: Literal["critical", "high", "moderate", "low"]
    impacted_services: list[str]
    impacted_customers: list[str]
    owners: list[Owner]
    evidence: list[Evidence]
    actions: list[Action]
    trace: list[TraceStep]
    memories: list[Memory]
    mode: Mode = "graph-tools"
    warnings: list[str]


class InvestigationsResponse(Model):
    investigations: list[Investigation]


class ErrorDetail(Model):
    code: str
    message: str


class ErrorResponse(Model):
    error: ErrorDetail

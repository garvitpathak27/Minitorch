# control_plane/state.py

from dataclasses import dataclass, field


@dataclass
class Workload:
    id: str
    image_path: str
    command: list[str]
    replicas: int
    cpu_limit_percent: float
    memory_limit_bytes: float


@dataclass
class Node:
    id: str
    address: str
    containers: list[str] = field(default_factory=list)
    last_seen: float = 0.0


nodes: dict[str, Node] = {}
workloads: dict[str, Workload] = {}
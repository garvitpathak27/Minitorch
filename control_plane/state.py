from dataclasses import dataclass, field
import time


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


class ClusterState:
    """
    The central Source of Truth for the orchestrator.
    This acts like the Kubernetes API Server reading from etcd.
    """

    def __init__(self):
        self.nodes: dict[str, Node] = {}
        self.workloads: dict[str, Workload] = {}

    def apply_intent(self, intent: dict):
        """
        Takes a validated JSON command from the Raft consensus log
        and updates the desired state of the cluster.
        """
        action = intent.get("action")

        if action == "create_workload":
            w_id = intent.get("id")

            self.workloads[w_id] = Workload(
                id=w_id,
                image_path=intent.get("image_path", "nginx"),
                command=intent.get("command", []),
                replicas=intent.get("replicas", 1),
                cpu_limit_percent=intent.get("cpu_limit_percent", 100.0),
                memory_limit_bytes=intent.get("memory_limit_bytes", 256 * 1024 * 1024),
            )
            print(
                f"[State] 📥 Registered desired workload: {w_id} ({self.workloads[w_id].replicas} replicas)"
            )

        elif action == "delete_workload":
            w_id = intent.get("id")
            if w_id in self.workloads:
                del self.workloads[w_id]
                print(f"[State] 🗑️ Deleted workload target: {w_id}")

        elif action == "register_node":
            n_id = intent.get("node_id")
            
            # --- FIX: Don't overwrite if the node already exists! ---
            if n_id in self.nodes:
                self.nodes[n_id].last_seen = time.time()
                self.nodes[n_id].address = intent.get("address", "")
            else:
                self.nodes[n_id] = Node(
                    id=n_id,
                    address=intent.get("address", ""),
                    last_seen=time.time()
                )
            print(f"[State] 🖥️ Registered/Updated worker node: {n_id}")

        else:
            print(f"[State] Unknown action in intent: {action}")

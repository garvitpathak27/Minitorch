import time
import requests
from control_plane.scheduler import pick_node


class Reconciler:
    def __init__(self, cluster_state):
        """
        Receives the active ClusterState object from main.py
        so it knows what the current desired workloads are.
        """
        self.state = cluster_state

    def reconcile(self):
        """
        Runs continuously (called by main.py).
        Checks actual cluster state vs desired state and issues HTTP commands.
        """

        for node in list(self.state.nodes.values()):
            if time.time() - node.last_seen > 30 and node.containers:
                print(
                    f"⚠️ [Reconciler] Node {node.id} is dead! Clearing its containers for rescheduling."
                )
                node.containers = []

        for workload in list(self.state.workloads.values()):

            actual = sum(
                1
                for node in self.state.nodes.values()
                for cid in node.containers
                if cid.startswith(workload.id)
            )
            desired = workload.replicas

            if actual != desired:
                print(
                    f"🔄 [Reconciler] Workload {workload.id} -> Desired: {desired} | Actual: {actual}"
                )

            if actual < desired:
                for _ in range(desired - actual):
                    alive_nodes = {
                        nid: node
                        for nid, node in self.state.nodes.items()
                        if time.time() - node.last_seen < 30
                    }
                    if not alive_nodes:
                        print("❌ [Reconciler] No alive nodes available to schedule!")
                        break

                    node = pick_node(alive_nodes)
                    if node is None:
                        break

                    try:
                        response = requests.post(
                            f"http://{node.address}/containers",
                            json={
                                "image_path": workload.image_path,
                                "command": workload.command,
                                "cpu_limit_percent": workload.cpu_limit_percent,
                                "memory_limit_bytes": workload.memory_limit_bytes,
                            },
                            timeout=2,
                        )
                        if response.status_code == 201:
                            data = response.json()
                            node.containers.append(f"{workload.id}_{data['id']}")
                            print(
                                f"✅ [Reconciler] Started container {data['id']} on node {node.id}"
                            )
                        else:
                            print(
                                f"⚠️ [Reconciler] Node {node.id} rejected container: {response.text}"
                            )

                    except requests.exceptions.RequestException as e:
                        print(f"⚠️ [Reconciler] Failed to reach node {node.id}: {e}")

            elif actual > desired:
                excess = actual - desired

                for node in self.state.nodes.values():
                    if excess == 0:
                        break

                    to_remove = [
                        cid for cid in node.containers if cid.startswith(workload.id)
                    ]

                    for cid in to_remove:
                        if excess == 0:
                            break

                        real_id = cid.split("_")[1]

                        try:
                            requests.delete(
                                f"http://{node.address}/containers/{real_id}", timeout=2
                            )
                            node.containers.remove(cid)
                            excess -= 1
                            print(
                                f"🛑 [Reconciler] Stopped container {real_id} on node {node.id}"
                            )

                        except requests.exceptions.RequestException as e:
                            print(f"⚠️ [Reconciler] Failed to reach node {node.id}: {e}")

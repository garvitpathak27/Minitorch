import time 
import requests
from control_plane.state import nodes , workloads
from control_plane.scheduler import pick_node


def reconcile_once():
    for node in nodes.values():
        if time.time() - node.last_seen > 30 and node.containers:
            print(f"node {node.id} is dead - clearing its container for rescheduling")
            node.containers = []

    for workload in workloads.values():
        actual = sum(
            1 for node in nodes.values()
            for cid in node.containers
            if cid.startswith(workload.id)
        )
        desired = workload.replicas

        print(f"workload {workload.id} -> desired : {desired} :: actual : {actual}")


        if actual < desired:
            for _ in range(desired - actual):
                alive_nodes = {
                    nid: node for nid , node in nodes.items()
                    if time.time() - node.last_seen < 30
                }
                if not alive_nodes:
                    print("no alive nodes available to schedule ")
                    break

                node  = pick_node(alive_nodes)
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
                        }
                    )
                    if response.status_code == 201:
                        data = response.json()
                        node.containers.append(f"{workload.id}_{data['id']}")
                        print(f"started container {data['id']} on node {node.id}")
                    else:
                        print(f"node {node.id} rejected container: {response.text}")

                except requests.exceptions.RequestException as e:
                    print(f"failed to reach node {node.id}: {e}")
        elif actual > desired:
            excess = actual - desired

            for node in nodes.values():
                if excess == 0:
                    break
                to_remove = [
                    cid for cid in node.containers
                    if cid.startswith(workload.id)

                ]   
                for cid in to_remove:
                    if excess ==0:
                        break

                    real_id = cid.split("_")[1]

                    try:
                        requests.delete(
                            f"http://{node.address}/containers/{real_id}"
                        )
                        node.containers.remove(cid)
                        excess -=1
                        print(f"stopped containder {real_id} on the node {node.id}") 

                    except requests.exceptions.RequestException as e:
                        print(f"failed to reach node {node.id}: {e}")


def reconcile_loop():
    while True:
        try:
            reconcile_once()
        except Exception as e:
            print(f"reconciler error: {e}")
        time.sleep(5)

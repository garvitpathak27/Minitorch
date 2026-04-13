from flask import Flask, request, jsonify
from flask_cors import CORS
import uuid
import threading
from control_plane.state import nodes, workloads, Node, Workload
from control_plane.reconciler import reconcile_loop
import time


app = Flask(__name__)
CORS(app)

@app.route("/nodes", methods=["POST"])
def register_node():
    data = request.json
    node_id = data.get("id")
    address = data.get("address")

    if not node_id or not address:
        return jsonify({"error": "id and address are required"}), 400

    nodes[node_id] = Node(id=node_id, address=address)
    print(f"node registered: {node_id} at {address}")
    return jsonify({"message": f"node {node_id} registered"}), 201


@app.route("/nodes", methods=["GET"])
def list_nodes():
    return jsonify([{
        "id": node.id,
        "address": node.address,
        "containers": node.containers,
        "last_seen": node.last_seen,
    } for node in nodes.values()])


@app.route("/workloads", methods=["POST"])
def create_workload():
    data = request.json
    image_path = data.get("image_path")
    command = data.get("command")
    replicas = data.get("replicas", 1)
    cpu_limit_percent = data.get("cpu_limit_percent", 50.0)
    memory_limit_bytes = data.get("memory_limit_bytes", 100 * 1024 * 1024)

    if not image_path or not command:
        return jsonify({"error": "image_path and command are required"}), 400

    workload_id = str(uuid.uuid4())[:8]
    workloads[workload_id] = Workload(  
        id=workload_id,
        image_path=image_path,
        command=command,
        replicas=replicas,
        cpu_limit_percent=cpu_limit_percent,
        memory_limit_bytes=memory_limit_bytes,
    )

    print(f"workload submitted: {workload_id} replicas={replicas}")
    return jsonify({
        "id": workload_id,
        "image_path": image_path,
        "command": command,
        "replicas": replicas,
    }), 201


@app.route("/workloads", methods=["GET"])
def list_workloads():
    return jsonify([{
        "id": w.id,
        "image_path": w.image_path,
        "command": w.command,
        "replicas": w.replicas,
        "cpu_limit_percent": w.cpu_limit_percent,
        "memory_limit_bytes": w.memory_limit_bytes,
    } for w in workloads.values()])


@app.route("/nodes/heartbeat", methods=["POST"])
def heartbeat():
    data = request.json
    node_id = data.get("id")
    
    if node_id not in nodes:
        return jsonify({"error": "node not registered"}), 404
    
    nodes[node_id].last_seen = time.time()
    return jsonify({"message": "heartbeat received"}), 200


if __name__ == "__main__":
    t = threading.Thread(target=reconcile_loop, daemon=True)
    t.start()
    print("reconciler started in background")

    app.run(host="0.0.0.0", port=6001, debug=False)
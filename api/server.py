"""
What the HTTP Server Does
Right now your runtime is a Python library. You can only use it by importing it in the same Python process. That's not useful for an orchestrator — the control plane needs to talk to node agents running on different machines.
The way processes on different machines talk to each other is over HTTP. Your node agent needs to expose a simple HTTP server so the control plane can say things like:
"start a container on this machine"
"list what containers are running"
"stop this container"


CONTROL PLANE                    NODE AGENT
(different machine)              (your machine)
      │                                │
      │  POST /containers             │
      │ ─────────────────────────────▶│  calls run_container()
      │                                │
      │  GET /containers              │
      │ ─────────────────────────────▶│  calls list_containers()
      │                                │
      │  DELETE /containers/abc123    │
      │ ─────────────────────────────▶│  calls stop_container()
      │                                │


"""

from flask import request, jsonify
from container.runtime import run_container, list_containers, get_container, stop_container
from models.container import ContainerStatus

def register_container_routes(app):

    @app.route("/containers", methods=["POST"])
    def create_container():
        data = request.json
        image_path = data.get("image_path")
        command = data.get("command")
        memory_limit = data.get("memory_limit_bytes", 100*1024*1024)
        cpu_limit = data.get("cpu_limit_percent", 50.0)

        if not image_path or not command:
            return jsonify({"error": "image_path and command are required"}), 400

        container_state = run_container(image_path, command, memory_limit, cpu_limit)
        return jsonify({
            "id": container_state.id,
            "image": container_state.image,
            "pid": container_state.pid,
            "status": container_state.status.value,
            "cpu_limit_percent": container_state.cpu_limit_percent,
            "memory_limit_bytes": container_state.memory_limit_bytes,
        }), 201

    @app.route("/containers", methods=["GET"])
    def list_all_containers():
        containers = list_containers()
        return jsonify([{
            "id": state.id,
            "image": state.image,
            "pid": state.pid,
            "status": state.status.value,
            "cpu_limit_percent": state.cpu_limit_percent,
            "memory_limit_bytes": state.memory_limit_bytes,
        } for state in containers])

    @app.route("/containers/<container_id>", methods=["DELETE"])
    def delete_container(container_id):
        container_state = get_container(container_id)
        if not container_state:
            return jsonify({"error": "container not found"}), 404

        if container_state.status == ContainerStatus.STOPPED:
            return jsonify({"error": "container already stopped"}), 400

        stop_container(container_id)
        return jsonify({"message": f"container {container_id} stopped successfully"})

"""
when i click POST 

{
    "cpu_limit_percent": 50.0,
    "id": "f45bccb0",
    "image": "/tmp/testroot",
    "memory_limit_bytes": 104857600,
    "pid": 25810,
    "status": "running"
}


when i click GET

[
    {
        "cpu_limit_percent": 50.0,
        "id": "f45bccb0",
        "image": "/tmp/testroot",
        "memory_limit_bytes": 104857600,
        "pid": 25899,
        "status": "running"
    }
]



when i clickl delet for a particular id 

    "message": "container f45bccb0 stopped successfully"


"""
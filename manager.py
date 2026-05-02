import subprocess
import os
import signal
from flask import Flask, jsonify, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# Dictionary to track running node processes
processes = {}

NODE_CONFIG = {
    "node1": 5001,
    "node2": 5002,
    "node3": 5003
}

@app.route('/start_node/<node_id>', methods=['POST'])
def start_node(node_id):
    if node_id not in NODE_CONFIG:
        return jsonify({"error": "Unknown node_id"}), 404
    
    if node_id in processes and processes[node_id].poll() is None:
        return jsonify({"message": f"{node_id} is already running"}), 200

    port = NODE_CONFIG[node_id]
    
    # Start main.py as a separate process
    process = subprocess.Popen(
        ["python", "main.py", node_id, str(port)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    processes[node_id] = process
    return jsonify({"status": "started", "node_id": node_id, "port": port}), 200

@app.route('/stop_node/<node_id>', methods=['POST'])
def stop_node(node_id):
    if node_id in processes:
        processes[node_id].terminate()
        del processes[node_id]
        return jsonify({"status": "stopped", "node_id": node_id}), 200
    return jsonify({"error": "Node not running"}), 404

@app.route('/status', methods=['GET'])
def get_status():
    status = {}
    for node_id in NODE_CONFIG.keys():
        is_running = node_id in processes and processes[node_id].poll() is None
        status[node_id] = "running" if is_running else "stopped"
    return jsonify(status), 200

if __name__ == "__main__":
    print("🚀 Node Manager API running on port 8000")
    app.run(port=8000)
"""
Entry point for running a consensus node

Usage:
    python main.py node1 5001
"""

import sys
import json
import threading
import time
import logging
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS

from consensus.types import NodeRole
from consensus.node import ConsensusNode
from consensus.transport import ConsensusTransport, register_consensus_routes
from control_plane.state import ClusterState
from control_plane.reconciler import Reconciler
from api.server import register_container_routes

# ---------------------------------------------------------
# Problem B Fix: Create app instance once at the top level
# ---------------------------------------------------------
app = Flask(__name__)
CORS(app)

logging.getLogger("werkzeug").setLevel(logging.ERROR)

# Argument Parsing
if len(sys.argv) < 3:
    print("Usage: python main.py <node_id> <port>")
    sys.exit(1)

node_id = sys.argv[1]
port = int(sys.argv[2])

# Cluster configuration
cluster = {
    "node1": "http://127.0.0.1:5001",
    "node2": "http://127.0.0.1:5002",
    "node3": "http://127.0.0.1:5003",
}

peers = [n for n in cluster if n != node_id]

# Shared State
cluster_state = ClusterState()

def handle_committed_log(command):
    """
    The bridge: When Raft agrees on a command, it is passed here 
    for the Control Plane to execute.
    """
    print(f"[{node_id}] 🌉 Control Plane received committed command: {command}")

    try:
        intent = json.loads(command) if isinstance(command, str) else command
        if hasattr(cluster_state, "apply_intent"):
            cluster_state.apply_intent(intent)
        else:
            print(f"[{node_id}] ⚠️ ClusterState missing 'apply_intent' method!")
    except Exception as e:
        print(f"[{node_id}] ❌ Failed to parse or apply command: {e}")

# Initialize Consensus and Transport
node = ConsensusNode(node_id, peers, on_commit_callback=handle_committed_log)
transport = ConsensusTransport(node, cluster)
node.send_message = transport.send_message

# Initialize Control Plane Reconciler
reconciler = Reconciler(cluster_state)

# Register routes from other modules
register_consensus_routes(app, transport)
register_container_routes(app)

def run_background_tasks():
    def raft_loop():
        while True:
            now = time.time()
            if node.role != NodeRole.LEADER:
                if now - node.last_heartbeat > node.election_timeout:
                    node.start_election()
            if node.role == NodeRole.LEADER:
                node.send_heartbeats()
            time.sleep(0.3)

    def reconciler_loop():
        while True:
            if hasattr(reconciler, "reconcile"):
                reconciler.reconcile()
            time.sleep(2.0)

    def kubelet_loop():
        """Registers this node with the cluster state."""
        while True:
            register_cmd = {
                "action": "register_node",
                "node_id": node_id,
                "address": f"127.0.0.1:{port}",
            }
            try:
                # Submit via local transport to ensure it goes through Raft
                requests.post(
                    f"http://127.0.0.1:{port}/submit",
                    json={"command": register_cmd},
                    timeout=1,
                )
            except Exception:
                pass
            time.sleep(10)

    threading.Thread(target=raft_loop, daemon=True).start()
    threading.Thread(target=reconciler_loop, daemon=True).start()
    threading.Thread(target=kubelet_loop, daemon=True).start()

# ---------------------------------------------------------
# Problem A Fix: Single join route definition
# ---------------------------------------------------------
@app.route("/join", methods=["POST"])
def join_cluster():
    data = request.json
    new_node_id = data.get("id")
    new_node_url = data.get("url")

    command = {
        "action": "add_node",
        "id": new_node_id,
        "url": new_node_url
    }
    
    # Check for the existence of submit_command or append_command
    if hasattr(node, "submit_command"):
        success = node.submit_command(command)
    else:
        # Fallback if your method name in ConsensusNode is append_command
        success = node.append_command(command)
    
    if success:
        return jsonify({"status": "joined", "message": f"{new_node_id} added"}), 200
    else:
        return jsonify({"status": "error", "message": "Not leader or failed to commit"}), 500

# ---------------------------------------------------------
# Problem C Fix: Added /cluster_state endpoint for frontend
# ---------------------------------------------------------
@app.route("/cluster_state", methods=["GET"])
def get_cluster_state():
    """Returns the current Raft and Node state for the frontend App.jsx."""
    nodes_info = {}
    now = time.time()

    # Build dictionary of nodes and their statuses based on recent heartbeats.
    for nid in cluster.keys():
        last_seen = None

        # Use Raft peer heartbeat timestamps when available.
        if hasattr(node, "peer_last_seen") and nid in node.peer_last_seen:
            last_seen = node.peer_last_seen[nid]

        # Prefer the control-plane view if it has a newer heartbeat.
        if hasattr(cluster_state, "nodes") and nid in cluster_state.nodes:
            cp_last_seen = cluster_state.nodes[nid].last_seen
            if last_seen is None or cp_last_seen > last_seen:
                last_seen = cp_last_seen

        # Assume the local node is alive even before it is registered.
        if nid == node_id:
            is_alive = True
        else:
            is_alive = last_seen is not None and (now - last_seen) < 30

        nodes_info[nid] = {"alive": is_alive}

    state = {
        "term": node.current_term,
        "leader": node.leader_id,
        "role": node.role.name if hasattr(node.role, 'name') else str(node.role),
        "nodes": nodes_info
    }
    return jsonify(state), 200

if __name__ == "__main__":
    run_background_tasks()
    print(f"🚀 Starting {node_id} on port {port}...")
    app.run(host='0.0.0.0', port=port)
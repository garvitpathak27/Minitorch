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
from flask import Flask


from consensus.types import NodeRole
from consensus.node import ConsensusNode
from consensus.transport import ConsensusTransport, register_consensus_routes


from control_plane.state import ClusterState
from control_plane.reconciler import Reconciler


from api.server import register_container_routes

logging.getLogger("werkzeug").setLevel(logging.ERROR)


node_id = sys.argv[1]
port = int(sys.argv[2])


cluster = {
    "node1": "http://127.0.0.1:5001",
    "node2": "http://127.0.0.1:5002",
    "node3": "http://127.0.0.1:5003",
}

peers = [n for n in cluster if n != node_id]


cluster_state = ClusterState()


def handle_committed_log(command):
    """
    This is the bridge! When the Raft cluster agrees on a command,
    it passes it here so the Control Plane can actually execute it.
    """
    print(f"[{node_id}] 🌉 Control Plane received committed command: {command}")

    try:
        intent = json.loads(command) if isinstance(command, str) else command

        if hasattr(cluster_state, "apply_intent"):
            cluster_state.apply_intent(intent)
        else:
            print(
                f"[{node_id}] ⚠️ Note: Make sure ClusterState has an 'apply_intent' method!"
            )

    except Exception as e:
        print(f"[{node_id}] ❌ Failed to parse or apply command: {e}")


node = ConsensusNode(node_id, peers, on_commit_callback=handle_committed_log)
transport = ConsensusTransport(node, cluster)
node.send_message = transport.send_message

reconciler = Reconciler(cluster_state)


app = Flask(__name__)


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
        """
        Continuously tells the Control Plane that this node is alive
        and ready to accept containers.
        """
        while True:
            register_cmd = {
                "action": "register_node",
                "node_id": node_id,
                "address": f"127.0.0.1:{port}",
            }
            try:
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


if __name__ == "__main__":
    run_background_tasks()

    print(f"🚀 Starting {node_id} on port {port}...")
    app.run(port=port)

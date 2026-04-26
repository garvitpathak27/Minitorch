"""
Entry point for running a consensus node

Usage:
    python main.py node1 5001
"""

import sys
from flask import Flask
from consensus.types import NodeRole

from consensus.node import ConsensusNode
from consensus.transport import ConsensusTransport, register_consensus_routes

import logging
logging.getLogger('werkzeug').setLevel(logging.ERROR)
# =====================================================
# Parse arguments
# =====================================================
node_id = sys.argv[1]
port = int(sys.argv[2])

# =====================================================
# Define cluster
# =====================================================
# You can expand this later
cluster = {
    "node1": "http://127.0.0.1:5001",
    "node2": "http://127.0.0.1:5002",
    "node3": "http://127.0.0.1:5003",
}

# peers = all except self
peers = [n for n in cluster if n != node_id]

# =====================================================
# Initialize node + transport
# =====================================================
node = ConsensusNode(node_id, peers)

transport = ConsensusTransport(node, cluster)

# IMPORTANT: bind transport to node
node.send_message = transport.send_message

# =====================================================
# Flask app
# =====================================================
app = Flask(__name__)

# register /message route
register_consensus_routes(app, transport)


# =====================================================
# Start background loop (heartbeat + elections)
# =====================================================
def run_background_tasks():
    import threading
    import time

    def loop():
        while True:
            now = time.time()

            # 🟢 only followers/candidates start election
            if node.role != NodeRole.LEADER:
                if now - node.last_heartbeat > node.election_timeout:
                    node.start_election()

            # 🟢 only leader sends heartbeats
            if node.role == NodeRole.LEADER:
                node.send_heartbeats()

            time.sleep(0.3)

    t = threading.Thread(target=loop, daemon=True)
    t.start()
# =====================================================
# Run
# =====================================================
if __name__ == "__main__":
    run_background_tasks()

    print(f"Starting {node_id} on port {port}")
    app.run(port=port)

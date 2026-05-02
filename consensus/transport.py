"""
Transport Layer

Responsible for:
- Sending messages between nodes (RPC simulation)
- Receiving HTTP requests
- Routing them to ConsensusNode

Acts as:
    network ↔ consensus engine
"""

from flask import Flask, request, jsonify
import requests
import time

from .types import Message, MessageType, LogEntry, NodeRole


class ConsensusTransport:

    def __init__(self, node, address_map: dict):
        """
        node → ConsensusNode instance
        address_map → {node_id: "http://ip:port"}
        """
        self.node = node
        self.address_map = address_map

    def send_message(self, message: Message):

        url = f"{self.address_map[message.destination]}/message"

        self.node.rpc_start_times[message.destination] = time.time()

        try:
            response = requests.post(url, json=self._serialize(message), timeout=1)

            if response and response.content:

                data = response.json()
                reply_msg = self._deserialize(data)

                start = self.node.rpc_start_times.get(reply_msg.source, time.time())
                self.node.weight_manager.record_response(reply_msg.source, start)

                if reply_msg.type == MessageType.REQUEST_VOTE_RESPONSE:
                    self.node.handle_vote_response(reply_msg)

                elif reply_msg.type == MessageType.APPEND_ENTRIES_RESPONSE:
                    self.node.handle_append_entries_response(reply_msg)

                elif reply_msg.type == MessageType.PROXY_APPEND_RESPONSE:

                    self.node.handle_append_entries_response(reply_msg)

        except Exception:

            pass

    def _serialize(self, message: Message):

        return {
            "type": message.type.value,
            "term": message.term,
            "source": message.source,
            "destination": message.destination,
            "prev_log_index": message.prev_log_index,
            "prev_log_term": message.prev_log_term,
            "entries": [
                {"term": e.term, "index": e.index, "command": e.command}
                for e in message.entries
            ],
            "leader_commit": message.leader_commit,
            "vote_granted": message.vote_granted,
            "success": message.success,
            "match_index": message.match_index,
            "proxy_nodes": message.proxy_nodes,
            "weight": message.weight,
            "metadata": message.metadata,
        }

    def _deserialize(self, data: dict) -> Message:

        return Message(
            type=MessageType(data["type"]),
            term=data["term"],
            source=data["source"],
            destination=data["destination"],
            prev_log_index=data.get("prev_log_index"),
            prev_log_term=data.get("prev_log_term"),
            entries=[
                LogEntry(term=e["term"], index=e["index"], command=e["command"])
                for e in data.get("entries", [])
            ],
            leader_commit=data.get("leader_commit"),
            vote_granted=data.get("vote_granted"),
            success=data.get("success"),
            match_index=data.get("match_index"),
            proxy_nodes=data.get("proxy_nodes", []),
            weight=data.get("weight"),
            metadata=data.get("metadata", {}),
        )

    def handle_message(self, data: dict):

        message = self._deserialize(data)

        if message.type == MessageType.REQUEST_VOTE:
            return self._serialize(self.node.handle_vote_request(message))

        elif message.type == MessageType.APPEND_ENTRIES:
            return self._serialize(self.node.handle_append_entries(message))

        elif message.type == MessageType.PROXY_APPEND:

            self.node.handle_proxy_append(message)
            return None

        return None


def register_consensus_routes(app: Flask, transport: ConsensusTransport):

    @app.route("/message", methods=["POST"])
    def receive_message():

        response = transport.handle_message(request.json)

        if response:
            return jsonify(response)

        return "", 200

    @app.route("/submit", methods=["POST"])
    def submit():

        data = request.json
        command = data.get("command")

        node = transport.node

        if node.role == NodeRole.LEADER:
            return jsonify(
                {
                    "success": node.submit_command(command),
                    "handled_by": node.node_id,
                    "role": "leader",
                }
            )

        if node.leader_id:
            leader_url = transport.address_map[node.leader_id]

            try:
                response = requests.post(
                    f"{leader_url}/submit", json={"command": command}, timeout=1
                )

                data = response.json()

                return jsonify(
                    {
                        "success": data.get("success"),
                        "handled_by": node.leader_id,
                        "role": "leader",
                    }
                )

            except Exception:
                return jsonify({"error": "leader unreachable"}), 500

        return jsonify({"error": "no leader known"}), 400

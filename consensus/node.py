"""
ConsensusNode = Core consensus engine

Implements:
- Raft (election, replication, commit)
- Cabinet (weighted quorum)
- RaftOptima (proxy leaders + aggregation)

This file controls EVERYTHING:
- elections
- log replication
- commit decisions
- proxy delegation
"""

from typing import Dict, List, Optional
import time
import random

from .types import Message, MessageType, NodeRole, LogEntry
from .weights import WeightManager
import json
import os


class ConsensusNode:

    def __init__(self, node_id: str, peers: List[str], on_commit_callback=None):

        self.node_id = node_id
        self.peers = peers

        self.current_term = 0
        self.voted_for: Optional[str] = None
        self.log: List[LogEntry] = []

        self.commit_index = -1
        self.last_applied = -1

        self.next_index: Dict[str, int] = {}
        self.match_index: Dict[str, int] = {}

        self.role = NodeRole.FOLLOWER
        self.last_heartbeat = time.time()
        self.election_timeout = random.uniform(1.5, 3.0)

        self.weight_manager = WeightManager([node_id] + peers)

        self.pending_votes: List[str] = []

        self.proxy_leaders: List[str] = []
        self.proxy_map: Dict[str, List[str]] = {}

        self.proxy_nodes: List[str] = []
        self.proxy_expected: List[str] = []
        self.proxy_responses: Dict[str, Message] = {}

        self.leader_id: Optional[str] = None

        self.rpc_start_times = {}

        self.repeated_election_attempts = 0
        self.MAX_ELECTION_ATTEMPTS = 5
        self.is_muted = False

        self.MEMBER_TIMEOUT = 10.0
        self.peer_last_seen: Dict[str, float] = {peer: time.time() for peer in peers}

        self.on_commit_callback = on_commit_callback

        self.load_state()

    def _state_file(self):
        return f"node_{self.node_id}_state.json"

    def save_state(self):
        data = {
            "term": self.current_term,
            "voted_for": self.voted_for,
            "log": [
                {"term": e.term, "index": e.index, "command": e.command}
                for e in self.log
            ],
        }
        with open(self._state_file(), "w") as f:
            json.dump(data, f)

    def load_state(self):
        if not os.path.exists(self._state_file()):
            return

        with open(self._state_file(), "r") as f:
            data = json.load(f)

        self.current_term = data["term"]
        self.voted_for = data["voted_for"]
        self.log = [LogEntry(e["term"], e["index"], e["command"]) for e in data["log"]]
        print(
            f"[{self.node_id}] state loaded | term={self.current_term} log_len={len(self.log)}"
        )

    def start_election(self):

        if self.is_muted:
            print(f"Node {self.node_id} is muted . skipping elections")
            return

        self.repeated_election_attempts += 1

        if self.repeated_election_attempts > self.MAX_ELECTION_ATTEMPTS:
            print(
                f"Node {self.node_id} failed {self.MAX_ELECTION_ATTEMPTS} election in a row. Assuming network issues and muting itself."
            )
            self.is_muted = True
            self.role = NodeRole.FOLLOWER
            return

        self.role = NodeRole.CANDIDATE
        self.current_term += 1
        self.voted_for = self.node_id
        self.save_state()
        self.pending_votes = [self.node_id]
        self.last_heartbeat = time.time()

        for peer in self.peers:
            self.send_message(
                Message(
                    type=MessageType.REQUEST_VOTE,
                    term=self.current_term,
                    source=self.node_id,
                    destination=peer,
                )
            )

        print(f"[{self.node_id}] START election | term={self.current_term}")

    def handle_vote_request(self, message: Message):

        if message.term < self.current_term:
            return Message(
                type=MessageType.REQUEST_VOTE_RESPONSE,
                term=self.current_term,
                source=self.node_id,
                destination=message.source,
                vote_granted=False,
            )

        if message.term > self.current_term:
            self.current_term = message.term
            self.voted_for = None
            self.role = NodeRole.FOLLOWER
            self.save_state()

        if self.voted_for is None or self.voted_for == message.source:
            self.voted_for = message.source
            self.save_state()
            return Message(
                type=MessageType.REQUEST_VOTE_RESPONSE,
                term=self.current_term,
                source=self.node_id,
                destination=message.source,
                vote_granted=True,
            )

        return Message(
            type=MessageType.REQUEST_VOTE_RESPONSE,
            term=self.current_term,
            source=self.node_id,
            destination=message.source,
            vote_granted=False,
        )

    def handle_vote_response(self, message: Message):

        if self.role != NodeRole.CANDIDATE:
            return

        if message.vote_granted:
            self.pending_votes.append(message.source)

            self.weight_manager.compute_weights()

            if self.weight_manager.quorum_reached(self.pending_votes):
                self.become_leader()

        print(f"[{self.node_id}] vote from {message.source} → {message.vote_granted}")

    def become_leader(self):

        self.role = NodeRole.LEADER
        self.leader_id = self.node_id
        self.last_heartbeat = time.time()

        for peer in self.peers:
            self.next_index[peer] = len(self.log)
            self.match_index[peer] = -1

        self._appoint_proxies()
        self.send_heartbeats()

        print(f"[{self.node_id}] 🚀 BECAME LEADER")

    def _appoint_proxies(self):

        num_proxies = max(1, len(self.peers) // 2)
        self.proxy_leaders = self.peers[:num_proxies]

        followers = [p for p in self.peers if p not in self.proxy_leaders]

        for i, follower in enumerate(followers):
            proxy = self.proxy_leaders[i % len(self.proxy_leaders)]
            self.proxy_map.setdefault(proxy, []).append(follower)

        for proxy, nodes in self.proxy_map.items():
            self.send_message(
                Message(
                    type=MessageType.PROXY_APPEND,
                    term=self.current_term,
                    source=self.node_id,
                    destination=proxy,
                    proxy_nodes=nodes,
                )
            )

    def submit_command(self, command):

        if self.role != NodeRole.LEADER:
            return False

        entry = LogEntry(self.current_term, len(self.log), command)
        self.log.append(entry)
        self.save_state()

        print(f"[{self.node_id}] appended {command}")

        self.replicate_log()
        return True

    def replicate_log(self):

        targets = self.proxy_leaders if self.proxy_leaders else self.peers

        for node in targets:

            prev_index = len(self.log) - 2
            prev_term = self.log[prev_index].term if prev_index >= 0 else 0

            self.send_message(
                Message(
                    type=MessageType.APPEND_ENTRIES,
                    term=self.current_term,
                    source=self.node_id,
                    destination=node,
                    prev_log_index=prev_index,
                    prev_log_term=prev_term,
                    entries=[self.log[-1]],
                    leader_commit=self.commit_index,
                )
            )

    def handle_append_entries(self, message: Message):
        """
        Handles incoming AppendEntries messages from the leader.
        This serves as both a heartbeat (empty entries) and the mechanism for log replication.
        """

        self.leader_id = message.source

        if message.term < self.current_term:
            return

        self.repeated_election_attempts = 0

        if self.is_muted:
            print(
                f"[{self.node_id}] Network healed! Heard leader {message.source}. Unmuting."
            )
            self.is_muted = False

        if self.role != NodeRole.PROXY:
            self.role = NodeRole.FOLLOWER

        self.last_heartbeat = time.time()

        if message.prev_log_index != -1:
            if message.prev_log_index >= len(self.log):
                return Message(
                    type=MessageType.APPEND_ENTRIES_RESPONSE,
                    term=self.current_term,
                    source=self.node_id,
                    destination=message.source,
                    success=False,
                )

        if message.entries:
            self.log = self.log[: message.prev_log_index + 1]
            self.log.extend(message.entries)

            self.save_state()

        if (
            message.leader_commit is not None
            and message.leader_commit > self.commit_index
        ):

            self.commit_index = min(message.leader_commit, len(self.log) - 1)

            self.apply_committed_entries()

        if self.role == NodeRole.PROXY and self.proxy_nodes:

            self.proxy_responses = {}

            for follower in self.proxy_nodes:
                print(f"[{self.node_id}] forwarding → {follower}")

                self.send_message(
                    Message(
                        type=MessageType.APPEND_ENTRIES,
                        term=self.current_term,
                        source=self.node_id,
                        destination=follower,
                        prev_log_index=message.prev_log_index,
                        prev_log_term=message.prev_log_term,
                        entries=message.entries,
                        leader_commit=message.leader_commit,
                    )
                )

        return Message(
            type=MessageType.APPEND_ENTRIES_RESPONSE,
            term=self.current_term,
            source=self.node_id,
            destination=message.source,
            success=True,
            match_index=len(self.log) - 1,
        )

    def handle_append_entries_response(self, message: Message):

        self.peer_last_seen[message.source] = time.time()

        if self.role == NodeRole.PROXY:

            self.proxy_responses[message.source] = message

            if len(self.proxy_responses) < len(self.proxy_nodes):
                return

            success = all(r.success for r in self.proxy_responses.values())
            match_index = min(r.match_index for r in self.proxy_responses.values())

            print(f"[{self.node_id}] aggregated response → leader")

            self.send_message(
                Message(
                    type=MessageType.PROXY_APPEND_RESPONSE,
                    term=self.current_term,
                    source=self.node_id,
                    destination=self.leader_id,
                    success=success,
                    match_index=match_index,
                )
            )

            self.proxy_responses = {}
            return

        if self.role != NodeRole.LEADER:
            return

        if not message.success:

            self.next_index[message.source] = max(
                0, self.next_index[message.source] - 1
            )

            retry_index = self.next_index[message.source] - 1

            retry_term = (
                self.log[retry_index].term
                if retry_index >= 0 and retry_index < len(self.log)
                else 0
            )

            entries = self.log[self.next_index[message.source] :]

            print(
                f"[{self.node_id}] retrying → {message.source} from index {self.next_index[message.source]}"
            )

            self.send_message(
                Message(
                    type=MessageType.APPEND_ENTRIES,
                    term=self.current_term,
                    source=self.node_id,
                    destination=message.source,
                    prev_log_index=retry_index,
                    prev_log_term=retry_term,
                    entries=entries,
                    leader_commit=self.commit_index,
                )
            )

            return

        self.match_index[message.source] = message.match_index
        self.next_index[message.source] = message.match_index + 1

        self._update_commit_index()

    def send_heartbeats(self):

        if self.role != NodeRole.LEADER:
            return

        current_time = time.time()
        dead_nodes = []

        for peer, last_seen in list(self.peer_last_seen.items()):
            if current_time - last_seen > self.MEMBER_TIMEOUT:
                dead_nodes.append(peer)

        if dead_nodes:
            for dead_node in dead_nodes:
                print(
                    f"[{self.node_id}] ⚠️ Peer {dead_node} timed out! Evicting from cluster."
                )

                if dead_node in self.peers:
                    self.peers.remove(dead_node)
                if dead_node in self.peer_last_seen:
                    del self.peer_last_seen[dead_node]

                if dead_node in self.proxy_leaders:
                    self.proxy_leaders.remove(dead_node)

            self.weight_manager = WeightManager([self.node_id] + self.peers)

            self._appoint_proxies()

        for peer in self.proxy_leaders if self.proxy_leaders else self.peers:

            next_idx = self.next_index.get(peer, len(self.log))

            prev_index = next_idx - 1
            prev_term = (
                self.log[prev_index].term
                if prev_index >= 0 and prev_index < len(self.log)
                else 0
            )

            entries = self.log[next_idx:]

            self.send_message(
                Message(
                    type=MessageType.APPEND_ENTRIES,
                    term=self.current_term,
                    source=self.node_id,
                    destination=peer,
                    prev_log_index=prev_index,
                    prev_log_term=prev_term,
                    entries=entries,
                    leader_commit=self.commit_index,
                )
            )

    def _update_commit_index(self):

        for i in range(len(self.log) - 1, self.commit_index, -1):

            replicated = [self.node_id]

            for peer, idx in self.match_index.items():
                if idx >= i:
                    replicated.append(peer)

            self.weight_manager.compute_weights()

            if self.weight_manager.quorum_reached(replicated):
                self.commit_index = i
                print(f"[{self.node_id}] COMMITTED index {i}")
                self.apply_committed_entries()
                break

    def apply_committed_entries(self):

        while self.last_applied < self.commit_index:
            self.last_applied += 1
            entry = self.log[self.last_applied]
            print(f"[{self.node_id}] APPLIED: {entry.command}")
            if self.on_commit_callback:

                self.on_commit_callback(entry.command)

        self.compact_log()

    def handle_proxy_append(self, message: Message):
        """
        Handles the PROXY_APPEND message sent by the leader
        to assign this node as a proxy.
        """

        if message.term < self.current_term:
            return

        if message.term > self.current_term:
            self.current_term = message.term
            self.voted_for = None
            self.save_state()

        self.role = NodeRole.PROXY
        self.leader_id = message.source
        self.proxy_nodes = message.proxy_nodes
        self.last_heartbeat = time.time()

        print(
            f"[{self.node_id}] 🛡️ Appointed as PROXY by {self.leader_id} for nodes: {self.proxy_nodes}"
        )

    def compact_log(self):
        """
        Prevents Out-Of-Memory (OOM) crashes by deleting the heavy container
        payloads from old, finalized log entries, while keeping the array
        size intact so Raft's index math doesn't break.
        """
        MAX_RETAINED_LOGS = 50

        if len(self.log) > MAX_RETAINED_LOGS:

            safe_wipe_index = self.commit_index - MAX_RETAINED_LOGS

            compaction_occurred = False

            for i in range(safe_wipe_index):
                if self.log[i].command != "COMPACTED":
                    self.log[i].command = "COMPACTED"
                    compaction_occurred = True

            if compaction_occurred:
                print(
                    f"[{self.node_id}] 🗜️ Log compacted. Cleaned up payloads before index {safe_wipe_index}."
                )
                self.save_state()

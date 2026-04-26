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

    def __init__(self, node_id: str, peers: List[str]):

        # =========================
        # Identity
        # =========================
        self.node_id = node_id
        self.peers = peers

        # =========================
        # Raft persistent state
        # =========================
        self.current_term = 0
        self.voted_for: Optional[str] = None
        self.log: List[LogEntry] = []

        # =========================
        # Raft volatile state
        # =========================
        self.commit_index = -1
        self.last_applied = -1

        # =========================
        # Leader state
        # =========================
        self.next_index: Dict[str, int] = {}
        self.match_index: Dict[str, int] = {}

        # =========================
        # Role + timing
        # =========================
        self.role = NodeRole.FOLLOWER
        self.last_heartbeat = time.time()
        self.election_timeout = random.uniform(1.5, 3.0)

        # =========================
        # Cabinet (weights)
        # =========================
        self.weight_manager = WeightManager([node_id] + peers)

        # =========================
        # Election tracking
        # =========================
        self.pending_votes: List[str] = []

        # =========================
        # Proxy system
        # =========================
        self.proxy_leaders: List[str] = []
        self.proxy_map: Dict[str, List[str]] = {}

        # Proxy aggregation state
        self.proxy_nodes: List[str] = []
        self.proxy_expected: List[str] = []
        self.proxy_responses: Dict[str, Message] = {}

        # =========================
        # Leader tracking
        # =========================
        self.leader_id: Optional[str] = None

        # =========================
        # Latency tracking (Cabinet)
        # =========================
        self.rpc_start_times = {}

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
        self.log = [
            LogEntry(e["term"], e["index"], e["command"])
            for e in data["log"]
        ]
        print(f"[{self.node_id}] state loaded | term={self.current_term} log_len={len(self.log)}")
    
    
    # =====================================================
    # Election
    # =====================================================
    def start_election(self):
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

    # =====================================================
    # Become Leader
    # =====================================================
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

    # =====================================================
    # Proxy assignment
    # =====================================================
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

    # =====================================================
    # Heartbeats
    # =====================================================
    def send_heartbeats(self):

        if self.role != NodeRole.LEADER:
            return

        for peer in self.proxy_leaders if self.proxy_leaders else self.peers:

            next_idx = self.next_index.get(peer, len(self.log))

            prev_index = next_idx - 1
            prev_term = (
                self.log[prev_index].term
                if prev_index >= 0 and prev_index < len(self.log)
                else 0
            )

            # 🧠 KEY: send missing entries if follower is behind
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
    # =====================================================
    # Client command
    # =====================================================
    def submit_command(self, command):

        if self.role != NodeRole.LEADER:
            return False

        entry = LogEntry(self.current_term, len(self.log), command)
        self.log.append(entry)
        self.save_state()

        print(f"[{self.node_id}] appended {command}")

        self.replicate_log()
        return True

    # =====================================================
    # Replication (Leader → Proxy)
    # =====================================================
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

    # =====================================================
    # Handle append entries (Follower / Proxy)
    # =====================================================
    
    def handle_append_entries(self, message: Message):
            """
            Handles incoming AppendEntries messages from the leader.
            This serves as both a heartbeat (empty entries) and the mechanism for log replication.
            """
            
            # 1. Acknowledge the leader's identity so we know who to route client requests to
            self.leader_id = message.source

            # 2. Term Check (Raft Safety Rule)
            # If the incoming message is from an older term, reject it. 
            # This prevents "ghost" leaders from a partitioned network from overwriting good data.
            if message.term < self.current_term:
                return Message(
                    type=MessageType.APPEND_ENTRIES_RESPONSE,
                    term=self.current_term,
                    source=self.node_id,
                    destination=message.source,
                    success=False,
                )

            # 3. Role & Timeout Reset
            # If we are a candidate or leader but see a valid AppendEntries, we must step down to follower.
            # Note: We preserve the PROXY role if we have been appointed one by the leader.
            if self.role != NodeRole.PROXY:
                self.role = NodeRole.FOLLOWER

            # Reset the election timer so we don't start an election while the leader is active.
            self.last_heartbeat = time.time()

            # 4. Log Consistency Check (Raft Safety Rule)
            # We must ensure our log matches the leader's log up to the point of `prev_log_index`.
            # If we are missing entries (our log is shorter than prev_log_index), we reject.
            # The leader will then backtrack and send earlier entries until we match.
            if message.prev_log_index != -1:
                if message.prev_log_index >= len(self.log):
                    return Message(
                        type=MessageType.APPEND_ENTRIES_RESPONSE,
                        term=self.current_term,
                        source=self.node_id,
                        destination=message.source,
                        success=False,
                    )

            # 5. Append New Entries & Persist
            # If the leader sent new logs, slice off any conflicting uncommitted logs 
            # (everything after prev_log_index) and append the new authoritative entries.
            if message.entries:
                self.log = self.log[: message.prev_log_index + 1]
                self.log.extend(message.entries)
                
                # Save to disk immediately so we don't lose data if we crash right after this
                self.save_state()   

            # 6. Commit & Apply (The Fix)
            # If the leader tells us that logs have been securely committed across the cluster,
            # we must update our own commit index. 
            if message.leader_commit is not None and message.leader_commit > self.commit_index:
                # We commit up to the leader's index, OR the end of our own log (whichever is smaller)
                # This prevents us from trying to commit logs we haven't received yet.
                self.commit_index = min(message.leader_commit, len(self.log) - 1)
                
                # Now actually execute those commands in the state machine
                self.apply_committed_entries()

            # 7. Proxy Forwarding (Custom RaftOptima Logic)
            # If this node is a designated proxy, it must forward this heartbeat/payload
            # to its assigned sub-followers to relieve network pressure on the main leader.
            if self.role == NodeRole.PROXY and self.proxy_nodes:
                
                # Reset responses tracker for this specific broadcast
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
                            leader_commit=message.leader_commit, # Pass down the commit index!
                        )
                    )

            # 8. Success Response
            # Tell the leader (or proxy) that we successfully processed the heartbeat/append.
            # We include our current log length so the leader knows exactly where we are.
            return Message(
                type=MessageType.APPEND_ENTRIES_RESPONSE,
                term=self.current_term,
                source=self.node_id,
                destination=message.source,
                success=True,
                match_index=len(self.log) - 1,
            )
    
    # =====================================================
    # Handle responses
    # =====================================================
    def handle_append_entries_response(self, message: Message):

        # ===== PROXY AGGREGATION =====
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

        # ===== LEADER HANDLING =====
        if self.role != NodeRole.LEADER:
            return

        # ✅ FIXED RETRY LOGIC (SAFE)
        if not message.success:

            # prevent negative index
            self.next_index[message.source] = max(
                0, self.next_index[message.source] - 1
            )

            retry_index = self.next_index[message.source] - 1

            retry_term = (
                self.log[retry_index].term
                if retry_index >= 0 and retry_index < len(self.log)
                else 0
            )

            entries = self.log[self.next_index[message.source]:]

            print(f"[{self.node_id}] retrying → {message.source} from index {self.next_index[message.source]}")

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

        # success case
        self.match_index[message.source] = message.match_index
        self.next_index[message.source] = message.match_index + 1

        self._update_commit_index()
    # =====================================================
    # Commit logic
    # =====================================================
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

    # =====================================================
    # Apply
    # =====================================================
    def apply_committed_entries(self):

        while self.last_applied < self.commit_index:
            self.last_applied += 1
            entry = self.log[self.last_applied]
            print(f"[{self.node_id}] APPLIED: {entry.command}")

# =====================================================
    # Handle Proxy Assignment
    # =====================================================
    def handle_proxy_append(self, message: Message):
        """
        Handles the PROXY_APPEND message sent by the leader 
        to assign this node as a proxy.
        """
        # Ignore outdated terms
        if message.term < self.current_term:
            return

        # Update term if the message is from a newer term
        if message.term > self.current_term:
            self.current_term = message.term
            self.voted_for = None
            self.save_state()

        # Update state to become a proxy
        self.role = NodeRole.PROXY
        self.leader_id = message.source
        self.proxy_nodes = message.proxy_nodes
        self.last_heartbeat = time.time()

        print(f"[{self.node_id}] 🛡️ Appointed as PROXY by {self.leader_id} for nodes: {self.proxy_nodes}")
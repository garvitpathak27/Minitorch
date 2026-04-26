from enum import Enum
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any


@dataclass
class LogEntry:
    term: int
    index: int
    command: object


class NodeRole(str, Enum):
    FOLLOWER = "follower"
    CANDIDATE = "candidate"
    LEADER = "leader"
    PROXY = "proxy"


class MessageType(str, Enum):
    REQUEST_VOTE = "request_vote"
    REQUEST_VOTE_RESPONSE = "request_vote_response"

    APPEND_ENTRIES = "append_entries"
    APPEND_ENTRIES_RESPONSE = "append_entries_response"

    PROXY_APPEND = "proxy_append"
    PROXY_APPEND_RESPONSE = "proxy_append_response"

    CONFIG_CHANGE = "config_change"


@dataclass
class Message:
    type: MessageType
    term: int
    source: str
    destination: str

    prev_log_index: Optional[int] = None
    prev_log_term: Optional[int] = None
    entries: List[LogEntry] = field(default_factory=list)
    leader_commit: Optional[int] = None

    vote_granted: Optional[bool] = None

    success: Optional[bool] = None
    match_index: Optional[int] = None

    proxy_nodes: List[str] = field(default_factory=list)
    weight: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

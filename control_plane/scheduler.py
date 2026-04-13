# control_plane/scheduler.py

from control_plane.state import Node


def pick_node(nodes: dict) -> Node | None:
    if not nodes:
        return None
    return min(nodes.values(), key=lambda node: len(node.containers))
import time


class WeightManager:

    def __init__(self, nodes: list[str]):
        self.nodes = nodes
        self.weights = {node: 1.0 for node in nodes}
        self.response_times = {node: [] for node in nodes}
        self.response_order = []

    def record_response(self, node: str, start_time: float):
        latency = time.time() - start_time
        self.response_times[node].append(latency)
        self.response_order.append(node)

    def compute_weights(self):
        if not self.response_order:
            return

        total = len(self.response_order)

        for i, node in enumerate(self.response_order):
            self.weights[node] = total - i

        total_weight = sum(self.weights.values())

        for node in self.weights:
            self.weights[node] /= total_weight

        self.response_order.clear()

    def quorum_reached(self, responding_nodes: list[str]) -> bool:
        total_weight = sum(self.weights.values())
        responding_weight = sum(self.weights[node] for node in responding_nodes)
        return responding_weight >= (total_weight / 2)

import subprocess
import time

nodes = [
    ("node1", 5001),
    ("node2", 5002),
    ("node3", 5003),
]

procs = []

for node, port in nodes:
    p = subprocess.Popen(["python3", "main.py", node, str(port)])
    procs.append(p)
    time.sleep(0.5)

print("Cluster started. Ctrl+C to stop.")

try:
    for p in procs:
        p.wait()
except KeyboardInterrupt:
    for p in procs:
        p.kill()
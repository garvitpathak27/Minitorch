
# 🚢 MiniOrch: A Distributed Container Orchestrator & Consensus Engine

![Python](https://img.shields.io/badge/Python-3.10+-blue?style=flat-square&logo=python)
![React](https://img.shields.io/badge/React-Vite-blue?style=flat-square&logo=react)
![Linux](https://img.shields.io/badge/Linux-Namespaces%20%7C%20Cgroups-orange?style=flat-square&logo=linux)
![Status](https://img.shields.io/badge/Status-Self%20Healing-success?style=flat-square)
![Consensus](https://img.shields.io/badge/Consensus-Raft%20%7C%20RaftOptima-purple?style=flat-square)

**MiniOrch** is a custom, Kubernetes-inspired distributed container orchestrator and distributed state machine built entirely from scratch in Python. 

Bypassing high-level abstractions like Docker, it interacts directly with the Linux kernel using raw syscalls, namespaces, and cgroups v2 for true process isolation. Furthermore, it features a custom-built distributed consensus layer implementing **Raft**, **Cabinet (Weighted Quorums)**, and **RaftOptima (Proxy Leaders)** to manage fault-tolerant cluster state.

This project demonstrates a foundational understanding of cloud-native infrastructure, featuring a central control plane with a continuous reconciliation loop, heartbeat monitoring for automated self-healing, and a live React dashboard.

---

## ✨ Key Features

### 🐳 Container Orchestration
* **Custom Container Runtime:** Built from scratch using `os.fork()` and Linux kernel primitives. Isolates processes via `PID`, `UTS`, `NET`, `MNT`, and `IPC` namespaces.
* **Filesystem Isolation:** Implements `pivot_root` and bind mounts to provide containers with completely isolated root filesystems.
* **Resource Constraints:** Directly programs the Linux `cgroups v2` virtual filesystem to enforce strict CPU quotas and Memory limits.
* **Distributed Control Plane & Scheduler:** Accepts user workloads and schedules them across available worker nodes using a "least-loaded" placement algorithm.
* **Continuous Reconciliation & Self-Healing:** A background control loop constantly monitors node heartbeats (every 5s). If a node dies (30s timeout), its containers are automatically rescheduled onto healthy nodes to fix the drift between Desired and Actual state.
* **Real-Time React UI:** A single-page application providing a live map of desired workloads, cluster health, and dynamic container placement.

### 🗳️ Distributed Consensus Engine
* **Raft Consensus Implementation:** Features full leader election, log replication, heartbeat monitoring, and term tracking for distributed fault tolerance.
* **State Persistence:** Nodes save term data, votes, and committed log entries to disk (`state.json`) to recover gracefully from crashes.
* **RaftOptima (Proxy Leaders):** Enhances standard Raft by appointing "Proxy Leaders." The main leader replicates logs only to proxies, who then broadcast to sub-followers, drastically reducing network bottlenecks.
* **Cabinet (Weighted Quorums):** Implements dynamic weight management to allow nodes with higher reliability or better latency to have stronger voting power during elections and log commits.

---

## 🏗️ Architecture

MiniOrch operates on two main planes: the **Control/Orchestration Plane** and the **State/Consensus Plane**.

```text
YOU (React Dashboard)               CONTROL PLANE (Port 6001)               NODE AGENTS (Ports 5000, 5001)
 │                                       │                                       │
 │  POST /workloads (Desired State)      │                                       │
 │──────────────────────────────────────▶│  workloads["app"] = Replicas: 3       │
 │                                       │                                       │
 │                                       │  [Reconciler Loop Wakes Up]           │
 │                                       │  Actual: 0, Desired: 3                │
 │                                       │  POST /containers ───────────────────▶│  fork() + Namespaces
 │                                       │  POST /containers ───────────────────▶│  Cgroups limits applied
 │                                       │  POST /containers ───────────────────▶│  execvp("command")
 │                                       │                                       │
 │                                       │  ◀─────────────────── Heartbeat (5s) ─│

-------------------------------------------------------------------------------------------------------

CONSENSUS CLUSTER (Ports 5001, 5002, 5003)
                                  
      [ Node 1 (Leader) ] ─────────▶ [ Node 2 (Proxy) ] ────────▶ [ Node 3 (Follower) ]
           │   (Appends Log)                 │   (Forwards Log)
           │                                 ▼
           └───────────────────────▶ [ Node 4 (Proxy) ] ────────▶ [ Node 5 (Follower) ]
```

---

## 🛠️ Tech Stack

| Component | Technology |
|-----------|------------|
| **Container Runtime** | Python 3.10+, Linux Kernel API (os.fork, execvp, ctypes, syscalls) |
| **Process Isolation** | Linux Namespaces (PID, UTS, NET, MNT, IPC), Cgroups v2 |
| **Networking & API** | Flask, HTTP/REST, `requests` |
| **Consensus State** | Custom Raft/RaftOptima Engine, JSON Persistence |
| **Frontend UI** | React 18+, Vite, JavaScript |
| **Root Filesystem** | Ubuntu Cloud Image or Alpine Mini Rootfs |

---

## 🚀 Getting Started

### Prerequisites
- **Linux environment** (strictly required for native namespaces and cgroups)
- **sudo privileges** (required to execute kernel-level isolation)
- **Python 3.10+** and **Node.js**
- An extracted Linux rootfs (e.g., Ubuntu Cloud Image or Alpine Mini Rootfs)

### 1. Installation & Setup

Clone the repository and set up the backend:
```bash
git clone https://github.com/garvitpathak27/minitorch.git
cd minitorch

python3 -m venv venv
source venv/bin/activate
pip install flask flask-cors requests
```

Set up the React Frontend:
```bash
cd frontend
npm install
```

Set up the Root Filesystem (Alpine Example):
```bash
mkdir -p /tmp/testroot
cd /tmp
wget https://dl-cdn.alpinelinux.org/alpine/v3.19/releases/x86_64/alpine-minirootfs-3.19.0-x86_64.tar.gz
sudo tar xzf alpine-minirootfs-3.19.0-x86_64.tar.gz -C testroot
```

---

## 🏃 Running the Infrastructure

To simulate the distributed system locally, open multiple terminal windows. 

### Part A: Start the Container Orchestrator

**Terminal 1:** Start the Control Plane
```bash
sudo venv/bin/python3 -m control_plane.api.server
```

**Terminals 2 & 3:** Start Worker Nodes
```bash
sudo venv/bin/python3 -m api.server 5000
sudo venv/bin/python3 -m api.server 5001
```

**Terminal 4:** Start the React Dashboard
```bash
cd frontend
npm run dev
```

*Register your nodes via the API:*
```bash
curl -X POST http://localhost:6001/nodes -H "Content-Type: application/json" -d '{"id": "node-5000", "address": "localhost:5000"}'
curl -X POST http://localhost:6001/nodes -H "Content-Type: application/json" -d '{"id": "node-5001", "address": "localhost:5001"}'
```

### Part B: Start the Consensus Ring (Raft Cluster)

To test the distributed state machine, spin up the consensus nodes. They will automatically elect a leader and establish proxies.

```bash
# Terminal 5
python main.py node1 5001

# Terminal 6
python main.py node2 5002

# Terminal 7
python main.py node3 5003
```

---

## 💥 The "Chaos" Demo (Testing Resiliency)

### Orchestrator Self-Healing
1. Open the React Dashboard (`http://localhost:5173`).
2. Deploy a workload with 4 replicas. Watch the scheduler distribute them evenly.
3. Go to the terminal running `node-5000` and force kill it (`CTRL+C`).
4. Watch the UI: The node turns **RED** (DEAD) after exactly 30 seconds of missed heartbeats. The containers vanish.
5. Within 5 seconds, the Reconciler Loop wakes up, detects the drift, and automatically schedules the missing containers onto the surviving `node-5001`.

### Consensus Election
1. Watch the logs of your Raft cluster (`node1`, `node2`, `node3`).
2. Identify the current **Leader**.
3. Kill the Leader process.
4. Watch the remaining nodes trigger an `election_timeout`, transition to `CANDIDATE` status, exchange votes via the Cabinet weight system, and instantly elect a new Leader to resume log replication.

---

## 📚 API Reference

### Control Plane (Port 6001)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` / `POST` | `/nodes` | List all registered nodes or register a new one |
| `GET` / `POST` | `/workloads` | List all workloads or submit a new desired state |

### Node Agent (Port 5000, 5001, etc.)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` / `POST` | `/containers` | List local containers or start a new one |
| `DELETE` | `/containers/<id>` | Kill a specific container |

---

## 🎓 Learning Outcomes

By studying the source code (especially `container/runtime.py` and `consensus/node.py`), you will understand:
- ✅ **Linux kernel primitives:** How `os.fork()`, `execvp`, namespaces, and cgroups physically build a container.
- ✅ **Declarative Systems:** How a continuous reconciliation loop fixes drift between "Actual" and "Desired" cluster states.
- ✅ **Distributed Consensus:** How the Raft algorithm prevents split-brain scenarios and maintains a unified state log.
- ✅ **Scalable Architecture:** How RaftOptima's proxying reduces network overhead for leaders in large node clusters.

---

## 📖 Further Reading

- **Kubernetes Architecture:** [kubernetes.io/docs/concepts/architecture/](https://kubernetes.io/docs/concepts/architecture/)
- **The Raft Consensus Algorithm:** [raft.github.io/](https://raft.github.io/)
- **Linux Namespaces:** [man7.org/linux/man-pages/man7/namespaces.7.html](https://man7.org/linux/man-pages/man7/namespaces.7.html)
- **Cgroups v2:** [kernel.org/doc/html/latest/admin-guide/cgroup-v2.html](https://www.kernel.org/doc/html/latest/admin-guide/cgroup-v2.html)

---

## 🤝 Contributing
This is an educational project designed to demystify the magic behind tools like Kubernetes, Docker, and etcd. Feel free to fork, extend, read the code, and break things!

## 📝 License
MIT License - See LICENSE for details.

---
**Built to understand the magic behind modern cloud-native infrastructure.**

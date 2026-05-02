# 🚢 MiniOrch: A Distributed Container Orchestrator

![Python](https://img.shields.io/badge/Python-3.x-blue?style=flat-square&logo=python)
![React](https://img.shields.io/badge/React-Vite-blue?style=flat-square&logo=react)
![Linux](https://img.shields.io/badge/Linux-Namespaces%20%7C%20Cgroups-orange?style=flat-square&logo=linux)
![Status](https://img.shields.io/badge/Status-Self%20Healing-success?style=flat-square)

**MiniOrch** is a custom, Kubernetes-inspired distributed container orchestrator built from scratch in Python. Bypassing high-level abstractions like Docker, it interacts directly with the Linux kernel using raw syscalls, namespaces, and cgroups v2 for true process isolation. 

This project demonstrates a foundational understanding of cloud-native infrastructure, featuring a central control plane with a continuous reconciliation loop, heartbeat monitoring for automated self-healing, and a live React dashboard.

---

## ✨ Key Features

* **Custom Container Runtime:** Built from scratch using Linux kernel primitives. Isolates processes via `PID`, `UTS`, `NET`, `MNT`, and `IPC` namespaces.
* **Filesystem Isolation:** Implements `pivot_root` and bind mounts to provide containers with completely isolated root filesystems.
* **Resource Constraints:** Directly programs the Linux `cgroups v2` virtual filesystem to enforce strict CPU quotas and Memory limits.
* **Distributed Control Plane:** A master node that accepts user workloads and schedules them across available worker nodes using a "least-loaded" placement algorithm.
* **Continuous Reconciliation:** A background control loop that constantly compares the **Actual State** of the cluster against the **Desired State**, automatically spinning up or spinning down containers to fix any drift.
* **Automated Self-Healing:** Worker nodes send background telemetry pulses every 5 seconds. If a node goes silent for >30 seconds, it is marked `DEAD`, and its containers are automatically rescheduled onto healthy nodes.
* **Real-Time UI:** A single-page React application providing a live map of desired workloads, cluster health, and dynamic container placement.

---

## 🏗️ Architecture

```
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
 │                                       │  ◀─────────────────── Heartbeat (5s) ─│
```

---

## 🛠️ Tech Stack

| Component | Technology |
|-----------|------------|
| **Runtime** | Python 3.10+, Linux Kernel API (ctypes, syscalls) |
| **Isolation** | Linux Namespaces (PID, UTS, NET, MNT, IPC), Cgroups v2 |
| **Networking** | Flask, HTTP/REST, requests |
| **Frontend** | React 18+, Vite, JavaScript |
| **Root Filesystem** | Ubuntu Cloud Image or Alpine Mini Rootfs |

---

## 🚀 Getting Started

### Prerequisites

- **Linux environment** (strictly required for native namespaces and cgroups)
- **sudo privileges** (required to execute kernel-level isolation)
- **Python 3.10+** and **Node.js** installed
- An extracted Linux rootfs (e.g., Ubuntu Cloud Image or Alpine Mini Rootfs)

### 1. Installation & Setup

Clone the repository:

```bash
git clone https://github.com/yourusername/miniorch.git
cd miniorch
```

Set up the Python Virtual Environment for the backend:

```bash
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

## 🏃 Running the Cluster

To simulate a distributed system on a single machine, open multiple terminal windows. Run all backend commands from the miniorch root directory.

### Terminal 1: Start the Control Plane

```bash
sudo venv/bin/python3 -m control_plane.api.server
```

### Terminal 2: Start Worker Node A

```bash
sudo venv/bin/python3 -m api.server 5000
```

### Terminal 3: Start Worker Node B

```bash
sudo venv/bin/python3 -m api.server 5001
```

### Terminal 4: Start the React Dashboard

```bash
cd frontend
npm run dev
```

### Step 4: Register the Nodes

Tell the control plane that your worker nodes exist:

```bash
curl -X POST http://localhost:6001/nodes \
  -H "Content-Type: application/json" \
  -d '{"id": "node-5000", "address": "localhost:5000"}'

curl -X POST http://localhost:6001/nodes \
  -H "Content-Type: application/json" \
  -d '{"id": "node-5001", "address": "localhost:5001"}'
```

---

## 💥 The "Chaos" Demo (Testing Self-Healing)

This project is built to survive failure. Try this sequence to watch the reconciler self-heal the cluster:

1. **Open the React Dashboard:** Navigate to `http://localhost:5173` in your browser.

2. **Deploy a Workload:** Submit a new workload with 4 replicas.

3. **Watch the Scheduler:** Observe the Control Plane evenly distribute the containers across `node-5000` and `node-5001`.

4. **Execute Chaos:** Go to the terminal running `node-5000` and forcefully kill it:
   ```bash
   CTRL+C
   ```

5. **Observe the Self-Healing:**
   - After exactly 30 seconds of missed heartbeats, `node-5000` turns **RED** (DEAD) on the dashboard.
   - The containers on the dead node vanish, and your workload drops to `2 / 4 Replicas`.
   - Within 5 seconds, the Reconciliation Loop wakes up, detects the drift, and automatically schedules the 2 missing containers onto the surviving `node-5001`.
   - System state is restored to `4 / 4 Replicas`.

---

## 📚 API Reference

### Control Plane (Port 6001)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/nodes` | List all registered nodes |
| `POST` | `/nodes` | Register a new node |
| `GET` | `/workloads` | List all workloads |
| `POST` | `/workloads` | Submit a new workload |

### Node Agent (Port 5000, 5001, etc.)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/containers` | List containers on this node |
| `POST` | `/containers` | Start a new container |
| `DELETE` | `/containers/<id>` | Kill a container |

---

## 🔍 How It Works: The Reconciliation Loop

The heart of MiniOrch is the **Reconciliation Loop**, running every 5 seconds on the Control Plane:

```python
def reconcile_loop():
    while True:
        for workload in workloads.values():
            # Count actual running containers across ALL nodes
            actual_count = sum(len(node.containers) 
                             for node in nodes.values() 
                             if node.is_alive)
            
            # Compare Desired vs Actual
            if actual_count < workload.replicas:
                # Schedule more containers on healthy nodes
                scheduler.place(workload, nodes)
            
            elif actual_count > workload.replicas:
                # Kill excess containers
                pass
        
        time.sleep(5)
```

This is the **Kubernetes pattern in miniature**: declarative desired state + continuous reconciliation = self-healing infrastructure.

---

## 🏥 Failure Detection & Recovery

**Heartbeat Mechanism:**
- Each Node Agent sends a heartbeat pulse to the Control Plane every 5 seconds.
- If a node misses 6 consecutive heartbeats (30 seconds total), it is marked as `DEAD`.
- Dead nodes are instantly removed from the scheduler's available pool.
- Any containers that were running on the dead node are cleared.
- The Reconciliation Loop immediately detects the missing containers and reschedules them onto healthy nodes.

---

## 🎓 Learning Outcomes

By studying and extending MiniOrch, you will understand:

- ✅ Linux kernel primitives: namespaces, cgroups, syscalls
- ✅ Container runtime design from first principles
- ✅ Distributed state management and consensus
- ✅ Control plane architecture and reconciliation patterns
- ✅ Scheduler algorithms and resource placement
- ✅ Health monitoring, failure detection, and self-healing
- ✅ Real-time status visualization

---

## 🚀 Next Steps

### Option 1: Bulletproof the Control Plane (Notebook 4 - Distributed State)
Replace the in-memory dictionaries with **etcd** (a distributed key-value store) backed by Raft consensus. This ensures cluster state survives Control Plane crashes.

### Option 2: Connect Your Containers (Notebook 5 - Networking)
Implement a Container Network Interface (CNI) using **veth pairs**, **iptables**, and an **overlay network** so containers on different machines can seamlessly communicate.

---

## 📖 Further Reading

- **Kubernetes Architecture:** https://kubernetes.io/docs/concepts/architecture/
- **The Raft Consensus Algorithm:** https://raft.github.io/
- **Linux Namespaces:** https://man7.org/linux/man-pages/man7/namespaces.7.html
- **Cgroups v2:** https://www.kernel.org/doc/html/latest/admin-guide/cgroup-v2.html

---

## 🤝 Contributing

This is a learning project. Feel free to fork, extend, and break it. The best way to understand distributed systems is to build them yourself.

---

## 📝 License

MIT License - See LICENSE for details.

---

**Built to understand the magic behind modern cloud-native infrastructure.**

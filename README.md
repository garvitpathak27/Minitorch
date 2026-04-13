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
 │                                       │  ◀─────────────────── Heartbeat (5s) ─│

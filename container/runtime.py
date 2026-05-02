"""
before foring we need to prepare the cgroup first ... because we need to limit the exist

step 1 is to generate a container id
step 2 ist  create a cgroup for the container and set resource limits
the forking happens next which is splited into two processes, the parent and the child
    the childe becomes the container ... it calls the three name space function in order then doese one final think that replaces the python process with the user specified command using execvp so that the container process is running the user specified command instead of the python code

    the parent does not become a countainer .. it just need to remmeber that containder is running and that information is stored in a file in /tmp/containers/{container_id}.json which is the config.json file for the container that contains all the metadata about the container like its id, its cgroup path, its pid, its command, etc ... this file is used by the CLI to get information about the container and to stop it when needed


    run_container(image_path, command, memory, cpu)
│
├── 1. generate container_id
├── 2. create cgroup + set limits
├── 3. os.fork()
│       │
│       ├── CHILD
│       │     setup_namespaces()
│       │     setup_rootfs()
│       │     setup_proc()
│       │     cg.add_pid(os.getpid())
│       │     os.execvp(command)   ← Python is gone, now running user's command
│       │
│       └── PARENT
│             store ContainerState in _containers dict
│             return the state
│
stop_container(container_id)
├── 1. os.kill(pid, 9)
├── 2. os.waitpid(pid)
└── 3. cg.destroy()
"""

from utils.syscalls import mount, MS_BIND, MS_REC
import os
import uuid
from models.container import ContainerState, ContainerStatus
from container.cgroups import CgroupManager
from container.namespaces import setup_namespaces, setup_proc

_containers: dict[str, ContainerState] = {}


def run_container(
    image_path: str,
    command: list[str],
    memory_limit_bytes: int = 100 * 1024 * 1024,
    cpu_limit_percent: float = 50.0,
) -> ContainerState:

    container_id = str(uuid.uuid4())[:8]

    # 1. Create the CGroup
    cg = CgroupManager(container_id)
    cg.create(
        memory_limit_bytes=memory_limit_bytes, cpu_limit_percent=cpu_limit_percent
    )

    pid = os.fork()
    if pid == 0:
        # ==========================================
        # CHILD PROCESS (Traps itself)
        # ==========================================
        try:
            setup_namespaces(container_id=container_id)
            
            # setup_rootfs already mounts /proc, so we just need this!
            setup_rootfs(image_path)
            
            # Exec replaces the Python process with the user's command
            os.execvp(command[0], command)
            
        except Exception as e:
            print(f"Error occurred in child process: {e}")
            os._exit(1)
            
    else:
        # ==========================================
        # PARENT PROCESS (Manages the state)
        # ==========================================
        
        # FIX: The parent puts the child's true PID into the CGroup!
        cg.add_pid(pid)

        state = ContainerState(
            id=container_id,
            image=image_path,
            pid=pid,
            status=ContainerStatus.RUNNING,
            cpu_limit_percent=cpu_limit_percent,
            memory_limit_bytes=memory_limit_bytes,
        )
        
        _containers[container_id] = state
        return state

def list_containers() -> list[ContainerState]:
    return list(_containers.values())


def get_container(container_id: str) -> ContainerState | None:
    return _containers.get(container_id)


def stop_container(container_id: str) -> None:

    state = _containers.get(container_id)
    if not state:
        raise ValueError(f"Container with id {container_id} not found")

    try:
        os.kill(state.pid, 9)
        os.waitpid(state.pid, 0)
    except ProcessLookupError:
        print(f"Process {state.pid} already exited")

    cg = CgroupManager(container_id)
    cg.destroy()

    state.status = ContainerStatus.STOPPED
    state.pid = None


def setup_rootfs(rootfs_path: str):
    """Traps the container inside the downloaded Ubuntu folder."""
    if not os.path.exists(rootfs_path):
        raise FileNotFoundError(
            f"RootFS path not found: {rootfs_path}. Did you download it?"
        )

    mount(rootfs_path.encode(), rootfs_path.encode(), b"bind", MS_BIND | MS_REC, None)

    os.chdir(rootfs_path)

    os.chroot(".")

    if not os.path.exists("/proc"):
        os.makedirs("/proc", exist_ok=True)
    mount(b"proc", b"/proc", b"proc", 0, None)

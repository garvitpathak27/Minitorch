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

import os # for fork , kill wait , and execvp
import uuid # for generating container id
from models.container import ContainerState , ContainerStatus
from container.cgroups import CgroupManager
from container.namespaces import setup_namespaces , setup_rootfs ,setup_proc

_containers : dict[str , ContainerState] = {} 
def run_container(
        image_path:str,
        command:list[str],
        memory_limit_bytes: int = 100*1024*1024, # default 100MB ,
        cpu_limit_percent: float= 50.0 # default 50% of a single CPU
) -> ContainerState:
    #step 1 generate a unique container id 
    container_id = str(uuid.uuid4())[:8] # short id for readability
    #step 2 create a cgroup for the container and set resource limits
    cg = CgroupManager(container_id)
    cg.create(memory_limit_bytes=memory_limit_bytes, cpu_limit_percent=cpu_limit_percent)

    #step 3 fork the process 
    pid = os.fork()
    if pid == 0:
        #child process becomes the container
        try:
            setup_namespaces(container_id=container_id)
            setup_rootfs(image_path)
            setup_proc()
            cg.add_pid(os.getpid())
            os.execvp(command[0], command)
        except Exception as e:
            print(f"Error occurred in child process: {e}")
            os._exit(1) # exit with error code if something goes wrong
    else:
        #parent process
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
        os.kill(state.pid, 9) # send SIGKILL to the container process
        os.waitpid(state.pid, 0) # wait for the process to exit
    except ProcessLookupError:
        print(f"Process {state.pid} already exited")
    
    cg = CgroupManager(container_id)
    cg.destroy() # clean up cgroup resources

    state.status = ContainerStatus.STOPPED
    state.pid = None # clear the pid since the container is stopped



# if __name__ == "__main__":
#     import time

#     print("=== runtime.py confirmation ===")

#     state = run_container(
#         image_path="/tmp/testroot",
#         command=["sleep", "30"],
#     )

#     print(f"✓ container started")
#     print(f"✓ container id: {state.id}")
#     print(f"✓ container pid: {state.pid}")
#     print(f"✓ status: {state.status}")

#     time.sleep(1)

#     cg = CgroupManager(state.id)
#     print(f"✓ memory usage: {cg.get_memory_usage()} bytes")

#     containers = list_containers()
#     print(f"✓ list_containers returns {len(containers)} container(s)")

#     found = get_container(state.id)
#     print(f"✓ get_container found: {found.id}")

#     stop_container(state.id)
#     print(f"✓ container stopped")
#     print(f"✓ status: {state.status}")
#     print(f"✓ pid: {state.pid}")

#     print("=== all tests passed ===")
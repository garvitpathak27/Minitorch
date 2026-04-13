"""
now we will be making names space 
now there are different ype of names psace that inclicdde PID , ITS , NET , MNT AND IPC 

now there are mainly 3 fucntion of namespace .. 
function 1 
    set up all the namespace at onece ( that are all the 5 expect for user namespace )
    so that the container process will be isolated from the host process and it will have its own PID namespace , its namespace , net namespace , mnt namespace and ipc namespace

function 2 
    swap the filesystem so that container has its own root  so that it cant see the host file system

function 3
    mount /proc inside the container so that it can see its own process and not the host process
"""

import os
import sys
from utils.syscalls import (
    unshare,
    sethostname,
    CLONE_NEWUTS,
    CLONE_NEWPID,
    CLONE_NEWNS,
    CLONE_NEWNET,
    CLONE_NEWIPC,
)


def setup_namespaces(container_id: str) -> None:
    # create all 5 namespaces at once using bitwise OR to combine flags
    # this isolates the container from the host for PID, UTS, MNT, NET, IPC
    # NOTE: CLONE_NEWPID only affects CHILDREN of this process, not this process itself
    unshare(CLONE_NEWUTS | CLONE_NEWPID | CLONE_NEWNS | CLONE_NEWNET | CLONE_NEWIPC)

    # set hostname to container id inside the UTS namespace
    # this is why docker containers show their container id as hostname
    sethostname(container_id)


def setup_rootfs(rootfs_path: str) -> None:
    # step 1 - create a temporary directory inside rootfs to hold the old root
    old_root = os.path.join(rootfs_path, ".old_root")
    os.makedirs(old_root, exist_ok=True)

    # step 2 - bind mount rootfs onto itself
    # pivot_root requires the new root to be a mount point, not just a directory
    # bind mounting it onto itself promotes it to a mount point
    os.system(f"mount --bind {rootfs_path} {rootfs_path}")

    # step 3 - pivot_root swaps / to point to rootfs_path
    # the old / is now accessible at /.old_root inside the new root
    os.system(f"pivot_root {rootfs_path} {old_root}")

    # step 4 - reset working directory to new root
    # after pivot_root the cwd is stale and points to the old root in memory
    os.chdir("/")

    # step 5 - lazy unmount the old root
    # -l means detach immediately even if files are open, clean up when they close
    # after this the container has zero visibility into the host filesystem
    os.system("umount -l /.old_root")

    # step 6 - remove the temporary directory
    os.system("rmdir /.old_root")


def setup_proc() -> None:
    # create /proc directory if it doesn't exist in the container rootfs
    os.makedirs("/proc", exist_ok=True)

    # unmount the host proc first so we get a clean one
    # 2>/dev/null suppresses error if it wasnt mounted
    os.system("umount -l /proc 2>/dev/null")

    # mount a fresh proc filesystem scoped to the container's PID namespace
    # this is why ps inside a container only shows container processes
    os.system("mount -t proc proc /proc")


# if __name__ == "__main__":
#     rootfs = "/tmp/testroot"

#     print("=== namespaces.py confirmation ===")

#     pid = os.fork()

#     if pid == 0:
#         try:
#             setup_namespaces("test-container-001")
#             print(f"✓ hostname: {os.uname().nodename}")

#             setup_rootfs(rootfs)
#             print(f"✓ rootfs swapped")
#             print(f"✓ root contents: {os.listdir('/')[:4]}...")

#             setup_proc()
#             print(f"✓ proc mounted")
#             print(f"✓ /proc exists: {os.path.exists('/proc')}")

#             sys.stdout.flush()
#             os._exit(0)

#         except Exception as e:
#             print(f"✗ failed: {e}")
#             sys.stdout.flush()
#             os._exit(1)
#     else:
#         os.waitpid(pid, 0)
#         print("=== confirmation done ===")

"""
C groups are used to control the resource usage of a container. They are used to limit the CPU and memory usage of a container. They are also used to isolate the container from the host system. In this file we will define the CGroup class which will be used to manage the c groups for our containers.


now for this we will be using cgroupmanager
in whiich there are three things are are most important 

first is kernael needs somwhere to store the rules for this specific container ... each cntainer gets its own isolated set of rules ... 
we creat directory under /sys/fs/cgroup for each container and then we write the rules ... 
no directory means no rules 

create the cgroup -> mkdir /sys/fs/cgroup/minitorch/abc123

second

an empty cgroup has no rules yhet you need to write the actal limit into it the kerner reads memory max and cpu max 

set the limits  ->  write into memor max and cpu max 

attachment or process 

writing pid into process group 
limits sitting in c grup do absolutely nothing unil you tell the kernel which process to appy them to ... you do that by writing the process id into cgroups.procs

attach the process  ->  write pid into cgroups.procs


sop the secquence is always 

cgroup create ()
cgroup add_pid()
cgroup destroy()

"""

import os
CGROUP_ROOT = "/sys/fs/cgroup"

class CgroupManager:

    def __init__(self ,container_id: str):
        self.container_id = container_id
        self.cgroup_path = os.path.join(CGROUP_ROOT, "minitorch", container_id)


    ## now the time to write the create function which does 3 things that are make the directory at self.cgroup_path and then set memory limit and cpu limit



    def create(self, cpu_limit_percent: float, memory_limit_bytes: int) -> None:
        # enable controllers at root level
        with open("/sys/fs/cgroup/cgroup.subtree_control", "w") as f:
            f.write("+memory +cpu")

        # create the minitorch parent directory first
        os.makedirs(os.path.join("/sys/fs/cgroup", "minitorch"), exist_ok=True)

        # enable controllers at minitorch level too
        with open("/sys/fs/cgroup/minitorch/cgroup.subtree_control", "w") as f:
            f.write("+memory +cpu")

        period = 100000
        quota = int(period * (cpu_limit_percent / 100))

        # now create the actual container cgroup
        os.makedirs(self.cgroup_path, exist_ok=True)
        with open(os.path.join(self.cgroup_path, "memory.max"), "w") as f:
            f.write(str(memory_limit_bytes))
        with open(os.path.join(self.cgroup_path, "cpu.max"), "w") as f:
            f.write(f"{quota} {period}")


    # now its time to write cgroup add pid fnction which will wre the pid into the cgrup 

    def add_pid(self , pid: int)->None:
        with open(os.path.join(self.cgroup_path , "cgroup.procs") , "w") as f:
            f.write(str(pid))

    # now we will write the destoy 


    def destroy(self) -> None:
        with open(os.path.join(self.cgroup_path , "cgroup.procs") , "r") as f:
            pids = f.read().strip().split("\n")
        if pids != ['']:
            raise RuntimeError(f"Cgroup {self.container_id} is not empty. PIDs: {pids}")
        os.rmdir(self.cgroup_path)


    # now we will opre the last medtho  of get memory usage 


    def get_memory_usage(self) -> int:
        with open(os.path.join(self.cgroup_path , "memory.current") , "r") as f:
            return int(f.read().strip())
        

    def get_cpu_usage(self) -> float:
        with open(os.path.join(self.cgroup_path , "cpu.stat") , "r") as f:
            lines = f.read().strip().split("\n")
        for line in lines:
            if line.startswith("usage_usec"):
                return float(line.split()[1]) / 1000000  # Convert microseconds to seconds
        raise RuntimeError(f"Could not find CPU usage for cgroup {self.container_id}")
    

# if __name__ == "__main__":
#     import subprocess

#     print("=== cgroups.py confirmation ===")

#     cg = CgroupManager("test-001")
#     cg.create(cpu_limit_percent=50.0, memory_limit_bytes=50 * 1024 * 1024)
#     print("✓ cgroup created")

#     # verify limits were actually written
#     with open(f"/sys/fs/cgroup/minitorch/test-001/memory.max") as f:
#         assert f.read().strip() == str(50 * 1024 * 1024), "memory limit wrong"
#     print("✓ memory limit verified")

#     with open(f"/sys/fs/cgroup/minitorch/test-001/cpu.max") as f:
#         assert f.read().strip() == "50000 100000", "cpu limit wrong"
#     print("✓ cpu limit verified")

#     # spawn a real process and attach it
#     proc = subprocess.Popen(["sleep", "30"])
#     cg.add_pid(proc.pid)
#     print(f"✓ pid {proc.pid} added")

#     mem = cg.get_memory_usage()
#     cpu = cg.get_cpu_usage()
#     print(f"✓ memory usage: {mem} bytes")
#     print(f"✓ cpu usage: {cpu} seconds")

#     # kill process then destroy
#     proc.terminate()
#     proc.wait()
#     cg.destroy()
#     print("✓ cgroup destroyed cleanly")

#     print("=== all tests passed ===")
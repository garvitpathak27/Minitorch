import ctypes 
import os 

CLONE_NEWPID = 0x20000000
CLONE_NEWUTS = 0x04000000
CLONE_NEWNS = 0x00020000
CLONE_NEWNET = 0x40000000
CLONE_NEWUSER = 0x10000000
CLONE_NEWIPC = 0x08000000


_LIBC = ctypes.CDLL("libc.so.6" , use_errno=True)


def raise_last_errno() -> None:
    errno = ctypes.get_errno()
    raise OSError(errno , os.strerror(errno))

def unshare (flag: int) -> None:
    if(_LIBC.unshare(flag) != 0):
        raise_last_errno()

def sethostname(name : str) -> None:
    encoded = name.encode()
    if _LIBC.sethostname(encoded , len(encoded)) != 0:
        raise_last_errno()

# if __name__ == "__main__":
#     print("syscall.py confirmation ")
    
#     print(f"before: {os.uname().nodename}")
#     unshare(CLONE_NEWUTS)
#     sethostname("MY-CONTAINER")
#     print(f"after:  {os.uname().nodename}")
#     assert os.uname().nodename == "MY-CONTAINER" , "hostname change failed"
#     print("unshare + sethostname working")

#     try:
#         unshare(0x00000000)
#     except OSError as e:
#         print(f"✓ errno raised correctly: {e}")

#     print("=== all tests passed ===")
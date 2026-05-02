import ctypes 
import os 

# Namespace Flags
CLONE_NEWPID = 0x20000000
CLONE_NEWUTS = 0x04000000
CLONE_NEWNS = 0x00020000
CLONE_NEWNET = 0x40000000
CLONE_NEWUSER = 0x10000000
CLONE_NEWIPC = 0x08000000

# Mount Flags
MS_BIND = 4096
MS_REC = 16384
MS_PRIVATE = 1 << 18

_LIBC = ctypes.CDLL("libc.so.6" , use_errno=True)

# --- Eagerly load C functions to prevent Fork Deadlocks ---
_libc_unshare = _LIBC.unshare
_libc_unshare.argtypes = [ctypes.c_int]
_libc_unshare.restype = ctypes.c_int

_libc_sethostname = _LIBC.sethostname
_libc_sethostname.argtypes = [ctypes.c_char_p, ctypes.c_size_t]
_libc_sethostname.restype = ctypes.c_int

_libc_mount = _LIBC.mount
_libc_mount.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_char_p, ctypes.c_ulong, ctypes.c_void_p]
_libc_mount.restype = ctypes.c_int

def raise_last_errno() -> None:
    errno = ctypes.get_errno()
    raise OSError(errno , os.strerror(errno))

def unshare(flag: int) -> None:
    if _libc_unshare(flag) != 0:
        raise_last_errno()

def sethostname(name: str) -> None:
    encoded = name.encode()
    if _libc_sethostname(encoded , len(encoded)) != 0:
        raise_last_errno()

def mount(source: bytes, target: bytes, fs_type: bytes, mountflags: int, data: bytes = None) -> None:
    if _libc_mount(source, target, fs_type, mountflags, data) != 0:
        raise_last_errno()
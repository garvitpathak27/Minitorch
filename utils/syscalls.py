import ctypes 
import os 

CLONE_NEWPID = 0x20000000
CLONE_NEWUTS = 0x04000000
CLONE_NEWNS = 0x00020000
CLONE_NEWNET = 0x40000000
CLONE_NEWUSER = 0x10000000
CLONE_NEWIPC = 0x08000000

_LIBC = ctypes.CDLL("libc.so.6" , use_errno=True)

# --------------------------------------------------------------------
# CRITICAL FIX: Eagerly resolve C functions to prevent Fork Deadlocks!
# ctypes resolves symbols lazily. By declaring them here, we force 
# the dynamic linker to bind them before any background threads start.
# --------------------------------------------------------------------
_libc_unshare = _LIBC.unshare
_libc_unshare.argtypes = [ctypes.c_int]
_libc_unshare.restype = ctypes.c_int

_libc_sethostname = _LIBC.sethostname
_libc_sethostname.argtypes = [ctypes.c_char_p, ctypes.c_size_t]
_libc_sethostname.restype = ctypes.c_int

def raise_last_errno() -> None:
    errno = ctypes.get_errno()
    raise OSError(errno , os.strerror(errno))

def unshare (flag: int) -> None:
    if _libc_unshare(flag) != 0:
        raise_last_errno()

def sethostname(name : str) -> None:
    encoded = name.encode()
    if _libc_sethostname(encoded , len(encoded)) != 0:
        raise_last_errno()
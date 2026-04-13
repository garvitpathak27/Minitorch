from dataclasses import dataclass, field
# when we use @dataclass above a class ... python alutomatically writes an __init thing for ti as a construnctor 
# field is a helper from same module you need it when adefauly value cant be static value for example when a default should be call time . time () right now 
from enum import Enum

from typing import Optional
import time 

class ContainerStatus(Enum):
    CREATED ="created"
    RUNNING = "running"
    STOPPED = "stopped"
    FAILED  = "failed"

@dataclass
class ContainerState:
    id: str
    image:str
    pid:Optional[int]
    status: ContainerStatus
    cpu_limit_percent: float 
    memory_limit_bytes: int
    created_at : float = field(default_factory=time.time) # default_factory is used when you want to call a function to get the default value instead of a static value bascally when you want to call the time at the creating of the container not when the file is loaded



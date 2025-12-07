
from enum import Enum

class Tag(str, Enum):
    urgent = "urgent"
    important = "important"
    optional = "optional"
    can_wait = "can_wait"

from enum import Enum, auto

class RobotState(Enum):
    """Represents the current operational state of the robot."""
    IDLE = auto()
    CONVERSING = auto()
    ALERT = auto()      # Health warnings (e.g., high HR)
    EMERGENCY = auto()  # Critical events (e.g., Fall detected)

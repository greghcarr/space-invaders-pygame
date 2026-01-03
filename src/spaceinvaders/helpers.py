from enum import Enum, auto


class Direction(Enum):
    LEFT = auto(),
    RIGHT = auto()
    UP = auto()
    DOWN = auto()
    
    def reverse(self):
        if self == Direction.UP:
            return Direction.DOWN
        elif self == Direction.DOWN:
            return Direction.UP
        elif self == Direction.RIGHT:
            return Direction.LEFT
        elif self == Direction.LEFT:
            return Direction.RIGHT
        return None
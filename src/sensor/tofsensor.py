from enum import Enum


class Direction(Enum):
    INDOOR = "indoor"
    OUTDOOR = "outdoor"


class ToFSensor:
    def open(self):
        raise NotImplementedError()

    def setDirection(self, direction: Direction):
        """Configure sensor to pick up the distance in a specific direction.
        """
        raise NotImplementedError()

    def getDistance(self) -> float:
        """Returns new distance in cm.
        """
        raise NotImplementedError()
    
    def close(self):
        raise NotImplementedError()

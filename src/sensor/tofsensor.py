from enum import Enum


class Directions(Enum):
    INSIDE = "indoor"
    OUTSIDE = "outdoor"

    def other(self, direction: 'Direction') -> 'Direction':
        if direction is Directions.INSIDE:
            return Directions.OUTSIDE
        else:
            return Directions.INSIDE

    def __iter__(self):
        return [self.INSIDE, self.OUTSIDE]


class ToFSensor:
    def open(self) -> None:
        raise NotImplementedError()

    def setDirection(self, direction: Directions) -> None:
        """Configure sensor to pick up the distance in a specific direction.
        """
        raise NotImplementedError()

    def getDistance(self) -> float:
        """Returns new distance in cm.
        """
        raise NotImplementedError()

    def close(self) -> None:
        raise NotImplementedError()

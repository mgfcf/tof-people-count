from sensor.tofsensor import ToFSensor, Directions
from datetime import datetime
import logging


COUNTING_CB = "counting"
START_TIME = "start"
END_TIME = "end"


class PeopleCounter ():
    def __init__(self, sensor: ToFSensor) -> None:
        self.sensor = sensor
        self.callbacks = {COUNTING_CB: []}
        self.maxTriggerDistance = 120   # In cm

    def hookCounting(self, cb) -> None:
        self.callbacks[COUNTING_CB].append(cb)

    def unhookCounting(self, cb) -> None:
        self.callbacks[COUNTING_CB].remove(cb)

    def run(self) -> None:
        self.keepRunning = True
        direction = Directions.INSIDE
        self.directionState = {
            Directions.INSIDE: {
                START_TIME: None, END_TIME: None
            },
            Directions.OUTSIDE: {
                START_TIME: None, END_TIME: None
            }
        }

        self.sensor.open()
        while self.keepRunning:
            # Switch to other direction
            direction: Directions = Directions.other(direction)
            logging.debug(f'Direction [{direction}] at {datetime.now()}')

            self.sensor.setDirection(direction)

            distance: float = self.sensor.getDistance()
            triggered: bool = self.isTriggerDistance(distance)
            changed: bool = self.updateState(direction, triggered)

            if changed:
                countChange: int = self.getCountChange(self.directionState)
                self.handleCallbacks(countChange)

        self.sensor.close()

    def getCountChange(self, directionState) -> int:
        # Is valid?
        for direction in Directions:
            if directionState[direction][START_TIME] is None or directionState[direction][END_TIME] is None:
                return 0    # Return no change if not valid

        # Get times into variables
        insideStart = directionState[Directions.INSIDE][START_TIME]
        insideEnd = directionState[Directions.INSIDE][END_TIME]
        outsideStart = directionState[Directions.OUTSIDE][START_TIME]
        outsideEnd = directionState[Directions.OUTSIDE][END_TIME]

        # In what direction is the doorframe entered and left?
        # Entering doorframe in the inside direction
        enteringInside: bool = outsideStart < insideStart
        # Leaving dooframe in the inside direction
        leavingInside: bool = outsideEnd < insideEnd

        # They have to be the same, otherwise they switch directions in between
        if enteringInside != leavingInside:
            # Someone did not go all the way
            # Either
            # Inside    -######-
            # Outside   ---##---
            # or
            # Inside    ---##---
            # Outside   -######-
            return 0

        # Are those times overlapping or disjunct?
        if insideEnd < outsideStart or outsideEnd < insideStart:
            # They are disjunct
            # Either
            # Inside    -##-----
            # Outside   -----##-
            # or
            # Inside    -----##-
            # Outside   -##-----
            return 0

        # What direction is the person taking?
        if enteringInside:
            # Entering the inside
            # Inside    ---####-
            # Outside   -####---
            return 1
        else:
            # Leaving the inside
            # Inside    -####---
            # Outside   ---####-
            return -1

    def isTriggerDistance(self, distance: float) -> bool:
        #! TODO: Should be based on the distance from the ground, not them the sensor
        return distance <= self.maxTriggerDistance

    def handleCallbacks(self, countChange: int) -> None:
        if countChange == 0:
            # Do nothing if there is no change
            return

        for cb in self.callbacks[COUNTING_CB]:
            cb(countChange)

    def updateState(self, direction: Directions, triggered: bool) -> bool:
        currentlyTriggered = self.directionState[direction] == None

        if triggered and not currentlyTriggered:
            # Set as new beginning for this direction
            self.directionState[direction][START_TIME] = datetime.now()
            self.directionState[direction][END_TIME] = None
            return True
        elif not triggered and currentlyTriggered:
            # Set as new end for this direction
            self.directionState[direction][END_TIME] = datetime.now()
            return True

        return False

from typing import Dict
from sensor.tof_sensor import ToFSensor, Directions
from datetime import datetime
import threading


COUNTING_CB = "counting"
TRIGGER_CB = "trigger"
CHANGE_CB = "changes"
START_TIME = "start_time"
END_TIME = "end_time"
TRIGGER_DISTANCES = "trigger_distances"
END_DISTANCE = "end_distance"


class PeopleCounter ():
    def __init__(self, sensor: ToFSensor) -> None:
        self.sensor = sensor
        self.callbacks = {COUNTING_CB: [], TRIGGER_CB: [], CHANGE_CB: []}
        self.maxTriggerDistance = 120   # In cm

    def hookCounting(self, cb) -> None:
        self.callbacks[COUNTING_CB].append(cb)

    def unhookCounting(self, cb) -> None:
        self.callbacks[COUNTING_CB].remove(cb)

    def hookTrigger(self, cb) -> None:
        self.callbacks[TRIGGER_CB].append(cb)

    def unhookTrigger(self, cb) -> None:
        self.callbacks[TRIGGER_CB].remove(cb)

    def hookChange(self, cb) -> None:
        self.callbacks[CHANGE_CB].append(cb)

    def unhookChange(self, cb) -> None:
        self.callbacks[CHANGE_CB].remove(cb)

    def getInitialDirectionState(self) -> Dict:
        return {
            Directions.INSIDE: [],
            Directions.OUTSIDE: []
        }

    def run(self) -> None:
        self.keepRunning = True
        direction = Directions.INSIDE
        self.directionState = self.getInitialDirectionState()

        self.sensor.open()
        while self.keepRunning:
            # Switch to other direction
            direction: Directions = Directions.other(direction)

            self.sensor.setDirection(direction)

            distance: float = self.sensor.getDistance()
            changed: bool = self.updateState(direction, distance)

            if changed:
                countChange: int = self.getCountChange(self.directionState)
                
                # Hooks
                th = threading.Thread(target=self.handleCallbacks, args=(countChange,))
                th.start()

                # Reset state if state is finalised
                if not self.isDirectionTriggered(Directions.INSIDE) and not self.isDirectionTriggered(Directions.OUTSIDE):
                    self.directionState = self.getInitialDirectionState()

        self.sensor.close()

    def getCountChange(self, directionState) -> int:
        # Is valid?
        for direction in Directions:
            # Is there at least one record for every direction?
            if len(directionState[direction]) <= 0:
                return 0

            # Did every record start and end?
            if directionState[direction][0][START_TIME] is None or directionState[direction][-1][END_TIME] is None:
                return 0    # Return no change if not valid

        # Get times into variables
        insideStart = directionState[Directions.INSIDE][0][START_TIME]
        insideEnd = directionState[Directions.INSIDE][-1][END_TIME]
        outsideStart = directionState[Directions.OUTSIDE][0][START_TIME]
        outsideEnd = directionState[Directions.OUTSIDE][-1][END_TIME]

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
        #! TODO: Should be based on the distance from the ground, not from the sensor
        return distance <= self.maxTriggerDistance
    
    def handleCallbacks(self, countChange: int):
        self.handleChangeCallbacks(countChange)
        self.handleCountingCallbacks(countChange)
        self.handleTriggerCallbacks()

    def handleCountingCallbacks(self, countChange: int) -> None:
        # Only notify counting on actual count change
        if countChange == 0:
            return

        for cb in self.callbacks[COUNTING_CB]:
            cb(countChange)

    def handleTriggerCallbacks(self) -> None:
        triggerState = {
            Directions.INSIDE: self.isDirectionTriggered(Directions.INSIDE),
            Directions.OUTSIDE: self.isDirectionTriggered(Directions.OUTSIDE)
        }
        
        for cb in self.callbacks[TRIGGER_CB]:
            cb(triggerState)

    def handleChangeCallbacks(self, countChange: int) -> None:
        for cb in self.callbacks[CHANGE_CB]:
            cb(countChange, self.directionState)
    
    def isDirectionTriggered(self, direction: Directions) -> bool:
        return len(self.directionState[direction]) > 0 and self.directionState[direction][-1][END_TIME] is None

    def updateState(self, direction: Directions, distance: float) -> bool:
        triggered: bool = self.isTriggerDistance(distance)
        
        previouslyTriggered = False
        if len(self.directionState[direction]) > 0:
            previouslyTriggered = self.directionState[direction][-1][END_TIME] is None

        if triggered and not previouslyTriggered:
            # Set as new beginning for this direction
            self.directionState[direction].append({
                START_TIME: datetime.now(),
                END_TIME: None,
                TRIGGER_DISTANCES: [distance],
                END_DISTANCE: None
            })
            return True
        elif not triggered and previouslyTriggered:
            # Set as end for this direction
            self.directionState[direction][-1][END_TIME] = datetime.now()
            self.directionState[direction][-1][END_DISTANCE] = distance
            return True
        elif previouslyTriggered:
            # Add distance at least
            self.directionState[direction][-1][TRIGGER_DISTANCES].append(distance)

        return False

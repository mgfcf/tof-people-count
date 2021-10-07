from peoplecounter import PeopleCounter
from sensor.vl53l1xsensor import VL53L1XSensor
import logging

counter = PeopleCounter(VL53L1XSensor())
peopleCount = 0

logging.getLogger().setLevel(logging.DEBUG)


def countChange(change: int) -> None:
    global peopleCount
    peopleCount += change
    logging.info(f'People count change to: {peopleCount}')


counter.hookCounting(countChange)
counter.run()

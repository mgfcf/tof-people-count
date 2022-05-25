from datetime import datetime
from typing import Dict
from interface.philips_hue import PhilipsHue
from sensor.people_counter import PeopleCounter
from sensor.vl53l1x_sensor import VL53L1XSensor
import logging
import json


LOG_FILE_PATH = "log.txt"   # Path for logs
hue_conf = {
    'bridge_ip': '',
    'transition_time': 10,  # seconds
    'light_group': '',
    # If file exists, application is considered 'registered' at the bridge
    'registered_file': 'smart_light_registered.bridge'
}   # Custom configuration for philips hue


hue: PhilipsHue = PhilipsHue(hue_conf)  # Light interface
counter: PeopleCounter = PeopleCounter(VL53L1XSensor())  # Sensor object
peopleCount: int = 0    # Global count of people on the inside

logging.getLogger().setLevel(logging.INFO)


def change_cb(countChange: int, directionState: Dict):
    """Handles basic logging of event data for later analysis.

    Args:
        countChange (int): The change in the number of people. Usually on of [-1, 0, 1].
        directionState (Dict): Object describing the internal state of the sensor.
    """
    data = {
        'version': 'v0.0',
        'previousPeopleCount': peopleCount,
        'countChange': countChange,
        'directionState': directionState,
        'dateTime': datetime.now(),
        'motionTriggeredLights': False
    }

    try:
        with open(LOG_FILE_PATH, 'a') as f:
            f.write(json.dumps(data, default=str) + "\n")
    except Exception as ex:
        logging.exception(f'Unable to write log file. {ex}')


def count_change(change: int) -> None:
    """Handles light state when people count changes

    Args:
        change (int): The change in the number of people. Usually on of [-1, 0, 1].
    """
    global hue
    global peopleCount

    # Are lights on at the moment?
    previous_lights_state = get_light_state()

    # Apply correction
    if peopleCount <= 0 and previous_lights_state:
        # Count was 0, but lights were on => people count was not actually 0
        peopleCount = 1
        logging.debug(f'People count corrected to {peopleCount}')
    elif peopleCount > 0 and not previous_lights_state:
        # Count was >0, but lights were off => people count was actually 0
        peopleCount = 0
        logging.debug(f'People count corrected to {peopleCount}')

    peopleCount += change
    if peopleCount < 0:
        peopleCount = 0
    logging.debug(f'People count changed by {change}')

    # Handle light
    target_light_state = peopleCount > 0

    # Return, if there is no change
    if previous_lights_state == target_light_state:
        return

    set_light_state(target_light_state)


def set_light_state(target_light_state: bool) -> bool:
    """Sets the lights to the given state.

    Args:
        target_light_state (bool): Should lights on the inside be on or off.

    Returns:
        bool: Previous light state.
    """
    # Are lights on at the moment?
    previous_lights_state = get_light_state()
    if target_light_state == previous_lights_state:
        return previous_lights_state

    # Adjust light as necessary
    hue.set_group(hue_conf['light_group'], {'on': target_light_state})
    logging.debug(f'Light state changed to {target_light_state}')

    return previous_lights_state


def get_light_state() -> bool:
    """
    Returns:
        bool: Current light state.
    """
    return hue.get_group(hue_conf['light_group'])['state']['any_on']


if __name__ == "__main__":
    # Represents callback trigger order
    counter.hookChange(change_cb)
    counter.hookCounting(count_change)

    counter.run()

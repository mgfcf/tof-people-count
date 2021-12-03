from datetime import datetime
from pathlib import Path
from typing import Dict
from interface.philips_hue import PhilipsHue
from sensor.people_counter import PeopleCounter
from sensor.tof_sensor import Directions
from sensor.vl53l1x_sensor import VL53L1XSensor
import logging
import json

LOG_FILE_PATH = "log.txt"
hue_conf = {
    'bridge_ip': '',
    'transition_time': 10,  # seconds
    'light_group': '',
    # If file exists, application is considered 'registered' at the bridge
    'registered_file': 'smart_light_registered.bridge'
}


hue = PhilipsHue(hue_conf)
counter = PeopleCounter(VL53L1XSensor())
peopleCount = 0
early_light_state = False   # TODO: Is probably redundant and can be implemented over peopleCount

logging.getLogger().setLevel(logging.INFO)


def count_change(change: int) -> None:
    global hue
    global peopleCount
    global early_light_state

    # Are lights on at the moment?
    previous_lights_state = hue.get_group(hue_conf['light_group'])[
        'state']['any_on']

    # Apply correction
    if peopleCount <= 0 and previous_lights_state and not early_light_state:
        # User indicates, that people count was not actually 0
        peopleCount = 1
        logging.debug(f'People count corrected to {peopleCount}')
    elif peopleCount > 0 and not previous_lights_state:
        # User indicates, that people count was actually 0
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
        if previous_lights_state:
            early_light_state = False
        return

    hue.set_group(hue_conf['light_group'], {'on': target_light_state})
    logging.debug(f'Light state changed to {target_light_state}')


def trigger_change(triggerState: Dict):
    global hue
    global early_light_state

    target_light_state = None

    # Is someone walking close to the door?
    target_light_state = triggerState[Directions.INSIDE] or triggerState[Directions.OUTSIDE]

    # Only look at changing situations
    if target_light_state == early_light_state:
        return
    
    # Are lights on at the moment?
    previous_lights_state = hue.get_group(hue_conf['light_group'])['state']['any_on']
    if target_light_state == previous_lights_state:
        return
    
    # Adjust light as necessary
    hue.set_group(hue_conf['light_group'], {'on': target_light_state})
    logging.debug(f'Light state changed to {target_light_state} for early light')
    
    early_light_state = target_light_state


def change_cb(countChange: int, directionState: Dict):
    data = {
        'previousPeopleCount': peopleCount,
        'countChange': countChange,
        'directionState': directionState,
        'dateTime': datetime.now()
    }

    try:
        with open(LOG_FILE_PATH, 'a') as f:
            f.write(json.dumps(data, default=str) + "\n")
    except Exception as ex:
        logging.exception(f'Unable to write log file. {ex}')


counter.hookCounting(count_change)
counter.hookTrigger(trigger_change)
counter.hookChange(change_cb)
counter.run()

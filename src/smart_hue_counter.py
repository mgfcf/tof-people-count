from datetime import datetime, time, timedelta
from typing import Dict
from interface.philips_hue import PhilipsHue
from sensor.people_counter import PeopleCounter
from sensor.tof_sensor import Directions
from sensor.vl53l1x_sensor import VL53L1XSensor
import logging
import json
from timeloop import Timeloop


# Should lights already turn on where there is any kind of motion in the sensor
ENABLE_MOTION_TRIGGERED_LIGHT = True

# Should lights change when a certain time in the schedule is reached
ENABLE_SCHEDULE_TRIGGERS = False    # Not working correctly at the moment, so turned off by default

# Schedule (Key is time after scene should be used. Value is scene name to be used.)
# Needs to be sorted chronologically
SCHEDULE = {}


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
motion_triggered_lights = False   # Is light on because of any detected motion
timeloop: Timeloop = Timeloop()  # Used for time triggered schedule

logging.getLogger().setLevel(logging.INFO)


def time_minus_time(time_a: time, time_b: time) -> timedelta:
    """Implementes a basic timedelta function for time objects.

    Args:
        time_a (time): Time to subtract from.
        time_b (time): Time to be subtracted.

    Returns:
        timedelta: Delta between the two time objects.
    """
    today = datetime.today()
    dt_a = datetime.combine(today, time_a)
    dt_b = datetime.combine(today, time_b)

    return dt_a - dt_b


def get_scene_for_time(time: time) -> str:
    """Determines the correct scene to activate for a given time.

    Args:
        time (time): Time to find scene for.

    Returns:
        string: Scene name that should be active. None, if schedule is empty.
    """
    global SCHEDULE

    if SCHEDULE is None or len(SCHEDULE) <= 0:
        return None

    previous_scene = None
    for start_time, scene in SCHEDULE.items():
        # If current time is still after schedule time, just keep going
        if start_time <= time:
            previous_scene = scene
            continue

        # Schedule timef is now after current time, which is too late
        # So if exists, take previous scene, since it was the last before the current time
        if previous_scene:
            return previous_scene
        else:
            break

    # Only breaks if it could not find a valid scene, so use lates scene as fallback
    return list(SCHEDULE.values())[-1]


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
        'motionTriggeredLights': motion_triggered_lights
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
    global motion_triggered_lights

    # Are lights on at the moment?
    previous_lights_state = get_light_state()

    # Apply correction
    if peopleCount <= 0 and previous_lights_state and not motion_triggered_lights:
        # Count was 0, but lights were on (not because of motion triggers) => people count was not actually 0
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
        if previous_lights_state:
            # Signaling that the people count is taking control over the light now
            motion_triggered_lights = False
        return

    set_light_state(target_light_state)


def trigger_change(triggerState: Dict):
    """Handles motion triggered light state.

    Args:
        triggerState (Dict): Describing in what directions the sensor is triggerd.
    """
    global hue
    global motion_triggered_lights

    target_light_state = None

    # Is someone walking close to the door?
    motion_detected = triggerState[Directions.INSIDE] or triggerState[Directions.OUTSIDE]
    target_light_state = motion_detected

    # Does motion triggered light need to do anything?
    if peopleCount > 0:
        # State is successfully handled by the count
        motion_triggered_lights = False
        return

    # Only look at changing situations
    if target_light_state == motion_triggered_lights:
        return

    set_light_state(target_light_state)

    # Save state
    motion_triggered_lights = target_light_state


def set_light_scene(target_scene: str) -> bool:
    """Sets the lights to the given scene, but only, if lights are already on. Does not correct count if lights are in an unexpected state.

    Args:
        target_scene (string): Name of the scene to activate.
    """
    # Is valid scene?
    if target_scene is None:
        return

    # Are lights on at the moment? Only based on people count for simplicity
    if peopleCount <= 0:
        # Lights are probably off, not doing anything
        return

    # Set lights to scene
    hue.set_group_scene(hue_conf['light_group'], target_scene)
    logging.debug(
        f'Light scene set to {target_scene}')


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
    target_scene = get_scene_for_time(datetime.now().time())
    if target_light_state and target_scene:
        # Set to specific scene if exists
        hue.set_group_scene(hue_conf['light_group'], target_scene)
        logging.debug(
            f'Light state changed to {target_light_state} with scene {target_scene}')
    else:
        hue.set_group(hue_conf['light_group'], {'on': target_light_state})
        logging.debug(f'Light state changed to {target_light_state}')

    return previous_lights_state


def get_light_state() -> bool:
    """
    Returns:
        bool: Current light state.
    """
    return hue.get_group(hue_conf['light_group'])['state']['any_on']


def update_scene():
    """Called by time trigger to update light scene if lights are on.
    """
    scene = get_scene_for_time(datetime.now().time())

    if scene is None:
        return

    set_light_scene(scene)
    logging.debug(f'Updated scene at {datetime.now().time()} to {scene}.')


def register_time_triggers():
    """Registeres time triggered callbacks based on the schedule, to adjust the current scene, if lights are on.
    """
    global SCHEDULE
    if SCHEDULE is None or len(SCHEDULE) <= 0:
        return

    for time in SCHEDULE.keys():
        delta = time_minus_time(time, datetime.now().time())
        if delta < timedelta(0):
            delta += timedelta(1)

        timeloop._add_job(update_scene, interval=timedelta(1), offset=delta)

    timeloop.start(block=False)

    logging.info("Registered time triggers.")


if __name__ == "__main__":
    if ENABLE_SCHEDULE_TRIGGERS:
        register_time_triggers()

    # Represents callback trigger order
    counter.hookChange(change_cb)
    counter.hookCounting(count_change)
    counter.hookTrigger(trigger_change)

    counter.run()

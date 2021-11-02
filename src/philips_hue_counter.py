from interface.philips_hue import PhilipsHue
from sensor.people_counter import PeopleCounter
from sensor.vl53l1x_sensor import VL53L1XSensor
import logging

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

logging.getLogger().setLevel(logging.INFO)


def count_change(change: int) -> None:
    global peopleCount
    
    # Are lights on at the moment?
    previous_lights_state = hue.get_group(hue_conf['light_group'])['state']['any_on']
    
    # Apply correction
    if peopleCount <= 0 and previous_lights_state:
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
        return
    
    hue.set_group(hue_conf['light_group'], {'on': target_light_state})
    logging.debug(f'Light state changed to {target_light_state}')


counter.hookCounting(count_change)
counter.run()

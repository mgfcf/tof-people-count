from peoplecounter import PeopleCounter
from sensor.vl53l1xsensor import VL53L1XSensor
import paho.mqtt.client as mqtt
from HaMqtt.MQTTSensor import MQTTSensor
import logging


HA_URL = ""
HA_PORT = 1883
HA_SENSOR_NAME = ""
HA_SENSOR_ID = ""


# Setup connection to HA
mqttClient = mqtt.Client()
mqttClient.connect(HA_URL, HA_PORT)
mqttClient.loop_start()  # Keep conneciton alive

# Setup mqtt binding
sensor = MQTTSensor(HA_SENSOR_NAME, HA_SENSOR_ID, mqttClient)
logging.debug(f'Connected to topic {sensor.state_topic}')


def countChange(change: int) -> None:
    """Called when people count change is detected.
    Sends update to the initialized HA instance.

    Args:
        change (int): Number of people leaving (<0) or entering (>0) a room.
    """
    # Send update to HA
    global sensor
    sensor.publish_state(change)
    
    logging.debug(f'People count changed by {change}')


# Setup people count sensor
counter = PeopleCounter(VL53L1XSensor())
counter.hookCounting(countChange)
counter.run()

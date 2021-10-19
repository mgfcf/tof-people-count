from peoplecounter import PeopleCounter
from sensor.vl53l1xsensor import VL53L1XSensor
import paho.mqtt.client as mqtt


HA_URL = ""
HA_PORT = 1883
HA_TOPIC = ""


# Setup connection to HA
mqttClient = mqtt.Client()
mqttClient.connect(HA_URL, HA_PORT)
mqttClient.loop_start()  # Keep conneciton alive


def countChange(change: int) -> None:
    """Called when people count change is detected.
    Sends update to the initialized HA instance.

    Args:
        change (int): Number of people leaving (<0) or entering (>0) a room.
    """
    # Send update to HA
    mqttClient.publish(HA_TOPIC, change)


# Setup people count sensor
counter = PeopleCounter(VL53L1XSensor())
counter.hookCounting(countChange)
counter.run()

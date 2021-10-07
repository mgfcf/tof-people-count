from sensor.tofsensor import Directions, ToFSensor
import VL53L1X

# Reference: https://github.com/pimoroni/vl53l1x-python
#
# Left, right, top and bottom are relative to the SPAD matrix coordinates,
# which will be mirrored in real scene coordinates.
# (or even rotated, depending on the VM53L1X element alignment on the board and on the board position)
#
# ROI in SPAD matrix coords:
#
# 15  top-left
# |  X____
# |  |    |
# |  |____X
# |        bottom-right
# 0__________15
#


class VL53L1XSensor (ToFSensor):
    def __init__(self) -> None:
        super().__init__()

    def open(self) -> None:
        self.sensor = VL53L1X.VL53L1X(i2c_bus=1, i2c_address=0x29)
        self.sensor.open()

        # Optionally set an explicit timing budget
        # These values are measurement time in microseconds,
        # and inter-measurement time in milliseconds.
        # If you uncomment the line below to set a budget you
        # should use `tof.start_ranging(0)`
        # tof.set_timing(66000, 70)
        self.ranging = 2
        # 0 = Unchanged
        # 1 = Short Range
        # 2 = Medium Range
        # 3 = Long Range

    def setDirection(self, direction: Directions) -> None:
        """Configure sensor to pick up the distance in a specific direction.
        """
        direction_roi = {
            Directions.INSIDE: VL53L1X.VL53L1xUserRoi(6, 3, 9, 0),
            Directions.OUTSIDE: VL53L1X.VL53L1xUserRoi(6, 15, 9, 12)
        }

        roi = direction_roi[direction]

        self.sensor.stop_ranging()
        self.sensor.set_user_roi(roi)
        self.sensor.start_ranging(self.ranging)

    def getDistance(self) -> float:
        """Returns new distance in cm.
        """
        distance = self.sensor.get_distance()

        return distance / 10

    def close(self) -> None:
        self.sensor.stop_ranging()
        self.sensor.close()

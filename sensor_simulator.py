"""EDGEGUARD-X: Hardware-independent sensor simulator.

Generates simulated radar, distance sensor and IMU readings.
These values are for software testing only, not real measurements.
"""

import math
import random
import time

from hardware.sensor_interface import SensorReading


class SensorSimulator:
    def __init__(self):
        self.start_time = time.time()

    def get_radar_reading(self) -> SensorReading:
        """Simulate an approaching vehicle detected by radar."""

        elapsed = time.time() - self.start_time

        distance = max(1.0, 20.0 - 2.0 * elapsed)
        relative_speed = -2.0

        return SensorReading(
            sensor_id="radar_01",
            timestamp=time.time(),
            object_id=1,
            object_class="vehicle",
            distance_m=round(distance, 2),
            relative_speed_mps=relative_speed,
            confidence=0.95,
            valid=True,
            metadata={"source": "simulation"},
        )

    def get_distance_reading(self) -> SensorReading:
        """Simulate a LiDAR or ToF distance measurement."""

        distance = random.uniform(8.0, 10.0)

        return SensorReading(
            sensor_id="tof_01",
            timestamp=time.time(),
            distance_m=round(distance, 2),
            confidence=0.90,
            valid=True,
            metadata={"source": "simulation"},
        )

    def get_imu_reading(self) -> dict:
        """Simulate basic IMU acceleration and angular velocity."""

        return {
            "sensor_id": "imu_01",
            "timestamp": time.time(),
            "acceleration_mps2": {
                "x": round(random.uniform(-0.2, 0.2), 3),
                "y": round(random.uniform(-0.2, 0.2), 3),
                "z": round(9.81 + random.uniform(-0.2, 0.2), 3),
            },
            "angular_velocity_dps": {
                "x": round(random.uniform(-1.0, 1.0), 3),
                "y": round(random.uniform(-1.0, 1.0), 3),
                "z": round(random.uniform(-1.0, 1.0), 3),
            },
            "valid": True,
            "metadata": {"source": "simulation"},
        }

"""
EDGEGUARD-X: Basic sensor fusion module.

Combines readings from different sensors.
This is an initial software prototype, not a calibrated
real-world sensor fusion system.
"""

from typing import Optional
from hardware.sensor_interface import SensorReading


class SensorFusion:
    def fuse_readings(
        self,
        radar: Optional[SensorReading] = None,
        distance: Optional[SensorReading] = None,
    ) -> dict:
        """Combine valid radar and distance-sensor readings."""

        readings = {}

        if radar is not None:
            radar.validate()
            if radar.valid:
                readings["radar"] = radar.to_dict()

        if distance is not None:
            distance.validate()
            if distance.valid:
                readings["distance"] = distance.to_dict()

        radar_distance = None
        tof_distance = None

        if "radar" in readings:
            radar_distance = readings["radar"]["distance_m"]

        if "distance" in readings:
            tof_distance = readings["distance"]["distance_m"]

        available_distances = [
            value
            for value in [radar_distance, tof_distance]
            if value is not None
        ]

        if available_distances:
            estimated_distance = round(
                sum(available_distances) / len(available_distances), 2
            )
        else:
            estimated_distance = None

        return {
            "sensor_count": len(readings),
            "radar_distance_m": radar_distance,
            "distance_sensor_m": tof_distance,
            "estimated_distance_m": estimated_distance,
            "fusion_method": "simple_average",
            "note": (
                "Prototype estimate; sensor calibration and "
                "object association are not implemented."
            ),
        }
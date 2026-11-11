"""
EDGEGUARD-X: Common sensor data interface.

This module defines a standard format for sensor readings.
It can be used with simulated sensors and real hardware.
"""

from dataclasses import dataclass, field, asdict
from typing import Optional
import time


@dataclass
class SensorReading:
    """Standard representation of a sensor reading."""

    sensor_id: str
    timestamp: float = field(default_factory=time.time)

    object_id: Optional[int] = None
    object_class: Optional[str] = None

    distance_m: Optional[float] = None
    relative_speed_mps: Optional[float] = None
    confidence: Optional[float] = None

    valid: bool = True
    metadata: dict = field(default_factory=dict)

    def validate(self) -> None:
        """Validate the reading before using it."""

        if not self.sensor_id:
            raise ValueError("sensor_id cannot be empty")

        if self.timestamp <= 0:
            raise ValueError("timestamp must be positive")

        if self.distance_m is not None:
            if self.distance_m < 0:
                raise ValueError("distance_m cannot be negative")

        if self.confidence is not None:
            if not 0.0 <= self.confidence <= 1.0:
                raise ValueError(
                    "confidence must be between 0.0 and 1.0"
                )

    def to_dict(self) -> dict:
        """Convert the reading into a dictionary."""

        self.validate()
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "SensorReading":
        """Create a reading from a dictionary."""

        reading = cls(**data)
        reading.validate()
        return reading
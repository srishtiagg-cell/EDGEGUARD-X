"""
EDGEGUARD-X: MCU communication protocol.

Creates and validates JSON messages for communication
between the Python software and a microcontroller.

Initial prototype: no physical hardware communication yet.
"""

import json
import time


class MCUProtocol:
    def __init__(self):
        self.sequence_number = 0

    def create_message(
        self,
        command: str,
        risk_level: str,
        distance_m=None,
    ) -> str:
        """Create a JSON message for the microcontroller."""

        allowed_commands = {
            "STATUS",
            "WARNING_ON",
            "WARNING_OFF",
        }

        allowed_risks = {
            "LOW",
            "MEDIUM",
            "HIGH",
            "CRITICAL",
        }

        if command not in allowed_commands:
            raise ValueError("Unsupported command")

        if risk_level not in allowed_risks:
            raise ValueError("Invalid risk level")

        if distance_m is not None and distance_m < 0:
            raise ValueError("Distance cannot be negative")

        self.sequence_number += 1

        message = {
            "sequence": self.sequence_number,
            "timestamp": time.time(),
            "command": command,
            "risk_level": risk_level,
            "distance_m": distance_m,
        }

        return json.dumps(message)

    @staticmethod
    def validate_message(message: str) -> dict:
        """Validate and decode a JSON message."""

        try:
            data = json.loads(message)
        except json.JSONDecodeError as error:
            raise ValueError("Invalid JSON message") from error

        required_fields = {
            "sequence",
            "timestamp",
            "command",
            "risk_level",
            "distance_m",
        }

        if not isinstance(data, dict):
            raise ValueError("Message must be a JSON object")

        if not required_fields.issubset(data.keys()):
            raise ValueError("Message is missing required fields")

        if data["command"] not in {
            "STATUS",
            "WARNING_ON",
            "WARNING_OFF",
        }:
            raise ValueError("Unsupported command")

        if data["risk_level"] not in {
            "LOW",
            "MEDIUM",
            "HIGH",
            "CRITICAL",
        }:
            raise ValueError("Invalid risk level")

        if data["distance_m"] is not None:
            if (
                not isinstance(data["distance_m"], (int, float))
                or data["distance_m"] < 0
            ):
                raise ValueError("Invalid distance")

        return data
"""
EDGEGUARD-X: Risk-to-MCU warning adapter.

Converts existing risk classifications into warning messages.
This does not control a vehicle or activate a physical buzzer.
"""

from hardware.mcu_protocol import MCUProtocol


class RiskAdapter:
    def __init__(self):
        self.protocol = MCUProtocol()

    def create_warning_message(
        self,
        risk_state: str,
        distance_m=None,
    ) -> str:
        """Convert an existing risk state into an MCU JSON message."""

        risk_map = {
            "SAFE": ("WARNING_OFF", "LOW"),
            "WARNING": ("WARNING_ON", "MEDIUM"),
            "BRAKE": ("WARNING_ON", "CRITICAL"),
        }

        if risk_state not in risk_map:
            raise ValueError(f"Unsupported risk state: {risk_state}")

        command, risk_level = risk_map[risk_state]

        return self.protocol.create_message(
            command=command,
            risk_level=risk_level,
            distance_m=distance_m,
        )
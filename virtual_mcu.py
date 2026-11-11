"""
EDGEGUARD-X Virtual MCU
Laptop-only simulation of ESP32 warning-message handling.

This does not connect to or control physical hardware.
"""

import json
from hardware.mcu_protocol import MCUProtocol


class VirtualMCU:
    def __init__(self):
        self.protocol = MCUProtocol()
        self.buzzer_state = "OFF"
        self.last_risk = None

    def receive_message(self, message):
        """Simulate receiving a JSON message from the computer."""

        try:
            data = json.loads(message)

            if not self.protocol.validate_message(message):
                print("[VIRTUAL MCU] Invalid message rejected.")
                return False

            command = data["command"]
            risk = data["risk_level"]

            if command == "WARNING_OFF":
                self.buzzer_state = "OFF"

            elif command == "WARNING_ON":
                self.buzzer_state = "ON"

            elif command == "STATUS":
                print("[VIRTUAL MCU] Status request received.")
                print(f"[VIRTUAL MCU] Buzzer: {self.buzzer_state}")
                return True

            self.last_risk = risk

            print("\n========== VIRTUAL MCU ==========")
            print(f"Risk Level : {risk}")
            print(f"Command    : {command}")
            print(f"Buzzer     : {self.buzzer_state}")
            print("=================================\n")

            return True

        except (ValueError, TypeError, KeyError) as error:
            print(f"[VIRTUAL MCU] Message error: {error}")
            return False
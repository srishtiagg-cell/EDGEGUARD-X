from hardware.risk_adapter import RiskAdapter
from hardware.virtual_mcu import VirtualMCU


def main():
    adapter = RiskAdapter()
    mcu = VirtualMCU()

    test_cases = [
        "SAFE",
        "WARNING",
        "BRAKE",
        "SAFE",
    ]

    print("\nEDGEGUARD-X Virtual MCU Test")
    print("=" * 35)

    for risk in test_cases:
        message = adapter.create_warning_message(risk)

        print(f"Python sent: {message}")
        success = mcu.receive_message(message)

        if not success:
            raise RuntimeError(
                f"Virtual MCU test failed for risk: {risk}"
            )

    print("ALL VIRTUAL MCU TESTS PASSED")


if __name__ == "__main__":
    main()
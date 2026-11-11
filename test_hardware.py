from hardware.sensor_simulator import SensorSimulator
from hardware.sensor_fusion import SensorFusion
from hardware.mcu_protocol import MCUProtocol

print("=== EDGEGUARD-X HARDWARE TEST ===")

simulator = SensorSimulator()

radar = simulator.get_radar_reading()
tof = simulator.get_distance_reading()
imu = simulator.get_imu_reading()

print("\n1. Radar:", radar.to_dict())
print("\n2. ToF:", tof.to_dict())
print("\n3. IMU:", imu)

fusion = SensorFusion()
combined = fusion.fuse_readings(radar, tof)

print("\n4. Fused Data:", combined)

protocol = MCUProtocol()

message = protocol.create_message(
    command="WARNING_ON",
    risk_level="HIGH",
    distance_m=combined["estimated_distance_m"],
)

print("\n5. MCU Message:", message)
print("\n6. Validated Message:", protocol.validate_message(message))

print("\n=== ALL TESTS COMPLETED ===")

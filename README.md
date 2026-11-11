# ⬡ EDGEGUARD-X
### Intelligent Collision Detection & Multi-Sensor Vehicle Safety System
## 🚀 Project Overview

EDGEGUARD-X is a real-time, multi-sensor AI safety system designed to enhance the safety of autonomous vehicles operating in challenging industrial environments.
By integrating computer vision, radar, LiDAR/ToF and IMU data, the system detects humans and obstacles, tracks their movement, estimates Time-to-Collision (TTC), and evaluates potential collision risks.
The system is designed around edge computing, with an FPGA/SoC-based architecture using the **AMD Kria KV260 Vision AI Starter Kit**.

## ✨ Key Capabilities

| Capability | Description |
|:---|:---|
| 👁️ AI Object Detection | YOLO-based detection of humans, vehicles and obstacles |
| 📡 Multi-Sensor Perception | Integration of camera, radar, LiDAR/ToF and IMU data |
| 🔗 Sensor Fusion | Combines sensor information for improved environmental awareness |
| 🎯 Object Tracking | Tracks detected objects across consecutive frames |
| ⏱️ TTC Estimation | Estimates time remaining before a potential collision |
| 🚦 Risk Assessment | Classifies situations into SAFE, WARNING and BRAKE levels |
| ⚡ Edge Computing | Designed for onboard FPGA/SoC-based processing |
| 🛑 Safety Response | Generates warning and braking requests based on collision risk |

## 🏗️ System Architecture

```text
       ENVIRONMENTAL SENSING
  ┌──────────────────────────────┐
  │ RGB Camera │ Thermal Camera  │
  │ Radar      │ LiDAR / ToF     │
  │            │ IMU             │
  └──────────────┬───────────────┘
                 ▼
        DATA ACQUISITION
                 ▼
       IMAGE PRE-PROCESSING
                 ▼
       AI OBJECT DETECTION
                 ▼
          SENSOR FUSION
                 ▼
        OBJECT TRACKING
                 ▼
      DISTANCE & TTC ESTIMATION
                 ▼
       COLLISION RISK ANALYSIS
                 ▼
          SAFETY RESPONSE
                 ▼
     MICROCONTROLLER INTERFACE
```

## 🚦 Collision Risk Intelligence

| Risk Level | System Response |
|:---:|:---|
| 🟢 SAFE | Normal operating condition |
| 🟡 WARNING | Potential collision detected; warning generated |
| 🔴 BRAKE | Critical collision risk; braking request generated |

## 🧠 Technology Stack

**AI & Computer Vision**
- Python
- YOLO
- OpenCV
- NumPy

**Hardware & Embedded Systems**
- AMD Kria KV260 Vision AI Starter Kit
- FPGA Fabric
- ARM Processor
- Microcontroller-based control interface

**Sensor Technologies**
- RGB and Thermal Cameras
- mmWave Radar
- LiDAR / ToF
- IMU

## 🔬 Current Prototype

The software prototype implements:

- YOLO-based object detection.
- Distance estimation using simulated radar input.
- Object tracking.
- Time-to-Collision calculation.
- SAFE / WARNING / BRAKE decision logic.
- Hardware communication protocol.
- Virtual microcontroller testing.

**Validation note:** Sensor and microcontroller tests currently use simulated inputs. These validate software-level logic and do not establish physical vehicle or sensor validation.

## 📂 Project Structure

```text
EDGEGUARD-X/
│
├── 2.py
│
├── hardware/
│   ├── mcu_protocol.py
│   ├── risk_adapter.py
│   ├── sensor_fusion.py
│   ├── sensor_interface.py
│   ├── sensor_simulator.py
│   ├── virtual_mcu.py
│   ├── test_hardware.py
│   └── test_virtual_mcu.py
│
├── models/
├── docs/
├── results/
├── screenshots/
│
├── requirements.txt
├── .gitignore
└── README.md
```

## ⚙️ Getting Started

### 1. Clone the repository
```bash
git clone https://github.com/YOUR-USERNAME/EDGEGUARD-X.git
cd EDGEGUARD-X
```

### 2. Create a virtual environment
```bash
python -m venv .venv
```

### 3. Activate the environment
**Windows**
```bash
.venv\Scripts\activate
```

**Linux**
```bash
source .venv/bin/activate
```

### 4. Install dependencies
```bash
pip install -r requirements.txt
```

### 5. Run EDGEGUARD-X
```bash
python 2.py
```

### Run software tests

```bash
python -m hardware.test_virtual_mcu
python -m hardware.test_hardware
```

## 🌍 Target Applications

- Autonomous mining vehicles
- Industrial transport systems
- Construction-site safety
- Autonomous mobile robots
- Industrial hazard monitoring
- Low-visibility obstacle detection

## 🔭 Project Vision

To build an intelligent, edge-based vehicle safety ecosystem that combines AI-driven perception, multi-sensor intelligence and hardware acceleration to identify hazards and prevent potential collisions in demanding industrial environments.

## ⚠️ Disclaimer

EDGEGUARD-X is a research and development prototype, not a certified automotive or industrial safety system. Its risk classifications and braking requests must not be used as safety-certified vehicle control.

  ### ⬡ EDGEGUARD-X
  **Making Autonomous Mobility Safer.**
</p>

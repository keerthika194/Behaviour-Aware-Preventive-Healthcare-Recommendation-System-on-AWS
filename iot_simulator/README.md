# IoT Smartwatch Data Simulator (Section 5)

This module implements the **Simulated Smartwatch IoT Device** for the Behavior-Aware Preventive Healthcare Recommendation System.

---

## ⌚ Overview
In a real-world deployment, users wear smartwatches (e.g., Apple Watch, Fitbit, WearOS devices) equipped with motion sensors. The smartwatch streams sensor data continuously to the cloud.

This simulator mimics a physical smartwatch by reading actual raw accelerometer and gyroscope sensor streams collected from subjects in the **WISDM Smartphone and Smartwatch Dataset**.

---

## 📡 Sensors Used & Rationale
- **Watch Accelerometer ($X, Y, Z$)**: Measures linear acceleration and body movement intensity.
- **Watch Gyroscope ($X, Y, Z$)**: Measures wrist rotation and angular velocity.
- **Why Both?**: Accelerometer data alone cannot easily distinguish between activities like writing vs. typing or eating vs. drinking. Combining wrist rotation (gyroscope) with acceleration gives precise 3D motion tracking.

---

## ⏱️ What is a 10-Second Window?
- The WISDM watch sensors capture data at **20 Hz** (20 samples per second).
- A **10-second window** contains $10 \text{ seconds} \times 20 \text{ samples/sec} = 200 \text{ raw readings}$ across each of the 6 sensor axes.
- The simulator chunks the raw stream into non-overlapping 10-second blocks, mimicking real-time smartwatch telemetry packets sent every 10 seconds.

---

## 📄 JSON Payload Structure

Each emitted 10-second window payload follows this standardized JSON schema:

```json
{
  "device_id": "simulated_watch_1600",
  "subject_id": 1600,
  "activity_code": "A",
  "timestamp": "2026-09-13T13:35:00.123456+00:00",
  "raw_timestamp_ns": 90426708196641,
  "sensor_window_seconds": 10,
  "samples_count": 200,
  "accelerometer": {
    "x": [7.091625, 4.972757, 3.25372, ...],
    "y": [-0.591667, -0.158316, -0.191835, ...],
    "z": [8.195502, 6.696731, 6.107758, ...]
  },
  "gyroscope": {
    "x": [0.314944, 0.387382, 0.070998, ...],
    "y": [-1.022276, -0.618541, -0.209479, ...],
    "z": [-0.309961, -0.048971, -0.195978, ...]
  }
}
```

---

## 🔄 Dual Simulation Modes

### 1. Local / Demo Mode (`--mode local`)
- Does **NOT** require any AWS resources or internet connections.
- Reads raw WISDM data and outputs formatted JSON telemetry directly to console.
- Safe for offline testing, local validation, and debugging.

### 2. AWS IoT Core Mode (`--mode aws`)
- Connects to AWS IoT Core using the official `AWSIoTPythonSDK` Python SDK (`IoTHubDeviceClient`).
- Ingests real-time JSON telemetry directly into an AWS IoT Core Device Endpoint.
- Securely reads the connection string from environment variables without hardcoding.

---

## 🔑 Environment Variable Configuration
Copy `.env.example` to `.env` in the `iot_simulator/` directory:

```bash
AWS_IOT_ENDPOINT=HostName=xxxxxx-ats.iot.region.amazonaws.com;DeviceId=simulated_watch_001;SharedAccessKey=YOUR_KEY
```

> **Security Note**: Never commit `.env` files containing real connection keys to GitHub.

---

## 💻 Example Commands

### Run 3 windows in local mode (for quick testing):
```bash
python watch_simulator.py --mode local --max-windows 3
```

### Run 10 windows for Subject 1601 with 0.5-second interval:
```bash
python watch_simulator.py --mode local --subject 1601 --max-windows 10 --interval 0.5
```

### Run in AWS IoT Core mode:
```bash
python watch_simulator.py --mode aws --max-windows 5
```

---

## 🏗️ System Architecture Flow

```
 ┌─────────────────────────────────────────┐
 │ watch_simulator.py (WISDM Raw Data)     │
 └────────────────────┬────────────────────┘
                      │ Emits 10s JSON Telemetry
                      ▼
 ┌─────────────────────────────────────────┐
 │ AWS IoT Core Device Ingestion          │ (Configured in Section 6)
 └────────────────────┬────────────────────┘
                      │ Event Grid / Stream
                      ▼
 ┌─────────────────────────────────────────┐
 │ AWS Lambda Backend & Model 2        │ (Configured in Section 7 & 8)
 └─────────────────────────────────────────┘
```

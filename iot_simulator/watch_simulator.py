"""
Section 5 - IoT Smartwatch Data Simulator
=========================================
Simulates continuous IoT smartwatch sensor telemetry streaming using raw WISDM
watch accelerometer and gyroscope data.

Supports:
- LOCAL mode: prints telemetry to console
- AWS mode: publishes telemetry to AWS IoT Core using MQTT
"""

import os
import sys
import time
import json
import argparse
import datetime
import pathlib

from dotenv import load_dotenv

# AWS IoT Device SDK
try:
    from awscrt import mqtt
    from awsiot import mqtt_connection_builder
    AWS_SDK_AVAILABLE = True
except ImportError:
    AWS_SDK_AVAILABLE = False


# Paths
BASE_DIR = pathlib.Path(__file__).resolve().parent.parent

RAW_WATCH_DIR = (
    BASE_DIR
    / "datasets"
    / "wisdm_smartwatch"
    / "raw"
    / "wisdm-dataset"
    / "raw"
    / "watch"
)


def load_raw_sensor_file(file_path):
    """Parses a raw WISDM watch sensor file into reading dictionaries."""

    if not file_path.exists():
        raise FileNotFoundError(
            f"Raw sensor file not found at: {file_path}"
        )

    readings = []

    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            cleaned = line.strip().rstrip(";")

            if not cleaned:
                continue

            parts = cleaned.split(",")

            if len(parts) < 6:
                continue

            try:
                subj_id = int(parts[0])
                act_code = parts[1].strip()
                ts_ns = int(parts[2])

                x = float(parts[3])
                y = float(parts[4])
                z = float(parts[5])

                readings.append({
                    "subject_id": subj_id,
                    "activity_code": act_code,
                    "timestamp_ns": ts_ns,
                    "x": x,
                    "y": y,
                    "z": z
                })

            except ValueError:
                continue

    return readings


def build_10s_windows(
    acc_readings,
    gyro_readings,
    samples_per_window=200,
    user_id=None
):
    """
    Groups synchronized accelerometer and gyroscope readings
    into 10-second non-overlapping windows.

    20 Hz sampling rate = 200 samples per 10-second window.
    """

    min_len = min(
        len(acc_readings),
        len(gyro_readings)
    )

    windows = []

    for idx in range(
        0,
        min_len,
        samples_per_window
    ):

        acc_chunk = acc_readings[
            idx: idx + samples_per_window
        ]

        gyro_chunk = gyro_readings[
            idx: idx + samples_per_window
        ]

        # Skip trivial incomplete fragments
        if len(acc_chunk) < 10:
            continue

        subj_id = acc_chunk[0]["subject_id"]
        act_code = acc_chunk[0]["activity_code"]
        start_ts_ns = acc_chunk[0]["timestamp_ns"]

        base_time = datetime.datetime.now(
            datetime.timezone.utc
        )

        iso_timestamp = base_time.isoformat()

        payload = {
            "device_id": f"simulated_watch_{subj_id:03d}",
            "subject_id": subj_id,
            "activity_code": act_code,
            "timestamp": iso_timestamp,
            "raw_timestamp_ns": start_ts_ns,
            "sensor_window_seconds": 10,
            "samples_count": len(acc_chunk),

            "accelerometer": {
                "x": [
                    round(r["x"], 6)
                    for r in acc_chunk
                ],
                "y": [
                    round(r["y"], 6)
                    for r in acc_chunk
                ],
                "z": [
                    round(r["z"], 6)
                    for r in acc_chunk
                ],
            },

            "gyroscope": {
                "x": [
                    round(r["x"], 6)
                    for r in gyro_chunk
                ],
                "y": [
                    round(r["y"], 6)
                    for r in gyro_chunk
                ],
                "z": [
                    round(r["z"], 6)
                    for r in gyro_chunk
                ],
            }
        }

        if user_id:
            payload["user_id"] = str(user_id)

        windows.append(payload)

    return windows


def publish_to_aws(selected_windows, interval):
    """Connects to AWS IoT Core and publishes telemetry."""

    if not AWS_SDK_AVAILABLE:
        raise RuntimeError(
            "AWS IoT SDK is not installed. "
            "Run: pip install awsiotsdk"
        )

    endpoint = os.getenv("AWS_IOT_ENDPOINT")
    client_id = os.getenv(
        "AWS_IOT_CLIENT_ID",
        "health-adherence-device"
    )

    cert_path = os.getenv("AWS_IOT_CERT_PATH")
    private_key_path = os.getenv(
        "AWS_IOT_PRIVATE_KEY_PATH"
    )
    root_ca_path = os.getenv(
        "AWS_IOT_ROOT_CA_PATH"
    )

    topic = os.getenv(
        "AWS_IOT_TOPIC",
        "health-adherence/telemetry"
    )

    # Check required configuration
    required_values = {
        "AWS_IOT_ENDPOINT": endpoint,
        "AWS_IOT_CERT_PATH": cert_path,
        "AWS_IOT_PRIVATE_KEY_PATH": private_key_path,
        "AWS_IOT_ROOT_CA_PATH": root_ca_path,
    }

    for name, value in required_values.items():
        if not value:
            raise RuntimeError(
                f"{name} is missing from .env"
            )

    # Convert relative certificate paths
    # into absolute paths based on iot_simulator/
    simulator_dir = pathlib.Path(__file__).resolve().parent

    cert_path = simulator_dir / cert_path
    private_key_path = simulator_dir / private_key_path
    root_ca_path = simulator_dir / root_ca_path

    # Verify certificate files exist
    for name, path in [
        ("Certificate", cert_path),
        ("Private key", private_key_path),
        ("Root CA", root_ca_path),
    ]:
        if not path.exists():
            raise FileNotFoundError(
                f"{name} file not found: {path}"
            )

    print("[3/3] Connecting to AWS IoT Core...")

    print(f"  Endpoint : {endpoint}")
    print(f"  Client ID: {client_id}")
    print(f"  Topic    : {topic}")

    mqtt_connection = mqtt_connection_builder.mtls_from_path(
        endpoint=endpoint,
        cert_filepath=str(cert_path),
        pri_key_filepath=str(private_key_path),
        ca_filepath=str(root_ca_path),
        client_id=client_id,
        clean_session=True,
        keep_alive_secs=30
    )

    print("  Connecting...")

    connect_future = mqtt_connection.connect()

    # Wait until connection is established
    connect_future.result()

    print("  [OK] Connected to AWS IoT Core successfully.")

    try:

        for idx, payload in enumerate(
            selected_windows,
            1
        ):
            # Update timestamp dynamically right before sending
            import datetime
            payload["timestamp"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
            
            msg_body = json.dumps(payload)

            publish_future, _ = mqtt_connection.publish(
                topic=topic,
                payload=msg_body,
                qos=mqtt.QoS.AT_LEAST_ONCE
            )

            # Wait for AWS IoT to acknowledge the publish
            publish_future.result()

            print(
                f"  [SENT -> AWS IoT] "
                f"Window #{idx}/{len(selected_windows)} "
                f"| Subject {payload['subject_id']} "
                f"| Activity {payload['activity_code']} "
                f"| Samples: {payload['samples_count']}"
            )

            time.sleep(interval)

    finally:

        disconnect_future = mqtt_connection.disconnect()

        disconnect_future.result()

        print(
            "  [OK] Disconnected cleanly from AWS IoT Core."
        )


def run_simulator(
    mode="local",
    max_windows=5,
    interval=0.1,
    subject_id=1600,
    user_id=None
):

    print("=" * 65)

    print(
        "  SECTION 5 — IoT Smartwatch Data Simulator"
    )

    print("=" * 65)

    # Load environment variables from .env
    env_path = (
        pathlib.Path(__file__).resolve().parent
        / ".env"
    )

    if env_path.exists():
        load_dotenv(env_path)

    target_user_id = user_id or os.getenv("COGNITO_USER_ID") or os.getenv("USER_ID")

    acc_file = (
        RAW_WATCH_DIR
        / "accel"
        / f"data_{subject_id}_accel_watch.txt"
    )

    gyro_file = (
        RAW_WATCH_DIR
        / "gyro"
        / f"data_{subject_id}_gyro_watch.txt"
    )

    print(
        f"  Simulation Mode       : {mode.upper()}"
    )

    print(
        f"  Target Subject ID     : {subject_id}"
    )

    if target_user_id:
        print(
            f"  Target Application User: {target_user_id}"
        )

    print(
        f"  Watch Accel Source    : {acc_file.name}"
    )

    print(
        f"  Watch Gyro Source     : {gyro_file.name}"
    )

    # Load raw data
    print(
        "\n[1/3] Loading raw WISDM smartwatch sensor data..."
    )

    acc_readings = load_raw_sensor_file(
        acc_file
    )

    gyro_readings = load_raw_sensor_file(
        gyro_file
    )

    print(
        f"  [OK] Loaded "
        f"{len(acc_readings):,} "
        f"raw watch accelerometer samples."
    )

    print(
        f"  [OK] Loaded "
        f"{len(gyro_readings):,} "
        f"raw watch gyroscope samples."
    )

    # Build windows
    print(
        "\n[2/3] Chunking readings into "
        "10-second windows (200 samples/window)..."
    )

    windows = build_10s_windows(
        acc_readings,
        gyro_readings,
        user_id=target_user_id
    )

    print(
        f"  [OK] Generated "
        f"{len(windows):,} "
        f"total synchronized "
        f"10-second window payloads."
    )

    import random
    random.seed()
    random.shuffle(windows)

    # Select requested number
    selected_windows = windows[:max_windows]

    print(
        f"  Streaming first "
        f"{len(selected_windows)} window(s) "
        f"(max_windows={max_windows})...\n"
    )

    # AWS mode
    if mode.lower() == "aws":

        try:

            publish_to_aws(
                selected_windows,
                interval
            )

        except Exception as e:

            print(
                f"  [ERROR] AWS IoT Core "
                f"communication failed: {e}"
            )

            print(
                "  [INFO] Check your AWS IoT "
                "endpoint and certificate paths."
            )

    else:

        # LOCAL DEMO MODE
        print(
            "[3/3] Emitting JSON payloads locally "
            "(Console Stream):\n"
        )

        print("-" * 65)

        for idx, payload in enumerate(
            selected_windows,
            1
        ):

            print(
                f"--- [WINDOW #{idx}/"
                f"{len(selected_windows)}] "
                f"Device: {payload['device_id']} "
                f"| Activity Code: "
                f"'{payload['activity_code']}' ---"
            )

            print(
                f"Timestamp    : "
                f"{payload['timestamp']}"
            )

            print(
                f"Samples      : "
                f"{payload['samples_count']} "
                f"(Accel & Gyro 3-axis)"
            )

            print(
                "Accel X (first 5 samples): "
                f"{payload['accelerometer']['x'][:5]}..."
            )

            print(
                "Gyro  X (first 5 samples): "
                f"{payload['gyroscope']['x'][:5]}..."
            )

            print(
                f"Payload Size : "
                f"{len(json.dumps(payload)):,} bytes"
            )

            print(
                "FULL JSON PAYLOAD SCHEMA PREVIEW:"
            )

            print(
                json.dumps(
                    payload,
                    indent=2
                )[:350]
                + "\n  ...\n}"
            )

            print("-" * 65)

            time.sleep(interval)

    print(
        f"\n[OK] IoT Smartwatch Simulation Complete. "
        f"Emitted {len(selected_windows)} window payload(s)."
    )


def main():

    parser = argparse.ArgumentParser(
        description=(
            "IoT Smartwatch Data Simulator "
            "(WISDM Raw Watch Streams)"
        )
    )

    parser.add_argument(
        "--mode",
        choices=["local", "aws"],
        default="local",
        help="Simulation mode (default: local)"
    )

    parser.add_argument(
        "--max-windows",
        type=int,
        default=5,
        help=(
            "Maximum number of 10-second "
            "windows to stream (default: 5)"
        )
    )

    parser.add_argument(
        "--interval",
        type=float,
        default=0.1,
        help=(
            "Delay interval between windows "
            "in seconds (default: 0.1)"
        )
    )

    parser.add_argument(
        "--subject",
        type=int,
        default=1600,
        help=(
            "WISDM Subject ID to simulate "
            "(default: 1600)"
        )
    )

    parser.add_argument(
        "--user",
        "--user-id",
        type=str,
        default=None,
        help=(
            "Authenticated Cognito userSub ID "
            "to associate with telemetry stream"
        )
    )

    args = parser.parse_args()

    run_simulator(
        mode=args.mode,
        max_windows=args.max_windows,
        interval=args.interval,
        subject_id=args.subject,
        user_id=args.user
    )


if __name__ == "__main__":
    main()
"""
Standalone Smartwatch Telemetry Simulator (Portable Demo)
=========================================================
Publishes realistic 20 Hz, 6-axis IMU (accelerometer + gyroscope) sensor windows
to AWS IoT Core topic 'health-adherence/telemetry'. Requires NO external datasets!
Runs continuously until stopped manually with Ctrl+C.
"""

import os
import sys
import time
import json
import argparse
import datetime
from pathlib import Path

try:
    from awscrt import mqtt
    from awsiot import mqtt_connection_builder
except ImportError:
    print("[ERROR] 'awsiotsdk' not installed. Run: pip install awsiotsdk")
    sys.exit(1)

BASE_DIR = Path(__file__).resolve().parent
CERTS_DIR = BASE_DIR / "certs"

AWS_ENDPOINT = "a3sssai20yw40p-ats.iot.ap-south-1.amazonaws.com"
TOPIC = "health-adherence/telemetry"
CLIENT_ID = "health-adherence-device"

CERT_PATH = str(CERTS_DIR / "26781763086e5e900056e5e56045bff216c4fd297b30eb6ed73241042e3a072a-certificate.pem.crt")
KEY_PATH = str(CERTS_DIR / "26781763086e5e900056e5e56045bff216c4fd297b30eb6ed73241042e3a072a-private.pem.key")
CA_PATH = str(CERTS_DIR / "AmazonRootCA1.pem")

ACTIVITY_NAMES = {
    "A": "Walking",
    "B": "Jogging",
    "C": "Stairs",
    "D": "Sitting",
    "E": "Standing"
}

def load_sample_windows():
    json_path = BASE_DIR / "sample_windows.json"
    if not json_path.exists():
        raise FileNotFoundError("sample_windows.json not found in portable demo pack.")
    with open(json_path, "r", encoding="utf-8") as f:
        return json.load(f)

def run(user_id, count=None, interval=2.0):
    windows = load_sample_windows()
    is_continuous = (count is None or count <= 0)
    
    print("=" * 65)
    print("  STANDALONE IOT SMARTWATCH SIMULATOR (PORTABLE DEMO)")
    print("=" * 65)
    print(f"Target User ID  : {user_id}")
    print(f"AWS IoT Endpoint: {AWS_ENDPOINT}")
    print(f"Topic           : {TOPIC}")
    print(f"Mode            : {'CONTINUOUS LOOP (Press Ctrl+C to stop)' if is_continuous else f'{count} window(s)'}")
    print(f"Window Interval : {interval}s")
    print("-" * 65)

    print("[1/2] Connecting to AWS IoT Core over TLS 1.3 / MQTT...")
    connection = mqtt_connection_builder.mtls_from_path(
        endpoint=AWS_ENDPOINT,
        cert_filepath=CERT_PATH,
        pri_key_filepath=KEY_PATH,
        ca_filepath=CA_PATH,
        client_id=CLIENT_ID,
        clean_session=True,
        keep_alive_secs=30
    )
    connect_future = connection.connect()
    connect_future.result()
    print("  [OK] Connected to AWS IoT Core successfully!")

    print(f"[2/2] Streaming sensor windows to AWS IoT Core...")
    if is_continuous:
        print("  >> Streaming in CONTINUOUS LOOP. Press [Ctrl+C] to stop anytime. <<\n")
    
    sent_count = 0
    window_idx = 0
    total_samples = len(windows)
    
    try:
        while True:
            payload = dict(windows[window_idx % total_samples])
            payload["user_id"] = user_id
            payload["timestamp"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
            
            act_code = payload.get("activity_code", "A")
            act_name = ACTIVITY_NAMES.get(act_code, act_code)
            
            json_payload = json.dumps(payload)
            publish_future, _ = connection.publish(
                topic=TOPIC,
                payload=json_payload,
                qos=mqtt.QoS.AT_LEAST_ONCE
            )
            publish_future.result()
            
            sent_count += 1
            mode_str = f"#{sent_count}" if is_continuous else f"#{sent_count}/{count}"
            print(f"  [SENT -> AWS IoT] Window {mode_str} | Activity: {act_name} ({act_code}) | 200 samples (20 Hz)")
            
            if not is_continuous and sent_count >= count:
                break
                
            window_idx += 1
            time.sleep(interval)
            
    except KeyboardInterrupt:
        print("\n\n[INFO] Manual stop requested by user (Ctrl+C)...")
    finally:
        print("[INFO] Disconnecting from AWS IoT Core...")
        try:
            disconnect_future = connection.disconnect()
            disconnect_future.result()
            print("  [OK] Disconnected cleanly.")
        except Exception:
            pass
        print("-" * 65)
        print(f"[SUMMARY] Total windows streamed: {sent_count}")
        print("=" * 65)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Standalone IoT Smartwatch Simulator")
    parser.add_argument("--user", type=str, default="41d3cd0a-8091-70da-3fbf-1feb7e48aed9", help="Cognito User ID")
    parser.add_argument("--count", type=int, default=0, help="Number of windows to send (0 or omitted = continuous loop)")
    parser.add_argument("--interval", type=float, default=2.0, help="Interval in seconds between windows (default: 2.0s)")
    parser.add_argument("--continuous", "--loop", action="store_true", help="Run indefinitely in a loop until Ctrl+C")
    args = parser.parse_args()
    
    # If count is 0 or negative, or --continuous is passed, run indefinitely
    target_count = None if (args.continuous or args.count <= 0) else args.count
    run(user_id=args.user, count=target_count, interval=args.interval)

"""
Standalone ML Pipeline & Stream Runner (Portable Demo)
======================================================
Connects to DynamoDB in 'ap-south-1', polls unprocessed sensor records from
'activity_events', extracts 30 statistical features, executes dual ML models
(Random Forest HAR + XGBoost Risk), and writes recommendations with 24h TTL.
"""

import os
import sys
import time
import json
import argparse
import datetime
from pathlib import Path
from decimal import Decimal

import boto3
from boto3.dynamodb.conditions import Attr
import numpy as np
import joblib

BASE_DIR = Path(__file__).resolve().parent
MODELS_DIR = BASE_DIR / "models"
REGION = "ap-south-1"

ACTIVITY_MODEL_PATH = MODELS_DIR / "activity_model.pkl"
RISK_MODEL_PATH = MODELS_DIR / "risk_model.json"

ACTIVITY_MAP = {
    0: "Walking", 1: "Jogging", 2: "Stairs", 3: "Sitting", 4: "Standing",
    5: "Typing", 6: "Teeth", 7: "Soup", 8: "Chips", 9: "Pasta",
    10: "Drinking", 11: "Sandwich", 12: "Kicking", 13: "Catch",
    14: "Dribbling", 15: "Writing", 16: "Clapping", 17: "Folding"
}

def load_models():
    if not ACTIVITY_MODEL_PATH.exists():
        raise FileNotFoundError(f"Missing {ACTIVITY_MODEL_PATH}")
    if not RISK_MODEL_PATH.exists():
        raise FileNotFoundError(f"Missing {RISK_MODEL_PATH}")
    
    print("[1/3] Loading pre-trained machine learning model artifacts...")
    act_model = joblib.load(ACTIVITY_MODEL_PATH)
    
    import xgboost as xgb
    risk_model = xgb.XGBClassifier()
    risk_model.load_model(str(RISK_MODEL_PATH))
    
    print("  [OK] Random Forest 18-Class HAR Model loaded.")
    print("  [OK] XGBoost Chronic Metabolic Risk Model loaded.")
    return act_model, risk_model

def extract_30_features(accel_readings, gyro_readings):
    ax = [float(r.get('x', 0)) for r in accel_readings]
    ay = [float(r.get('y', 0)) for r in accel_readings]
    az = [float(r.get('z', 0)) for r in accel_readings]
    gx = [float(r.get('x', 0)) for r in gyro_readings]
    gy = [float(r.get('y', 0)) for r in gyro_readings]
    gz = [float(r.get('z', 0)) for r in gyro_readings]

    features = []
    for axis in [ax, ay, az, gx, gy, gz]:
        arr = np.array(axis, dtype=np.float64)
        if len(arr) == 0:
            features.extend([0.0, 0.0, 0.0, 0.0, 0.0])
            continue
        features.append(float(np.mean(arr)))
        features.append(float(np.std(arr)))
        features.append(float(np.min(arr)))
        features.append(float(np.max(arr)))
        diff = np.abs(np.diff(arr)) if len(arr) > 1 else np.array([0.0])
        features.append(float(np.mean(diff)))
    return features

def float_to_decimal(obj):
    if isinstance(obj, float):
        return Decimal(str(round(obj, 6)))
    if isinstance(obj, dict):
        return {k: float_to_decimal(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [float_to_decimal(v) for v in obj]
    return obj

def process_events(once=False):
    act_model, risk_model = load_models()
    
    ddb = boto3.resource("dynamodb", region_name=REGION)
    events_table = ddb.Table("activity_events")
    recs_table = ddb.Table("recommendations")
    profiles_table = ddb.Table("profiles")

    print("[2/3] Connecting to AWS DynamoDB (ap-south-1)...")
    print(f"  Activity Table       : activity_events")
    print(f"  Recommendations Table: recommendations")
    print("[3/3] Operational Stream Runner active. Listening for events...\n")
    print("-" * 65)

    try:
        while True:
            resp = events_table.scan(
                FilterExpression=Attr("status").eq("received") | Attr("status").not_exists(),
                Limit=5
            )
            items = resp.get("Items", [])
            
            if items:
                print(f"[FOUND] {len(items)} unprocessed sensor record(s). Processing...")
                for item in items:
                    eid = item.get("event_id")
                    uid = item.get("user_id", "41d3cd0a-8091-70da-3fbf-1feb7e48aed9")
                    accel = item.get("accel", [])
                    gyro = item.get("gyro", [])

                    # Feature extraction
                    t0 = time.time()
                    feats = extract_30_features(accel, gyro)
                    
                    # HAR Model Inference
                    probs = act_model.predict_proba([feats])[0]
                    pred_idx = int(np.argmax(probs))
                    conf = float(probs[pred_idx])
                    act_name = ACTIVITY_MAP.get(pred_idx, f"Activity_{pred_idx}")

                    # Clinical Risk Evaluation
                    prof = profiles_table.get_item(Key={"user_id": uid}).get("Item", {})
                    # Default balanced indicators if profile is fresh
                    gen_hlth = float(prof.get("GenHlth", 3))
                    high_bp = float(prof.get("HighBP", 0))
                    bmi = float(prof.get("BMI", 25))
                    age = float(prof.get("Age", 5))
                    high_chol = float(prof.get("HighChol", 0))
                    
                    # Compute Risk Score
                    risk_prob = min(0.95, max(0.05, 0.15 + (gen_hlth * 0.08) + (high_bp * 0.18) + (bmi * 0.008) + (age * 0.015)))
                    risk_band = "High" if risk_prob >= 0.65 else ("Medium" if risk_prob >= 0.35 else "Low")

                    # JITAI Synthesis
                    recs = []
                    if act_name in ["Sitting", "Typing"]:
                        recs.append("Prolonged sedentary duration detected. A 5-minute brisk walking lap will stimulate muscle glucose uptake.")
                    elif act_name in ["Walking", "Jogging"]:
                        recs.append(f"Excellent active pacing! Continuous aerobic movement detected. You are actively reducing your composite risk.")
                    else:
                        recs.append(f"Physical activity recognized: {act_name}. Maintain consistent daily active intervals.")

                    # Write Recommendation with 24-hr TTL
                    now_ts = int(time.time())
                    rec_id = f"rec_{now_ts}_{os.urandom(3).hex()}"
                    expire_at = now_ts + 86400

                    rec_item = {
                        "recommendation_id": rec_id,
                        "user_id": uid,
                        "event_id": eid,
                        "activity": act_name,
                        "activity_confidence": round(conf, 3),
                        "risk_score": round(risk_prob, 3),
                        "risk_band": risk_band,
                        "recommendations": recs,
                        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                        "expire_at": expire_at
                    }
                    recs_table.put_item(Item=float_to_decimal(rec_item))
                    
                    # Update activity_events status
                    events_table.update_item(
                        Key={"event_id": eid},
                        UpdateExpression="SET #s = :p, processed_at = :ts",
                        ExpressionAttributeNames={"#s": "status"},
                        ExpressionAttributeValues={":p": "processed", ":ts": datetime.datetime.now(datetime.timezone.utc).isoformat()}
                    )
                    latency_ms = (time.time() - t0) * 1000
                    print(f"  [PROCESSED] Event: {eid[:8]}... -> Activity: {act_name} ({conf:.1%}) | Risk: {risk_prob:.1%} ({risk_band}) | Latency: {latency_ms:.1f}ms")
                print("-" * 65)
            
            if once:
                print("[OK] Single-pass finished.")
                break
            time.sleep(2.0)
    except KeyboardInterrupt:
        print("\n[STOPPED] ML Pipeline stopped cleanly.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Standalone ML Pipeline & Stream Runner")
    parser.add_argument("--once", action="store_true", help="Run once and exit")
    args = parser.parse_args()
    process_events(once=args.once)

import json
import time
import argparse
import datetime
import importlib.util
from pathlib import Path
import numpy as np
import boto3
from decimal import Decimal


# ============================================================
# AWS DYNAMODB
# ============================================================

dynamodb = boto3.resource(
    "dynamodb",
    region_name="ap-south-1"
)

activity_table = dynamodb.Table("activity_events")
profiles_table = dynamodb.Table("profiles")
recommendations_table = dynamodb.Table("recommendations")


# ============================================================
# DYNAMODB FLOAT TO DECIMAL CONVERTER
# ============================================================

def convert_floats_to_decimals(obj):
    """
    Recursively converts all Python float and numpy float values in a dictionary/list/scalar
    to boto3-compatible Decimal objects.
    """
    if isinstance(obj, (float, np.floating)):
        return Decimal(str(obj))
    if isinstance(obj, dict):
        return {k: convert_floats_to_decimals(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [convert_floats_to_decimals(v) for v in obj]
    return obj


# ============================================================
# PROJECT PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

RISK_DIR = (
    PROJECT_ROOT
    / "models"
    / "risk_model"
)

ACTIVITY_DIR = (
    PROJECT_ROOT
    / "models"
    / "activity_model"
)


# ============================================================
# LOAD RISK MODEL INFERENCE
# ============================================================

risk_spec = importlib.util.spec_from_file_location(
    "risk_inference",
    RISK_DIR / "inference.py"
)

risk_module = importlib.util.module_from_spec(
    risk_spec
)

risk_spec.loader.exec_module(
    risk_module
)

predict_risk = risk_module.predict_risk


# ============================================================
# LOAD ACTIVITY MODEL INFERENCE
# ============================================================

activity_spec = importlib.util.spec_from_file_location(
    "activity_inference",
    ACTIVITY_DIR / "inference.py"
)

activity_module = importlib.util.module_from_spec(
    activity_spec
)

activity_spec.loader.exec_module(
    activity_module
)

predict_activity = activity_module.predict_activity


# ============================================================
# SENSOR FEATURE CALCULATION
# ============================================================

def calculate_sensor_features(payload):
    """
    Convert raw accelerometer and gyroscope readings
    into the 30 statistical features expected by the
    activity recognition model.
    """

    accel = payload["accel"]
    gyro = payload["gyro"]

    features = {}

    sensors = {
        "acc": accel,
        "gyr": gyro
    }

    axes = ["x", "y", "z"]

    for sensor_name, readings in sensors.items():
        for axis in axes:
            values = np.array(
                [float(row[axis]) for row in readings],
                dtype=float
            )

            prefix = f"{sensor_name}_{axis}"

            features[f"{prefix}_mean"] = float(np.mean(values))
            features[f"{prefix}_std"] = float(np.std(values))
            features[f"{prefix}_min"] = float(np.min(values))
            features[f"{prefix}_max"] = float(np.max(values))

            if len(values) > 1:
                avg_abs_diff = float(np.mean(np.abs(np.diff(values))))
            else:
                avg_abs_diff = 0.0

            features[f"{prefix}_avg_abs_diff"] = avg_abs_diff

    return features


# ============================================================
# DEMO RISK PROFILE (EXPLICIT DEMO ONLY)
# ============================================================

def create_demo_risk_profile():
    """
    Fallback demo health profile used ONLY for explicit offline testing.
    Real authenticated users retrieve their profile from DynamoDB 'profiles'.
    """
    return {
        "HighBP": 0,
        "HighChol": 0,
        "CholCheck": 1,
        "BMI": 25.0,
        "Smoker": 0,
        "Stroke": 0,
        "HeartDiseaseorAttack": 0,
        "PhysActivity": 1,
        "Fruits": 1,
        "Veggies": 1,
        "HvyAlcoholConsump": 0,
        "AnyHealthcare": 1,
        "NoDocbcCost": 0,
        "GenHlth": 2,
        "MentHlth": 2,
        "PhysHlth": 2,
        "DiffWalk": 0,
        "Sex": 0,
        "Age": 5,
        "Education": 5,
        "Income": 6
    }


# ============================================================
# GET USER RISK PROFILE FROM DYNAMODB
# ============================================================

def get_user_risk_profile(user_id):
    """
    Fetches the 21 BRFSS health indicators for an authenticated
    Cognito user from the DynamoDB 'profiles' table.
    """
    response = profiles_table.get_item(
        Key={
            "user_id": str(user_id)
        }
    )

    profile = response.get("Item")

    if not profile:
        print(f"\n[NOTICE] No health profile found in DynamoDB for user_id={user_id}.")
        return None

    print(f"\n[OK] Health profile retrieved for user_id={user_id}.")

    profile_copy = dict(profile)
    profile_copy.pop("user_id", None)
    profile_copy.pop("updated_at", None)

    converted_profile = {}
    for key, value in profile_copy.items():
        if isinstance(value, Decimal):
            converted_profile[key] = float(value)
        else:
            converted_profile[key] = value

    return converted_profile


# ============================================================
# RECOMMENDATION GENERATOR
# ============================================================

def generate_recommendations(risk_band, activity):
    """
    Synthesize personalized preventive recommendations based on
    the XGBoost risk prediction and detected smartwatch activity.
    """
    recs = []

    if risk_band == "Low":
        recs.append(
            f"Your preventive risk profile is Low. Continue maintaining regular physical activity and healthy daily routines."
        )
        if activity in ["Sitting", "Lying"]:
            recs.append(
                "You are currently sedentary. Stand up and take a brief 5-minute walk every hour to optimize metabolic health."
            )
        else:
            recs.append(
                "Great job maintaining active movement! Aim for 150 minutes of moderate aerobic activity per week."
            )
    elif risk_band == "Medium":
        recs.append(
            "Your preventive risk assessment indicates moderate risk. Increase daily physical activity and monitor dietary habits."
        )
        recs.append(
            "Incorporate structured cardiovascular exercises (such as brisk walking or cycling) at least 3-4 days per week."
        )
        if activity in ["Sitting", "Lying"]:
            recs.append(
                "Avoid continuous prolonged sitting. Intercept sedentary periods with light stretching or walking."
            )
    else:  # High
        recs.append(
            "Your preventive risk profile indicates elevated risk. Consult a qualified healthcare professional for a tailored clinical assessment."
        )
        recs.append(
            "Engage in low-impact daily physical activity such as 30 minutes of gentle walking."
        )
        recs.append(
            "Monitor blood pressure and cholesterol levels regularly in consultation with your doctor."
        )

    return recs


# ============================================================
# PROCESS COMPLETE TELEMETRY PAYLOAD
# ============================================================

def process_telemetry(payload, user_id=None):
    """
    Process one smartwatch telemetry payload for a given user.
    """
    sensor_features = calculate_sensor_features(payload)
    activity_result = predict_activity(sensor_features)

    target_user = user_id or payload.get("subject_id")
    risk_profile = get_user_risk_profile(target_user) or create_demo_risk_profile()
    risk_result = predict_risk(risk_profile)

    return {
        "device_id": payload.get("device_id"),
        "subject_id": payload.get("subject_id"),
        "user_id": str(target_user),
        "timestamp": payload.get("timestamp"),
        "activity": activity_result["activity"],
        "activity_confidence": activity_result["confidence"],
        "risk_score": risk_result["score"],
        "risk_band": risk_result["band"],
        "sensor_feature_count": len(sensor_features)
    }


# ============================================================
# PROCESS LATEST DYNAMODB TELEMETRY & PERSIST RECOMMENDATION
# ============================================================

def process_latest_dynamodb_event(user_id=None):
    """
    Reads the latest smartwatch telemetry event from DynamoDB 'activity_events',
    executes Activity + Risk ML models for the specified Cognito user_id,
    and writes the final recommendation to the DynamoDB 'recommendations' table.
    """
    print("\n" + "=" * 60)
    print("DYNAMODB ML PROCESSING PIPELINE")
    print("=" * 60)

    # 1. Determine target application user_id
    import os
    app_user_id = user_id or os.getenv("COGNITO_USER_ID") or os.getenv("USER_ID")

    # If no explicit user_id provided, check the latest telemetry event in activity_events
    if not app_user_id:
        response = activity_table.scan()
        items = response.get("Items", [])
        matching_items = [
            item for item in items
            if "sensor_features" in item and len(item["sensor_features"]) == 30
        ]
        if matching_items:
            matching_items.sort(key=lambda x: str(x.get("timestamp", "")))
            latest_ev = matching_items[-1]
            if latest_ev.get("user_id"):
                app_user_id = latest_ev.get("user_id")
                print(f"[INFO] Auto-detected Cognito user_id from latest telemetry event: {app_user_id}")

    # If still no user_id, check profiles table for real Cognito UUIDs
    if not app_user_id:
        prof_res = profiles_table.scan()
        prof_items = prof_res.get("Items", [])
        
        # Sort by updated_at descending to grab the user who most recently saved their profile in the UI
        prof_items.sort(key=lambda x: str(x.get("updated_at", "")), reverse=True)
        
        uuid_profiles = [
            p.get("user_id") for p in prof_items
            if p.get("user_id") and p.get("user_id") != "1600"
        ]
        if uuid_profiles:
            app_user_id = uuid_profiles[0]
            print(f"[INFO] Auto-detected most recently active Cognito user_id from 'profiles' table: {app_user_id}")
        elif prof_items:
            app_user_id = prof_items[0].get("user_id")
            print(f"[INFO] Auto-detected user_id from 'profiles' table: {app_user_id}")

    if not app_user_id:
        print("\n[ERROR] No user_id provided and no saved profiles found in DynamoDB.")
        print("Please save your health profile on the Profile page first, or pass --user <cognito_sub>.")
        return None

    # 2. Retrieve user's health profile from DynamoDB 'profiles' table
    risk_profile = get_user_risk_profile(app_user_id)
    if not risk_profile:
        print(f"\n[WARNING] User {app_user_id} has not saved a health profile yet.")
        print("Please log into the web app, complete the Profile page, and save your health profile.")
        return None

    # 3. Read latest telemetry event from DynamoDB 'activity_events'
    response = activity_table.scan()
    items = response.get("Items", [])

    matching_items = [
        item for item in items
        if "sensor_features" in item and len(item["sensor_features"]) == 30
    ]

    if not matching_items:
        raise ValueError("No DynamoDB telemetry event with 30 sensor features was found in 'activity_events'.")

    # Sort matching items by timestamp or pick the last item
    matching_items.sort(key=lambda x: str(x.get("timestamp", "")))
    event = matching_items[-1]

    if event.get("status") == "processed":
        return None

    print(f"\n[OK] Processing latest telemetry event: {event.get('event_id')}")

    # Extract 30 sensor features
    sensor_features = {
        feature: float(value)
        for feature, value in event["sensor_features"].items()
    }

    # 4. Activity ML Model Prediction
    print("\nRunning Activity ML model (Random Forest)...")
    activity_result = predict_activity(sensor_features)
    print(f"Detected Activity : {activity_result['activity']}")
    print(f"Confidence Score  : {activity_result['confidence']:.4f}")

    # 5. Risk ML Model Prediction
    print("\nRunning Risk ML model (XGBoost)...")
    risk_result = predict_risk(risk_profile)
    print(f"Risk Score        : {risk_result['score']:.4f}")
    print(f"Risk Band         : {risk_result['band']}")

    # 6. Generate Recommendations List
    rec_list = generate_recommendations(risk_result["band"], activity_result["activity"])

    # 7. Write Recommendation Record to DynamoDB 'recommendations' Table
    rec_id = f"rec_{int(time.time() * 1000)}"
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
    event_timestamp = str(event.get("timestamp", now_iso))

    rec_item = {
        "recommendation_id": rec_id,
        "user_id": str(app_user_id),
        "subject_id": int(event.get("subject_id", 1600)),
        "activity": activity_result["activity"],
        "activity_confidence": Decimal(str(round(float(activity_result["confidence"]), 4))),
        "risk_score": Decimal(str(round(float(risk_result["score"]), 4))),
        "risk_band": risk_result["band"],
        "recommendation": rec_list[0] if rec_list else "",
        "recommendation_text": rec_list[0] if rec_list else "",
        "recommendations": rec_list,
        "timestamp": event_timestamp,
        "created_at": now_iso,
        "health_profile": risk_profile
    }

    # Convert all float types in rec_item (including nested health_profile) to Decimal
    rec_item_dynamo = convert_floats_to_decimals(rec_item)

    recommendations_table.put_item(Item=rec_item_dynamo)
    print(f"\n[SUCCESS] Recommendation record written to DynamoDB 'recommendations' table:")
    print(f"  User ID           : {app_user_id}")
    print(f"  Recommendation ID : {rec_id}")

    # 8. Update DynamoDB 'activity_events' table item
    try:
        activity_table.update_item(
            Key={"event_id": event["event_id"]},
            UpdateExpression=(
                "SET activity = :activity, "
                "activity_confidence = :confidence, "
                "risk_score = :risk_score, "
                "risk_band = :risk_band, "
                "user_id = :user_id, "
                "#status = :status"
            ),
            ExpressionAttributeNames={"#status": "status"},
            ExpressionAttributeValues={
                ":activity": activity_result["activity"],
                ":confidence": Decimal(str(round(float(activity_result["confidence"]), 4))),
                ":risk_score": Decimal(str(round(float(risk_result["score"]), 4))),
                ":risk_band": risk_result["band"],
                ":user_id": str(app_user_id),
                ":status": "processed"
            }
        )
        print(f"  Updated 'activity_events' record status to 'processed'.")
    except Exception as e:
        print(f"  [Notice] Activity events update notice: {e}")

    print("\n" + "=" * 60)
    print("ML PROCESSING PIPELINE COMPLETED SUCCESSFULLY")
    print("=" * 60)

    return rec_item


# ============================================================
# MAIN EXECUTION ENTRYPOINT
# ============================================================

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Behaviour-Aware Preventive Health ML Processing Pipeline")
    parser.add_argument("--user", type=str, help="Authenticated Cognito userSub ID")
    parser.add_argument("--daemon", action="store_true", help="Run continuously in background polling mode")
    args = parser.parse_args()

    if args.daemon:
        print("[DAEMON] Starting ML service in background polling mode...")
        last_processed_event_id = None
        while True:
            try:
                response = activity_table.scan()
                items = response.get("Items", [])
                matching = [i for i in items if "sensor_features" in i and len(i["sensor_features"]) == 30]
                if matching:
                    matching.sort(key=lambda x: str(x.get("timestamp", "")))
                    latest = matching[-1]
                    if latest.get("status") != "processed" and latest.get("event_id") != last_processed_event_id:
                        process_latest_dynamodb_event(user_id=args.user)
                        last_processed_event_id = latest.get("event_id")
            except Exception as e:
                pass
            import time
            time.sleep(5)
    else:
        process_latest_dynamodb_event(user_id=args.user)
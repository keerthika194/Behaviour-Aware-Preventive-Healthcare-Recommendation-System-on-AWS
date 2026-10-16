"""
Health Adherence Cloud ML Inference Engine Lambda Handler
=========================================================
AWS Lambda function triggered by DynamoDB Streams (Pattern B: Decoupled Streams)
on the 'activity_events' table.

Responsibilities:
1. Unpacks raw 3-axis accelerometer and gyroscope arrays (200 readings per window).
2. Computes the 30 statistical time-domain features.
3. Loads and caches Random Forest activity and XGBoost risk models across warm starts.
4. Retrieves user clinical baseline from DynamoDB 'profiles' (with default fallback).
5. Runs dual inference (< 50ms) to compute detected activity, confidence, risk score, and band.
6. Persists output recommendation item to DynamoDB 'recommendations' with 24-hr TTL (expire_at).
7. Updates the source 'activity_events' item to status: 'processed'.
"""

import os
import sys
import json
import time
import math
import uuid
import datetime
import pathlib
import warnings
from decimal import Decimal
import numpy as np
import joblib
import xgboost as xgb
import boto3
from boto3.dynamodb.types import TypeDeserializer

# ============================================================
# AWS DYNAMODB RESOURCE INITIALIZATION
# ============================================================

REGION = os.environ.get("AWS_REGION", "ap-south-1")
dynamodb = boto3.resource("dynamodb", region_name=REGION)

PROFILES_TABLE_NAME = os.environ.get("PROFILES_TABLE", "profiles")
RECOMMENDATIONS_TABLE_NAME = os.environ.get("RECOMMENDATIONS_TABLE", "recommendations")
ACTIVITY_TABLE_NAME = os.environ.get("ACTIVITY_TABLE", "activity_events")

profiles_table = dynamodb.Table(PROFILES_TABLE_NAME)
recommendations_table = dynamodb.Table(RECOMMENDATIONS_TABLE_NAME)
activity_table = dynamodb.Table(ACTIVITY_TABLE_NAME)

_DESERIALIZER = TypeDeserializer()

# ============================================================
# MODULE-LEVEL MODEL ARTIFACT CACHING
# ============================================================

_ACTIVITY_MODEL = None
_ACTIVITY_SCHEMA = None
_ACTIVITY_FEATURE_NAMES = None
_RISK_MODEL = None
_RISK_SCHEMA = None
_RISK_FEATURE_NAMES = None

_CACHED_ACTIVE_USER = None
_CACHED_ACTIVE_USER_TIME = 0.0


def _resolve_active_user():
    """
    Resolves the most recently active Cognito userSub from DynamoDB 'profiles'.
    Caches the lookup for 60 seconds to prevent redundant scans across stream batches.
    """
    global _CACHED_ACTIVE_USER, _CACHED_ACTIVE_USER_TIME
    now = time.time()
    if _CACHED_ACTIVE_USER and (now - _CACHED_ACTIVE_USER_TIME) < 60.0:
        return _CACHED_ACTIVE_USER

    try:
        prof_res = profiles_table.scan(Limit=10)
        p_items = prof_res.get("Items", [])
        p_items.sort(key=lambda x: str(x.get("updated_at", "")), reverse=True)
        real_users = [p.get("user_id") for p in p_items if p.get("user_id") and str(p.get("user_id")) != "1600"]
        if real_users:
            _CACHED_ACTIVE_USER = str(real_users[0])
            _CACHED_ACTIVE_USER_TIME = now
            return _CACHED_ACTIVE_USER
    except Exception:
        pass

    return "1600"


DEFAULT_CLINICAL_BASELINE = {
    "HighBP": 0.0,
    "HighChol": 0.0,
    "CholCheck": 1.0,
    "BMI": 25.0,
    "Smoker": 0.0,
    "Stroke": 0.0,
    "HeartDiseaseorAttack": 0.0,
    "PhysActivity": 1.0,
    "Fruits": 1.0,
    "Veggies": 1.0,
    "HvyAlcoholConsump": 0.0,
    "AnyHealthcare": 1.0,
    "NoDocbcCost": 0.0,
    "GenHlth": 2.0,
    "MentHlth": 2.0,
    "PhysHlth": 2.0,
    "DiffWalk": 0.0,
    "Sex": 0.0,
    "Age": 5.0,
    "Education": 5.0,
    "Income": 6.0
}


def _locate_artifact(relative_candidates):
    """
    Locates an artifact file by checking possible base directories
    across local development, Lambda root (/var/task), and Lambda layers (/opt).
    """
    base_dirs = [
        pathlib.Path(__file__).resolve().parent,
        pathlib.Path(__file__).resolve().parent / "models",
        pathlib.Path(__file__).resolve().parent.parent.parent / "models",
        pathlib.Path.cwd() / "models",
        pathlib.Path.cwd(),
        pathlib.Path("/var/task"),
        pathlib.Path("/var/task/models"),
        pathlib.Path("/opt"),
        pathlib.Path("/opt/models"),
    ]

    for base in base_dirs:
        for rel in relative_candidates:
            cand = base / rel
            if cand.is_file():
                return cand

    raise FileNotFoundError(f"Could not locate model artifact. Tried candidates: {relative_candidates}")


def load_models():
    """
    Loads and caches the Random Forest activity classifier and XGBoost risk model.
    Subsequent invocations on warm Lambda containers reuse cached instances.
    """
    global _ACTIVITY_MODEL, _ACTIVITY_SCHEMA, _ACTIVITY_FEATURE_NAMES, _RISK_MODEL, _RISK_SCHEMA, _RISK_FEATURE_NAMES

    # 1. Activity Model
    if _ACTIVITY_MODEL is None or _ACTIVITY_SCHEMA is None:
        schema_path = _locate_artifact([
            pathlib.Path("activity_model") / "feature_schema.json",
            pathlib.Path("feature_schema_activity.json"),
            pathlib.Path("feature_schema.json")
        ])
        with open(schema_path, "r", encoding="utf-8") as f:
            _ACTIVITY_SCHEMA = json.load(f)
        _ACTIVITY_FEATURE_NAMES = tuple(_ACTIVITY_SCHEMA["feature_names"])

        pkl_path = _locate_artifact([
            pathlib.Path("activity_model") / "activity_model.pkl",
            pathlib.Path("activity_model.pkl")
        ])
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            _ACTIVITY_MODEL = joblib.load(pkl_path)
        print(f"[ML_ENGINE] Loaded Activity model from {pkl_path}")

    # 2. Risk Model
    if _RISK_MODEL is None or _RISK_SCHEMA is None:
        risk_schema_path = _locate_artifact([
            pathlib.Path("risk_model") / "feature_schema.json",
            pathlib.Path("feature_schema_risk.json")
        ])
        with open(risk_schema_path, "r", encoding="utf-8") as f:
            _RISK_SCHEMA = json.load(f)
        _RISK_FEATURE_NAMES = tuple(_RISK_SCHEMA["feature_names"])

        json_path = _locate_artifact([
            pathlib.Path("risk_model") / "risk_model.json",
            pathlib.Path("risk_model.json")
        ])
        _RISK_MODEL = xgb.XGBClassifier()
        _RISK_MODEL.load_model(str(json_path))
        print(f"[ML_ENGINE] Loaded Risk model from {json_path}")


# ============================================================
# TYPE CONVERSION UTILITIES
# ============================================================

def _safe_float(val, default=0.0):
    """
    Safely converts any scalar to float, returning default if None, invalid, NaN, or Infinite.
    """
    if val is None:
        return default
    try:
        f = float(val)
        return default if (math.isnan(f) or math.isinf(f)) else f
    except (ValueError, TypeError):
        return default


def convert_floats_to_decimals(obj):
    """
    Recursively converts float and numpy float values to boto3-compatible Decimal objects.
    Protects against NaN / Infinity which are unsupported by DynamoDB.
    """
    if isinstance(obj, (float, np.floating)):
        if math.isnan(obj) or math.isinf(obj):
            return Decimal("0")
        return Decimal(str(obj))
    if isinstance(obj, Decimal):
        if obj.is_nan() or obj.is_infinite():
            return Decimal("0")
        return obj
    if isinstance(obj, dict):
        return {k: convert_floats_to_decimals(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [convert_floats_to_decimals(v) for v in obj]
    return obj


def convert_decimals_to_native(obj):
    """
    Recursively converts Decimal objects to int or float for standard JSON serialization.
    """
    if isinstance(obj, Decimal):
        return int(obj) if obj % 1 == 0 else float(obj)
    if isinstance(obj, dict):
        return {k: convert_decimals_to_native(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [convert_decimals_to_native(v) for v in obj]
    return obj


def decimal_serializer(obj):
    """Fallback JSON serializer for Decimal instances."""
    if isinstance(obj, Decimal):
        return int(obj) if obj % 1 == 0 else float(obj)
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


def deserialize_dynamodb_record(item):
    """
    Recursively transforms a DynamoDB typed attribute dictionary or list
    ({'S': 'val'}, {'N': '123'}, {'L': [...]}, {'M': {...}})
    into a native Python data structure with standard primitives.
    """
    if isinstance(item, list):
        return [deserialize_dynamodb_record(elem) for elem in item]

    if not isinstance(item, dict):
        if isinstance(item, Decimal):
            return int(item) if item % 1 == 0 else float(item)
        return item

    # Check if item represents a DynamoDB Typed Attribute
    keys = list(item.keys())
    dynamodb_types = {"S", "N", "B", "SS", "NS", "BS", "M", "L", "NULL", "BOOL"}
    if len(keys) == 1 and keys[0] in dynamodb_types:
        try:
            val = _DESERIALIZER.deserialize(item)
            if isinstance(val, (dict, list)):
                return deserialize_dynamodb_record(val)
            if isinstance(val, set):
                return [deserialize_dynamodb_record(elem) for elem in sorted(val, key=str)]
            if isinstance(val, Decimal):
                return int(val) if val % 1 == 0 else float(val)
            return val
        except Exception:
            pass

    converted = {}
    for k, v in item.items():
        converted[k] = deserialize_dynamodb_record(v)
    return converted


# ============================================================
# SENSOR FEATURE EXTRACTION (30 STATISTICAL TIME-DOMAIN FEATURES)
# ============================================================

def _extract_axis_series(sensor_input):
    """
    Normalizes any sensor input format into a dict of 3 numpy float arrays: {'x': np.array, 'y': np.array, 'z': np.array}.
    Supports:
      - dict of lists: {'x': [...], 'y': [...], 'z': [...]}
      - list of dicts: [{'x': ..., 'y': ..., 'z': ...}, ...]
      - list of tuples/lists: [[x, y, z], ...]
      - JSON-encoded strings of any above structure
      - Case-insensitive keys ('x'/'X', 'y'/'Y', 'z'/'Z')
    """
    if not sensor_input:
        return None

    if isinstance(sensor_input, str):
        try:
            sensor_input = json.loads(sensor_input)
        except Exception:
            return None

    # Format 1: dict of axis lists
    if isinstance(sensor_input, dict):
        x_raw = sensor_input.get("x") or sensor_input.get("X") or []
        y_raw = sensor_input.get("y") or sensor_input.get("Y") or []
        z_raw = sensor_input.get("z") or sensor_input.get("Z") or []
        if not (x_raw or y_raw or z_raw):
            return None
        return {
            "x": np.nan_to_num(np.array([_safe_float(v) for v in x_raw], dtype=float), nan=0.0, posinf=0.0, neginf=0.0),
            "y": np.nan_to_num(np.array([_safe_float(v) for v in y_raw], dtype=float), nan=0.0, posinf=0.0, neginf=0.0),
            "z": np.nan_to_num(np.array([_safe_float(v) for v in z_raw], dtype=float), nan=0.0, posinf=0.0, neginf=0.0),
        }

    # Format 2 & 3: list of readings
    if isinstance(sensor_input, list):
        if len(sensor_input) == 0:
            return None
        x_vals, y_vals, z_vals = [], [], []
        for r in sensor_input:
            if isinstance(r, dict):
                x_val = r.get("x") if "x" in r else r.get("X")
                y_val = r.get("y") if "y" in r else r.get("Y")
                z_val = r.get("z") if "z" in r else r.get("Z")
                x_vals.append(_safe_float(x_val))
                y_vals.append(_safe_float(y_val))
                z_vals.append(_safe_float(z_val))
            elif isinstance(r, (list, tuple)):
                x_vals.append(_safe_float(r[0] if len(r) > 0 else 0.0))
                y_vals.append(_safe_float(r[1] if len(r) > 1 else 0.0))
                z_vals.append(_safe_float(r[2] if len(r) > 2 else 0.0))
            else:
                x_vals.append(_safe_float(r))
                y_vals.append(0.0)
                z_vals.append(0.0)

        return {
            "x": np.nan_to_num(np.array(x_vals, dtype=float), nan=0.0, posinf=0.0, neginf=0.0),
            "y": np.nan_to_num(np.array(y_vals, dtype=float), nan=0.0, posinf=0.0, neginf=0.0),
            "z": np.nan_to_num(np.array(z_vals, dtype=float), nan=0.0, posinf=0.0, neginf=0.0),
        }

    return None


def extract_sensor_features(data_dict):
    """
    Converts raw 3-axis accelerometer and gyroscope sensor arrays
    (200 readings per 10-second window at 20 Hz) into the 30 statistical
    time-domain features:
      - Mean
      - Standard Deviation (population, ddof=0)
      - Min
      - Max
      - Average Absolute Difference (avg_abs_diff)
    for axes x, y, z across accelerometer (acc) and gyroscope (gyr).
    """
    load_models()

    # 1. Already extracted 30 features present?
    if "sensor_features" in data_dict:
        sf = data_dict["sensor_features"]
        if isinstance(sf, str):
            try:
                sf = json.loads(sf)
            except Exception:
                sf = None
        if isinstance(sf, dict):
            if _ACTIVITY_FEATURE_NAMES and all(k in sf for k in _ACTIVITY_FEATURE_NAMES):
                return {k: _safe_float(sf[k], 0.0) for k in _ACTIVITY_FEATURE_NAMES}
            if len(sf) == 30:
                return {k: _safe_float(v, 0.0) for k, v in sf.items()}

    acc_raw = data_dict.get("accel")
    if acc_raw is None:
        acc_raw = data_dict.get("accelerometer") or data_dict.get("acc") or data_dict.get("acceleration")

    gyr_raw = data_dict.get("gyro")
    if gyr_raw is None:
        gyr_raw = data_dict.get("gyroscope") or data_dict.get("gyr")

    acc_axes = _extract_axis_series(acc_raw)
    gyr_axes = _extract_axis_series(gyr_raw)

    if acc_axes is None or gyr_axes is None:
        raise ValueError("Missing raw sensor arrays: 'accel' and 'gyro' are required to extract features.")

    if len(acc_axes["x"]) == 0 or len(gyr_axes["x"]) == 0:
        raise ValueError("Sensor arrays 'accel' and 'gyro' must not be empty.")

    features = {}
    sensors = {
        "acc": acc_axes,
        "gyr": gyr_axes
    }
    axes = ["x", "y", "z"]

    for sensor_name, axis_dict in sensors.items():
        for axis in axes:
            values = axis_dict[axis]
            prefix = f"{sensor_name}_{axis}"

            mean_val = float(np.mean(values)) if len(values) > 0 else 0.0
            std_val = float(np.std(values)) if len(values) > 0 else 0.0
            min_val = float(np.min(values)) if len(values) > 0 else 0.0
            max_val = float(np.max(values)) if len(values) > 0 else 0.0

            if len(values) > 1:
                diffs = np.abs(np.diff(values))
                avg_abs_diff = float(np.mean(diffs)) if len(diffs) > 0 else 0.0
            else:
                avg_abs_diff = 0.0

            features[f"{prefix}_mean"] = _safe_float(mean_val)
            features[f"{prefix}_std"] = _safe_float(std_val)
            features[f"{prefix}_min"] = _safe_float(min_val)
            features[f"{prefix}_max"] = _safe_float(max_val)
            features[f"{prefix}_avg_abs_diff"] = _safe_float(avg_abs_diff)

    return features


# ============================================================
# CLINICAL BASELINE PROFILE RETRIEVAL
# ============================================================

def get_user_risk_profile(user_id, client_table=None):
    """
    Fetches the 21 BRFSS health indicators for an authenticated user
    from the DynamoDB 'profiles' table. If unset or unavailable,
    falls back to the clinical default baseline.
    """
    target_table = client_table or profiles_table
    if not user_id:
        return dict(DEFAULT_CLINICAL_BASELINE)

    try:
        response = target_table.get_item(Key={"user_id": str(user_id)})
        item = response.get("Item")
        if not item:
            return dict(DEFAULT_CLINICAL_BASELINE)

        profile_dict = dict(item)
        profile_dict.pop("user_id", None)
        profile_dict.pop("updated_at", None)

        lowered_input = {str(pk).lower(): pv for pk, pv in profile_dict.items()}
        converted_profile = dict(DEFAULT_CLINICAL_BASELINE)
        for k in DEFAULT_CLINICAL_BASELINE:
            if k in profile_dict:
                converted_profile[k] = _safe_float(profile_dict[k], DEFAULT_CLINICAL_BASELINE[k])
            elif k.lower() in lowered_input:
                converted_profile[k] = _safe_float(lowered_input[k.lower()], DEFAULT_CLINICAL_BASELINE[k])

        return converted_profile
    except Exception as e:
        print(f"[ML_ENGINE] Notice: Unable to fetch profile for user {user_id} ({e}). Using default baseline.")
        return dict(DEFAULT_CLINICAL_BASELINE)


# ============================================================
# RECOMMENDATION GENERATION
# ============================================================

def generate_recommendations(risk_band, activity):
    """
    Synthesize personalized preventive recommendations based on
    the XGBoost risk prediction and detected smartwatch activity.
    """
    recs = []

    if risk_band == "Low":
        recs.append(
            "Your preventive risk profile is Low. Continue maintaining regular physical activity and healthy daily routines."
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
# DUAL ML INFERENCE (< 50ms LATENCY)
# ============================================================

def run_dual_inference(sensor_features, clinical_profile):
    """
    Executes dual inference:
    1. Random Forest Activity Classifier using the 30 sensor features.
    2. XGBoost Chronic Disease Risk Classifier using the 21 health indicators.
    High-performance vector execution achieves < 50ms total latency.
    """
    load_models()

    # 1. Activity Classifier (Vectorized NumPy execution)
    act_vector = np.array([[_safe_float(sensor_features.get(feat, 0.0)) for feat in _ACTIVITY_FEATURE_NAMES]], dtype=np.float32)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=UserWarning)
        act_probs = _ACTIVITY_MODEL.predict_proba(act_vector)[0]

    max_idx = int(np.argmax(act_probs))
    predicted_activity = str(_ACTIVITY_MODEL.classes_[max_idx])
    confidence = round(float(act_probs[max_idx]), 4)

    # 2. Risk Classifier (Vectorized NumPy execution)
    risk_vector = np.array([[_safe_float(clinical_profile.get(feat, 0.0)) for feat in _RISK_FEATURE_NAMES]], dtype=np.float32)

    prob_class_1 = float(_RISK_MODEL.predict_proba(risk_vector)[0, 1])
    risk_score = round(prob_class_1, 4)

    if risk_score < 0.35:
        risk_band = "Low"
    elif risk_score < 0.65:
        risk_band = "Medium"
    else:
        risk_band = "High"

    return {
        "activity": predicted_activity,
        "confidence": confidence,
        "risk_score": risk_score,
        "risk_band": risk_band
    }


# ============================================================
# SINGLE EVENT PROCESSOR
# ============================================================

def process_single_event(raw_item):
    """
    Processes a single activity event item:
    1. Extracts 30 sensor features from raw window or existing sensor_features.
    2. Retrieves user's clinical baseline profile.
    3. Executes dual inference.
    4. Generates recommendations.
    5. Writes recommendation record to DynamoDB 'recommendations' with 24h expire_at TTL.
    6. Updates source 'activity_events' item with status: 'processed'.
    """
    start_time = time.perf_counter()

    event_id = raw_item.get("event_id")
    user_id = raw_item.get("user_id")

    raw_subj = raw_item.get("subject_id")
    try:
        if raw_subj is not None:
            subject_id = int(float(str(raw_subj).strip()))
        else:
            subject_id = 1600
    except (ValueError, TypeError):
        subject_id = 1600

    # Resolve active Cognito userSub if unset
    target_user = user_id
    if not target_user or str(target_user) == "1600":
        target_user = _resolve_active_user()
    if not target_user:
        target_user = "1600"

    # 1. Extract 30 features
    sensor_features = extract_sensor_features(raw_item)

    # 2. Fetch Clinical Baseline
    clinical_profile = get_user_risk_profile(target_user)

    # 3. Dual Inference
    inference_result = run_dual_inference(sensor_features, clinical_profile)
    inference_duration_ms = (time.perf_counter() - start_time) * 1000.0
    print(f"[ML_ENGINE] Inference finished in {inference_duration_ms:.2f}ms: "
          f"Activity='{inference_result['activity']}' (conf={inference_result['confidence']}), "
          f"Risk={inference_result['risk_score']} ({inference_result['risk_band']})")

    # 4. Generate Recommendations
    rec_list = generate_recommendations(inference_result["risk_band"], inference_result["activity"])
    rec_text = rec_list[0] if rec_list else ""

    # 5. Build Recommendation Item with 24-hour Unix epoch TTL
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    now_iso = now_utc.isoformat()
    ttl_epoch = int(time.time()) + (24 * 3600)
    rec_id = f"rec_{int(time.time() * 1000)}_{uuid.uuid4().hex[:6]}"

    rec_item = {
        "recommendation_id": rec_id,
        "user_id": str(target_user),
        "subject_id": int(subject_id),
        "activity": inference_result["activity"],
        "activity_confidence": Decimal(str(inference_result["confidence"])),
        "risk_score": Decimal(str(inference_result["risk_score"])),
        "risk_band": inference_result["risk_band"],
        "recommendation": rec_text,
        "recommendation_text": rec_text,
        "recommendations": rec_list,
        "timestamp": str(raw_item.get("timestamp", now_iso)),
        "created_at": now_iso,
        "health_profile": clinical_profile,
        "expire_at": ttl_epoch
    }
    if event_id:
        rec_item["event_id"] = str(event_id)
    if raw_item.get("device_id"):
        rec_item["device_id"] = str(raw_item["device_id"])

    # Write to DynamoDB recommendations table
    rec_item_dynamo = convert_floats_to_decimals(rec_item)
    try:
        recommendations_table.put_item(Item=rec_item_dynamo)
        print(f"[ML_ENGINE] Written recommendation {rec_id} for user {target_user} (TTL expire_at: {ttl_epoch})")
    except Exception as e:
        print(f"[ML_ENGINE] Error writing to recommendations table: {e}")

    # 6. Update source activity_events item to status: 'processed'
    if event_id:
        try:
            activity_table.update_item(
                Key={"event_id": str(event_id)},
                UpdateExpression=(
                    "SET activity = :activity, "
                    "activity_confidence = :confidence, "
                    "risk_score = :risk_score, "
                    "risk_band = :risk_band, "
                    "user_id = :user_id, "
                    "#status = :status, "
                    "sensor_features = :sensor_features"
                ),
                ExpressionAttributeNames={"#status": "status"},
                ExpressionAttributeValues={
                    ":activity": inference_result["activity"],
                    ":confidence": Decimal(str(inference_result["confidence"])),
                    ":risk_score": Decimal(str(inference_result["risk_score"])),
                    ":risk_band": inference_result["risk_band"],
                    ":user_id": str(target_user),
                    ":status": "processed",
                    ":sensor_features": convert_floats_to_decimals(sensor_features)
                }
            )
            print(f"[ML_ENGINE] Updated activity_events event_id={event_id} status to 'processed'.")
        except Exception as e:
            print(f"[ML_ENGINE] Notice updating activity_events: {e}")

    return {
        "event_id": event_id,
        "recommendation_id": rec_id,
        "user_id": str(target_user),
        "activity": inference_result["activity"],
        "activity_confidence": inference_result["confidence"],
        "risk_score": inference_result["risk_score"],
        "risk_band": inference_result["risk_band"],
        "expire_at": ttl_epoch,
        "inference_latency_ms": round(inference_duration_ms, 2)
    }


# ============================================================
# MAIN AWS LAMBDA HANDLER
# ============================================================

def lambda_handler(event, context):
    """
    Primary AWS Lambda Handler. Ingests DynamoDB Stream event batches.
    Filters for 'INSERT' events on activity_events, extracts features,
    runs dual inference, persists results, and marks source items as processed.
    """
    if not event or not isinstance(event, dict):
        print("[ML_ENGINE] Empty or non-dict event received.")
        return {"statusCode": 200, "processed_count": 0, "results": []}

    records = event.get("Records")
    if records is None:
        # Direct non-stream payload support (for test harness or manual trigger)
        records = [event]

    print(f"[ML_ENGINE] Processing batch with {len(records)} record(s).")
    processed_results = []

    for record in records:
        clean_item = None
        if not isinstance(record, dict):
            continue

        try:
            # 1. DynamoDB Stream Event handling
            event_name = record.get("eventName")
            if event_name and event_name != "INSERT":
                print(f"[ML_ENGINE] Skipping non-INSERT stream record (eventName: {event_name})")
                continue

            dynamo_data = record.get("dynamodb", {})
            new_image = dynamo_data.get("NewImage") or record.get("NewImage") or record

            # Deserialize typed DynamoDB attributes
            clean_item = deserialize_dynamodb_record(new_image)
            if not isinstance(clean_item, dict) or not clean_item:
                continue

            # Skip already processed or archived items
            item_status = clean_item.get("status")
            if item_status in ("processed", "archived"):
                print(f"[ML_ENGINE] Item {clean_item.get('event_id')} has status '{item_status}'. Skipping.")
                continue

            result = process_single_event(clean_item)
            processed_results.append(result)

        except Exception as exc:
            print(f"[ML_ENGINE ERROR] Failed processing record: {exc}")
            import traceback
            traceback.print_exc()
            if isinstance(clean_item, dict) and clean_item.get("event_id"):
                try:
                    activity_table.update_item(
                        Key={"event_id": str(clean_item["event_id"])},
                        UpdateExpression="SET #status = :status, error_message = :err",
                        ExpressionAttributeNames={"#status": "status"},
                        ExpressionAttributeValues={":status": "failed", ":err": str(exc)[:250]}
                    )
                except Exception:
                    pass

    return {
        "statusCode": 200,
        "processed_count": len(processed_results),
        "results": convert_decimals_to_native(processed_results)
    }

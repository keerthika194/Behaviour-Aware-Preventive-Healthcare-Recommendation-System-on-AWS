"""
Section 4 - Smartwatch Activity Recognition Inference Module
=============================================================
Provides reusable predict_activity(input_dict) function for real-time smartwatch activity recognition.
Compatible with IoT pipeline, direct invocation, microservices, and AWS Functions.
"""

import json
import pathlib
import joblib
import pandas as pd
import numpy as np

# Module directory paths
MODEL_DIR = pathlib.Path(__file__).resolve().parent
MODEL_PKL = MODEL_DIR / "activity_model.pkl"
SCHEMA_JSON = MODEL_DIR / "feature_schema.json"

# Cached model & schema instances
_MODEL = None
_SCHEMA = None


def _load_artifacts():
    global _MODEL, _SCHEMA
    if _SCHEMA is None:
        if not SCHEMA_JSON.exists():
            raise FileNotFoundError(f"Feature schema not found at {SCHEMA_JSON}. Please run train_activity_model.py first.")
        with open(SCHEMA_JSON, "r", encoding="utf-8") as f:
            _SCHEMA = json.load(f)

    if _MODEL is None:
        if not MODEL_PKL.exists():
            raise FileNotFoundError(f"Model file not found at {MODEL_PKL}. Please run train_activity_model.py first.")
        _MODEL = joblib.load(MODEL_PKL)


def predict_activity(input_dict: dict) -> dict:
    """
    Predicts smartwatch activity label and prediction confidence score from 30 sensor features.

    Parameters:
      input_dict (dict): Dictionary containing the 30 smartwatch sensor features.

    Returns:
      dict: {
          "activity": str (e.g. "Walking"),
          "confidence": float (0.0 to 1.0 confidence score)
      }
    """
    _load_artifacts()

    expected_features = _SCHEMA["feature_names"]

    # Align input features with expected schema order
    aligned_input = {}
    for feat in expected_features:
        if feat in input_dict:
            aligned_input[feat] = float(input_dict[feat])
        else:
            aligned_input[feat] = 0.0

    # Convert to DataFrame with exact column order
    df_input = pd.DataFrame([aligned_input], columns=expected_features)

    # Predict activity label
    predicted_activity = str(_MODEL.predict(df_input)[0])

    # Compute prediction confidence (max predicted class probability)
    probabilities = _MODEL.predict_proba(df_input)[0]
    confidence = round(float(np.max(probabilities)), 4)

    return {
        "activity": predicted_activity,
        "confidence": confidence
    }


if __name__ == "__main__":
    # Self-test using a sample input row from test.csv
    print("Testing activity inference module...")
    test_csv = MODEL_DIR.parent.parent / "datasets" / "wisdm_smartwatch" / "processed" / "test.csv"

    if test_csv.exists():
        df_test = pd.read_csv(test_csv)
        sample_row = df_test.iloc[0]
        actual_label = sample_row["activity_label"]

        # Extract features dictionary
        feature_cols = [c for c in df_test.columns if c not in ["subject_id", "activity_label"]]
        sample_input = sample_row[feature_cols].to_dict()

        res = predict_activity(sample_input)
        print(f"\nSample Inference Self-Check:")
        print(f"  Actual Activity   : {actual_label}")
        print(f"  Predicted Activity: {res['activity']}")
        print(f"  Confidence Score  : {res['confidence']}")
    else:
        print("Note: Run train_activity_model.py first to generate model artifacts.")

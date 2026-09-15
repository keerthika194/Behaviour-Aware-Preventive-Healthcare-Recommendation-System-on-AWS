"""
Section 3 - Risk Prediction Inference Module
=============================================
Provides reusable predict_risk(input_dict) function for preventive diabetes/chronic risk assessment.
Compatible with direct invocation, microservices, and AWS Functions.
"""

import json
import pathlib
import pandas as pd
import xgboost as xgb

# Module directory paths
MODEL_DIR = pathlib.Path(__file__).resolve().parent
MODEL_JSON = MODEL_DIR / "risk_model.json"
SCHEMA_JSON = MODEL_DIR / "feature_schema.json"

# Cached model & schema instances
_MODEL = None
_SCHEMA = None


def _load_artifacts():
    global _MODEL, _SCHEMA
    if _SCHEMA is None:
        if not SCHEMA_JSON.exists():
            raise FileNotFoundError(f"Feature schema not found at {SCHEMA_JSON}. Please run train_risk_model.py first.")
        with open(SCHEMA_JSON, "r", encoding="utf-8") as f:
            _SCHEMA = json.load(f)

    if _MODEL is None:
        if not MODEL_JSON.exists():
            raise FileNotFoundError(f"Model file not found at {MODEL_JSON}. Please run train_risk_model.py first.")
        _MODEL = xgb.XGBClassifier()
        _MODEL.load_model(str(MODEL_JSON))


def predict_risk(input_dict: dict) -> dict:
    """
    Predicts diabetes/chronic disease risk probability and risk band from user health/lifestyle inputs.

    Risk Band Threshold Rationale:
      - Low Risk    (score < 0.35): Low probability of binary outcome. Standard preventive advice.
      - Medium Risk (0.35 <= score < 0.65): Moderate risk. Behavioral modifications recommended.
      - High Risk   (score >= 0.65): High probability. Priority clinical evaluation suggested.

    Parameters:
      input_dict (dict): Feature dictionary containing the 21 health/lifestyle indicators.

    Returns:
      dict: {
          "score": float (0.0 to 1.0 probability),
          "band": str ("Low" | "Medium" | "High"),
          "thresholds": dict,
          "missing_features_defaulted": list
      }
    """
    _load_artifacts()

    expected_features = _SCHEMA["feature_names"]

    # Align features and handle any missing keys with default 0.0
    aligned_input = {}
    missing_keys = []
    for feat in expected_features:
        if feat in input_dict:
            aligned_input[feat] = float(input_dict[feat])
        else:
            missing_keys.append(feat)
            aligned_input[feat] = 0.0

    # Convert to DataFrame with exact column order
    df_input = pd.DataFrame([aligned_input], columns=expected_features)

    # Predict probability of class 1 (Diabetes/Prediabetes)
    prob_class_1 = float(_MODEL.predict_proba(df_input)[0, 1])
    score = round(prob_class_1, 4)

    # Determine Risk Band
    if score < 0.35:
        band = "Low"
    elif score < 0.65:
        band = "Medium"
    else:
        band = "High"

    return {
        "score": score,
        "band": band,
        "thresholds": {
            "low": "< 0.35",
            "medium": "0.35 - 0.65",
            "high": ">= 0.65"
        },
        "missing_features_defaulted": missing_keys
    }


if __name__ == "__main__":
    # Test script self-check
    print("Testing inference module...")
    sample_input = {
        "HighBP": 1,
        "HighChol": 1,
        "CholCheck": 1,
        "BMI": 32.0,
        "Smoker": 1,
        "Stroke": 0,
        "HeartDiseaseorAttack": 1,
        "PhysActivity": 0,
        "Fruits": 0,
        "Veggies": 1,
        "HvyAlcoholConsump": 0,
        "AnyHealthcare": 1,
        "NoDocbcCost": 0,
        "GenHlth": 4,
        "MentHlth": 10,
        "PhysHlth": 15,
        "DiffWalk": 1,
        "Sex": 1,
        "Age": 9,
        "Education": 4,
        "Income": 5
    }
    result = predict_risk(sample_input)
    print("Sample Inference Result:\n", json.dumps(result, indent=2))

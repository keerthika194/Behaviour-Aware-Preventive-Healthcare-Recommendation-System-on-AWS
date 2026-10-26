"""
Section 4 - Model 2: Smartwatch Activity Recognition (Random Forest)
====================================================================
Trains a Random Forest classifier on preprocessed WISDM smartwatch sensor data
to recognize 18 activity classes from 30 accelerometer and gyroscope features.

Outputs:
  - models/activity_model/activity_model.pkl
  - models/activity_model/feature_schema.json
"""

import json
import pathlib
import joblib
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    classification_report,
    confusion_matrix,
)

# Paths
BASE_DIR = pathlib.Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "datasets" / "wisdm_smartwatch" / "processed"
MODEL_DIR = BASE_DIR / "models" / "activity_model"

TRAIN_CSV = DATA_DIR / "train.csv"
TEST_CSV = DATA_DIR / "test.csv"
MODEL_PKL = MODEL_DIR / "activity_model.pkl"
SCHEMA_JSON = MODEL_DIR / "feature_schema.json"

TARGET_COL = "activity_label"
EXCLUDE_COLS = ["subject_id", TARGET_COL]


def run_data_integrity_checks(train_df, test_df, feature_cols):
    """Verifies dataset integrity criteria before model training."""
    print("  [Integrity Check 1] Verifying target column exists...")
    assert TARGET_COL in train_df.columns, f"Missing {TARGET_COL} in train dataset!"
    assert TARGET_COL in test_df.columns, f"Missing {TARGET_COL} in test dataset!"

    print("  [Integrity Check 2] Verifying subject_id is NOT in feature columns...")
    assert "subject_id" not in feature_cols, "subject_id was mistakenly included in features!"

    print("  [Integrity Check 3] Verifying feature count...")
    assert len(feature_cols) == 30, f"Expected 30 sensor features, found {len(feature_cols)}!"

    print("  [Integrity Check 4] Verifying train & test feature schemas match...")
    assert list(train_df[feature_cols].columns) == list(test_df[feature_cols].columns), "Feature schemas mismatch!"

    print("  [Integrity Check 5] Verifying 0 missing values...")
    train_nulls = train_df[feature_cols].isnull().sum().sum()
    test_nulls = test_df[feature_cols].isnull().sum().sum()
    assert train_nulls == 0, f"Found {train_nulls} missing values in train features!"
    assert test_nulls == 0, f"Found {test_nulls} missing values in test features!"

    print("  [Integrity Check 6] Verifying target is not in feature columns...")
    assert TARGET_COL not in feature_cols, "Target column is mistakenly in feature list!"

    print("  [OK] All 6 Data Integrity Checks Passed Successfully!\n")


def main():
    print("=" * 60)
    print("  SECTION 4 — Training Smartwatch Activity Model (Random Forest)")
    print("=" * 60)

    MODEL_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Load Datasets
    print(f"\n[1/5] Loading processed datasets from:\n  {DATA_DIR}")
    train_df = pd.read_csv(TRAIN_CSV)
    test_df = pd.read_csv(TEST_CSV)

    # Automatically identify feature columns (excluding subject_id and activity_label)
    feature_cols = [c for c in train_df.columns if c not in EXCLUDE_COLS]

    # Run Integrity Checks
    run_data_integrity_checks(train_df, test_df, feature_cols)

    X_train = train_df[feature_cols]
    y_train = train_df[TARGET_COL]

    X_test = test_df[feature_cols]
    y_test = test_df[TARGET_COL]

    classes = sorted(y_train.unique())
    print(f"  Training samples : {len(X_train)}")
    print(f"  Testing samples  : {len(X_test)}")
    print(f"  Feature count    : {len(feature_cols)}")
    print(f"  Activity classes : {len(classes)} classes")
    print(f"  Classes list     : {classes}\n")

    # 2. Train Random Forest Classifier
    print("[2/5] Training Random Forest Classifier...")
    rf_config = {
        "n_estimators": 200,
        "max_depth": 20,
        "min_samples_split": 2,
        "min_samples_leaf": 1,
        "random_state": 42,
        "n_jobs": -1,
        "class_weight": "balanced"
    }

    model = RandomForestClassifier(**rf_config)
    model.fit(X_train, y_train)
    print("  [OK] Model training complete.")

    # 3. Evaluate Model on Test Set
    print("\n[3/5] Evaluating model on holdout test set...")
    y_pred = model.predict(X_test)

    # Weighted metrics for multi-class classification
    avg_method = "weighted"
    acc = accuracy_score(y_test, y_pred)
    prec = precision_score(y_test, y_pred, average=avg_method)
    rec = recall_score(y_test, y_pred, average=avg_method)
    f1 = f1_score(y_test, y_pred, average=avg_method)

    print("-" * 55)
    print(f"  TEST EVALUATION METRICS (Averaging method: '{avg_method}')")
    print("-" * 55)
    print(f"  Accuracy  : {acc:.4f} ({acc*100:.2f}%)")
    print(f"  Precision : {prec:.4f}")
    print(f"  Recall    : {rec:.4f}")
    print(f"  F1-Score  : {f1:.4f}")
    print("-" * 55)

    print("\n--- Concise Classification Report ---")
    print(classification_report(y_test, y_pred, digits=4))

    # 4. Save Model & Feature Schema
    print("[4/5] Saving model artifacts...")

    # Save model using joblib
    joblib.dump(model, MODEL_PKL)
    print(f"  [OK] Saved Random Forest model to:\n       {MODEL_PKL}")

    # Save feature schema
    schema = {
        "model_type": "RandomForestClassifier",
        "target": TARGET_COL,
        "feature_names": feature_cols,
        "feature_count": len(feature_cols),
        "activity_classes": classes,
        "rf_configuration": rf_config,
        "test_metrics": {
            "averaging_method": avg_method,
            "accuracy": round(float(acc), 4),
            "precision": round(float(prec), 4),
            "recall": round(float(rec), 4),
            "f1_score": round(float(f1), 4),
        },
    }

    with open(SCHEMA_JSON, "w", encoding="utf-8") as f:
        json.dump(schema, f, indent=2)

    print(f"  [OK] Saved Feature Schema to:\n       {SCHEMA_JSON}")
    print("\n[5/5] Section 4 Model Training Finished Successfully!")


if __name__ == "__main__":
    main()

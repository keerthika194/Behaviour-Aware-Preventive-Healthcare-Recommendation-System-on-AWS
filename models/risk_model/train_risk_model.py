"""
Section 3 - Model 1: Preventive Risk Prediction (XGBoost)
==========================================================
Trains an XGBoost classifier on the BRFSS 2015 processed dataset to predict
diabetes/chronic health risk binary target (Diabetes_binary).

Outputs:
  - models/risk_model/risk_model.json
  - models/risk_model/feature_schema.json
"""

import json
import pathlib
import pandas as pd
import numpy as np
from xgboost import XGBClassifier
from sklearn.model_selection import GridSearchCV
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    classification_report,
)

# Paths
BASE_DIR = pathlib.Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "datasets" / "brfss_diabetes" / "processed"
MODEL_DIR = BASE_DIR / "models" / "risk_model"

TRAIN_CSV = DATA_DIR / "train.csv"
TEST_CSV = DATA_DIR / "test.csv"
MODEL_JSON = MODEL_DIR / "risk_model.json"
SCHEMA_JSON = MODEL_DIR / "feature_schema.json"

TARGET_COL = "Diabetes_binary"


def main():
    print("=" * 60)
    print("  SECTION 3 — Training Preventive Risk Model (XGBoost)")
    print("=" * 60)

    MODEL_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Load data
    print(f"\n[1/5] Loading processed datasets from:\n  {DATA_DIR}")
    train_df = pd.read_csv(TRAIN_CSV)
    test_df = pd.read_csv(TEST_CSV)

    feature_cols = [c for c in train_df.columns if c != TARGET_COL]
    print(f"  Predictor features ({len(feature_cols)}): {feature_cols}")

    X_train = train_df[feature_cols]
    y_train = train_df[TARGET_COL]

    X_test = test_df[feature_cols]
    y_test = test_df[TARGET_COL]

    print(f"  Train set shape: {X_train.shape}")
    print(f"  Test set shape : {X_test.shape}")

    # 2. Hyperparameter Grid Search
    print("\n[2/5] Running GridSearchCV hyperparameter tuning...")
    param_grid = {
        "max_depth": [3, 5, 7],
        "n_estimators": [100, 200],
        "learning_rate": [0.03, 0.08, 0.15],
        "subsample": [0.8, 1.0],
        "colsample_bytree": [0.8, 1.0],
    }

    base_xgb = XGBClassifier(
        eval_metric="logloss",
        random_state=42,
        n_jobs=-1,
    )

    grid_search = GridSearchCV(
        estimator=base_xgb,
        param_grid=param_grid,
        scoring="roc_auc",
        cv=3,
        verbose=1,
        n_jobs=-1,
    )

    grid_search.fit(X_train, y_train)

    best_params = grid_search.best_params_
    best_auc = grid_search.best_score_
    print(f"\n  [OK] Best CV ROC-AUC: {best_auc:.4f}")
    print(f"  [OK] Best Hyperparameters: {json.dumps(best_params, indent=2)}")

    best_model = grid_search.best_estimator_

    # 3. Evaluate on test set
    print("\n[3/5] Evaluating optimal model on holdout test set...")
    y_pred = best_model.predict(X_test)
    y_proba = best_model.predict_proba(X_test)[:, 1]

    acc = accuracy_score(y_test, y_pred)
    prec = precision_score(y_test, y_pred)
    rec = recall_score(y_test, y_pred)
    f1 = f1_score(y_test, y_pred)
    auc = roc_auc_score(y_test, y_proba)

    print("-" * 50)
    print("  TEST EVALUATION METRICS:")
    print("-" * 50)
    print(f"  Accuracy  : {acc:.4f} ({acc*100:.2f}%)")
    print(f"  Precision : {prec:.4f}")
    print(f"  Recall    : {rec:.4f}")
    print(f"  F1-Score  : {f1:.4f}")
    print(f"  AUC-ROC   : {auc:.4f}")
    print("-" * 50)

    # 4. Save Model and Feature Schema
    print("\n[4/5] Saving model artifacts...")

    # Save model natively as JSON
    best_model.save_model(str(MODEL_JSON))
    print(f"  [OK] Saved XGBoost model to:\n       {MODEL_JSON}")

    # Save feature schema
    schema = {
        "model_type": "XGBoostClassifier",
        "target": TARGET_COL,
        "feature_names": feature_cols,
        "feature_count": len(feature_cols),
        "best_hyperparameters": best_params,
        "test_metrics": {
            "accuracy": round(float(acc), 4),
            "precision": round(float(prec), 4),
            "recall": round(float(rec), 4),
            "f1_score": round(float(f1), 4),
            "auc_roc": round(float(auc), 4),
        },
    }

    with open(SCHEMA_JSON, "w", encoding="utf-8") as f:
        json.dump(schema, f, indent=2)

    print(f"  [OK] Saved Feature Schema to:\n       {SCHEMA_JSON}")

    # 5. Output Summary JSON for automated parsing
    print("\n[5/5] Section 3 Model Training Finished Successfully!")


if __name__ == "__main__":
    main()

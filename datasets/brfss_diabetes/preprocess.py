"""
BRFSS 2015 Diabetes Health Indicators — Preprocessing Script
=============================================================
Dataset:  Diabetes Health Indicators Dataset (BRFSS 2015)
Source:   https://www.kaggle.com/datasets/alexteboul/diabetes-health-indicators-dataset
Author:   Alex Teboul (original CDC BRFSS data)
License:  CC0 — Public Domain

Expected raw file (place in datasets/brfss_diabetes/raw/ before running):
  1. diabetes_binary_5050split_health_indicators_BRFSS2015.csv   ← preferred (balanced 70,692 rows)
  2. diabetes_binary_health_indicators_BRFSS2015.csv             ← fallback (253,680 rows, imbalanced)

Outputs:
  datasets/brfss_diabetes/processed/train.csv   (80 % split)
  datasets/brfss_diabetes/processed/test.csv    (20 % split)

Steps performed:
  1. Detect and load the best available raw CSV.
  2. Drop duplicate rows.
  3. Verify / handle missing values (dataset is documented as clean; we still check).
  4. Encode binary columns (already 0/1 in this dataset — verified).
  5. Balance classes if the imbalanced fallback file was used (random undersample).
  6. 80/20 stratified train/test split.
  7. Save processed CSVs with headers.
  8. Print dataset shapes and class distributions.
"""

import os
import sys
import pathlib
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.utils import resample

# ── Paths ─────────────────────────────────────────────────────────────────────
SCRIPT_DIR   = pathlib.Path(__file__).resolve().parent
RAW_DIR      = SCRIPT_DIR / "raw"
PROCESSED_DIR = SCRIPT_DIR / "processed"
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

# Preferred balanced file first, then full imbalanced version
CANDIDATE_FILES = [
    "diabetes_binary_5050split_health_indicators_BRFSS2015.csv",  # 70,692 rows, balanced
    "diabetes_binary_health_indicators_BRFSS2015.csv",            # 253,680 rows, imbalanced
]

TARGET_COLUMN = "Diabetes_binary"
RANDOM_STATE  = 42
TEST_SIZE     = 0.20

# ── Helper: print separator ───────────────────────────────────────────────────
def section(title: str) -> None:
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print('=' * 60)

# ── Step 1: Locate raw file ───────────────────────────────────────────────────
section("Step 1 — Locating raw CSV file")

chosen_file = None
is_balanced  = False

for fname in CANDIDATE_FILES:
    fpath = RAW_DIR / fname
    if fpath.exists():
        chosen_file = fpath
        is_balanced = "5050split" in fname
        print(f"  ✔ Found: {fpath}")
        print(f"  → Balanced (pre-split 50-50): {is_balanced}")
        break

if chosen_file is None:
    print("\n  ✘ ERROR: No raw CSV found in:", RAW_DIR)
    print("  Please download the dataset from Kaggle and place the CSV in:")
    print(f"    {RAW_DIR}")
    print("  Expected filenames:")
    for f in CANDIDATE_FILES:
        print(f"    • {f}")
    sys.exit(1)

# ── Step 2: Load data ─────────────────────────────────────────────────────────
section("Step 2 — Loading raw data")
df = pd.read_csv(chosen_file)
print(f"  Raw shape : {df.shape}")
print(f"  Columns   : {list(df.columns)}")

# ── Step 3: Verify target column exists ──────────────────────────────────────
section("Step 3 — Verifying target column")
if TARGET_COLUMN not in df.columns:
    print(f"  ✘ ERROR: Target column '{TARGET_COLUMN}' not found.")
    print(f"  Available columns: {list(df.columns)}")
    sys.exit(1)
print(f"  ✔ Target column '{TARGET_COLUMN}' found.")
print(f"  Raw class distribution:\n{df[TARGET_COLUMN].value_counts()}")

# ── Step 4: Drop duplicates ───────────────────────────────────────────────────
section("Step 4 — Removing duplicates")
before = len(df)
df.drop_duplicates(inplace=True)
after  = len(df)
print(f"  Dropped {before - after} duplicate row(s). Remaining: {after}")

# ── Step 5: Handle missing values ─────────────────────────────────────────────
section("Step 5 — Handling missing values")
missing = df.isnull().sum()
total_missing = missing.sum()
print(f"  Total missing values: {total_missing}")
if total_missing > 0:
    print("  Missing per column:")
    print(missing[missing > 0])
    # Strategy: drop rows with any missing target; fill numeric features with median
    df.dropna(subset=[TARGET_COLUMN], inplace=True)
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    for col in numeric_cols:
        if df[col].isnull().any():
            median_val = df[col].median()
            df[col].fillna(median_val, inplace=True)
            print(f"  Filled '{col}' missing values with median={median_val:.4f}")
    print(f"  Shape after missing-value handling: {df.shape}")
else:
    print("  ✔ No missing values found — dataset is clean.")

# ── Step 6: Validate and encode categorical columns ───────────────────────────
section("Step 6 — Validating feature types")
# The BRFSS dataset features are already binary (0/1) or numeric ordinal.
# We confirm all columns are numeric; no further encoding needed.
non_numeric = df.select_dtypes(exclude=[np.number]).columns.tolist()
if non_numeric:
    print(f"  Non-numeric columns found: {non_numeric}")
    print("  Converting to numeric where possible …")
    for col in non_numeric:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df.dropna(inplace=True)
    print(f"  Shape after type coercion: {df.shape}")
else:
    print("  ✔ All columns are already numeric — no encoding needed.")

# ── Step 7: Balance classes (only if using the imbalanced fallback) ───────────
section("Step 7 — Class balancing")
class_counts = df[TARGET_COLUMN].value_counts()
print(f"  Class counts before balancing:\n{class_counts}")

if is_balanced:
    print("  ✔ Using the pre-balanced 50-50 split file — no resampling needed.")
else:
    print("  Using imbalanced fallback file → applying random undersampling …")
    majority_class = class_counts.idxmax()
    minority_class = class_counts.idxmin()
    minority_count = class_counts[minority_class]

    df_majority = df[df[TARGET_COLUMN] == majority_class]
    df_minority = df[df[TARGET_COLUMN] == minority_class]

    df_majority_down = resample(
        df_majority,
        replace=False,
        n_samples=minority_count,
        random_state=RANDOM_STATE
    )
    df = pd.concat([df_majority_down, df_minority]).sample(
        frac=1, random_state=RANDOM_STATE
    ).reset_index(drop=True)

    print(f"  Class counts after undersampling:\n{df[TARGET_COLUMN].value_counts()}")
    print(f"  Balanced shape: {df.shape}")

# ── Step 8: Stratified 80/20 train-test split ─────────────────────────────────
section("Step 8 — Stratified train/test split (80/20)")
X = df.drop(columns=[TARGET_COLUMN])
y = df[TARGET_COLUMN]

X_train, X_test, y_train, y_test = train_test_split(
    X, y,
    test_size=TEST_SIZE,
    random_state=RANDOM_STATE,
    stratify=y
)

train_df = pd.concat([X_train, y_train], axis=1)
test_df  = pd.concat([X_test,  y_test],  axis=1)

print(f"  Train shape : {train_df.shape}")
print(f"  Test  shape : {test_df.shape}")

# ── Step 9: Save processed files ──────────────────────────────────────────────
section("Step 9 — Saving processed files")
train_path = PROCESSED_DIR / "train.csv"
test_path  = PROCESSED_DIR / "test.csv"

train_df.to_csv(train_path, index=False)
test_df.to_csv(test_path,  index=False)

print(f"  ✔ Saved: {train_path}")
print(f"  ✔ Saved: {test_path}")

# ── Step 10: Summary report ───────────────────────────────────────────────────
section("BRFSS Preprocessing Complete — Summary")
print(f"\n  1. BRFSS train dataset shape   : {train_df.shape}")
print(f"  2. BRFSS test  dataset shape   : {test_df.shape}")
print(f"\n  3. BRFSS class distribution (train):")
print(train_df[TARGET_COLUMN].value_counts().to_string(header=False))
print(f"\n  3b. BRFSS class distribution (test):")
print(test_df[TARGET_COLUMN].value_counts().to_string(header=False))
print(f"\n  7. Generated files:")
print(f"     • {train_path}")
print(f"     • {test_path}")
print()

"""
WISDM Smartwatch Activity Dataset — Preprocessing Script
=========================================================
Dataset:  WISDM Smartphone and Smartwatch Activity and Biometrics Dataset
Source:   https://archive.ics.uci.edu/dataset/507/wisdm+smartphone+and+smartwatch+activity+and+biometrics+dataset
Author:   G. Weiss, Fordham University / WISDM Lab
License:  CC BY 4.0
DOI:      https://doi.org/10.24432/C5HK59

Expected raw directory structure (after unzipping wisdm-dataset.zip):
  datasets/wisdm_smartwatch/raw/
  └── wisdm-dataset/
      ├── activity_key.txt
      ├── watch_accelerometer/       ← 51 files: data1600.txt … data1650.txt
      ├── watch_gyroscope/           ← 51 files: data1600.txt … data1650.txt
      ├── phone_accelerometer/       ← IGNORED — we only use watch sensors
      └── phone_gyroscope/           ← IGNORED — we only use watch sensors

NOTE: Only watch_accelerometer and watch_gyroscope directories are used.

Raw data format per line:
  <subject_id>,<activity_code>,<timestamp>,<x>,<y>,<z>;

Feature extraction:
  - Segment time-series into non-overlapping 10-second windows (20 Hz → 200 samples/window)
  - For each axis (x, y, z) in accelerometer and gyroscope:
      • mean, std, min, max, avg_abs_diff
  - Total features: 3 axes × 5 stats × 2 sensors = 30 features

Output:
  datasets/wisdm_smartwatch/processed/train.csv
  datasets/wisdm_smartwatch/processed/test.csv
"""

import os
import sys
import pathlib
import re
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split

# ── Paths ─────────────────────────────────────────────────────────────────────
SCRIPT_DIR    = pathlib.Path(__file__).resolve().parent
RAW_DIR       = SCRIPT_DIR / "raw"
PROCESSED_DIR = SCRIPT_DIR / "processed"
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

# The zip extracts to a folder called "wisdm-dataset"
# We support both the direct unzip location and one level up
POSSIBLE_ROOTS = [
    RAW_DIR / "wisdm-dataset",
    RAW_DIR,
]

WATCH_ACC_DIR_NAME = "watch_accelerometer"
WATCH_GYR_DIR_NAME = "watch_gyroscope"
ACTIVITY_KEY_NAME  = "activity_key.txt"

SAMPLE_RATE    = 20          # Hz — collected at 20 samples per second
WINDOW_SECONDS = 10          # seconds per window
WINDOW_SIZE    = SAMPLE_RATE * WINDOW_SECONDS   # 200 samples per window
RANDOM_STATE   = 42
TEST_SIZE      = 0.20

# ── Helper ────────────────────────────────────────────────────────────────────
def section(title: str) -> None:
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print('=' * 60)

# ── Step 1: Locate dataset root ───────────────────────────────────────────────
section("Step 1 — Locating WISDM dataset root")

dataset_root = None
for candidate in POSSIBLE_ROOTS:
    acc_path = candidate / WATCH_ACC_DIR_NAME
    gyr_path = candidate / WATCH_GYR_DIR_NAME
    if acc_path.exists() and gyr_path.exists():
        dataset_root = candidate
        break

if dataset_root is None:
    print("\n  ✘ ERROR: WISDM dataset directories not found.")
    print(f"  Expected inside: {RAW_DIR}")
    print(f"  Looking for   : {WATCH_ACC_DIR_NAME}/ and {WATCH_GYR_DIR_NAME}/")
    print("\n  Please:")
    print("  1. Download wisdm-dataset.zip from:")
    print("     https://archive.ics.uci.edu/dataset/507/")
    print("  2. Unzip it so the folder structure is:")
    print(f"     {RAW_DIR}/wisdm-dataset/{WATCH_ACC_DIR_NAME}/data1600.txt ...")
    sys.exit(1)

watch_acc_dir = dataset_root / WATCH_ACC_DIR_NAME
watch_gyr_dir = dataset_root / WATCH_GYR_DIR_NAME
activity_key_path = dataset_root / ACTIVITY_KEY_NAME

print(f"  ✔ Dataset root    : {dataset_root}")
print(f"  ✔ Watch accel dir : {watch_acc_dir}")
print(f"  ✔ Watch gyro  dir : {watch_gyr_dir}")
print(f"  ✔ Activity key    : {activity_key_path}")

# ── Step 2: Load activity key ─────────────────────────────────────────────────
section("Step 2 — Loading activity key")

activity_map = {}   # code → label

if activity_key_path.exists():
    with open(activity_key_path, "r") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            # Expected format: "A = Walking" or "A=Walking"
            # Try several separators
            match = re.match(r"^([A-S])\s*[=:]\s*(.+)$", line, re.IGNORECASE)
            if match:
                code  = match.group(1).upper()
                label = match.group(2).strip()
                activity_map[code] = label
    print(f"  ✔ Loaded {len(activity_map)} activity mappings:")
    for code, label in sorted(activity_map.items()):
        print(f"     {code} → {label}")
else:
    # Fallback: use the documented activity codes from the paper
    print(f"  ⚠  activity_key.txt not found at {activity_key_path}")
    print("  Using documented WISDM activity codes as fallback …")
    activity_map = {
        "A": "Walking",
        "B": "Jogging",
        "C": "Stairs",
        "D": "Sitting",
        "E": "Standing",
        "F": "Typing",
        "G": "Brushing_Teeth",
        "H": "Eating_Soup",
        "I": "Eating_Chips",
        "J": "Eating_Pasta",
        "K": "Drinking_from_Cup",
        "L": "Eating_Sandwich",
        "M": "Kicking_Soccer_Ball",
        "O": "Catch_Tennis_Ball",
        "P": "Dribbling_Basketball",
        "Q": "Writing",
        "R": "Clapping",
        "S": "Folding_Clothes",
    }
    print(f"  Using {len(activity_map)} fallback activity labels.")

# ── Step 3: Read raw sensor files ─────────────────────────────────────────────

def read_sensor_dir(sensor_dir: pathlib.Path, sensor_name: str) -> pd.DataFrame:
    """
    Read all subject files from a sensor directory.
    Each line: subject_id,activity_code,timestamp,x,y,z;
    Returns a clean DataFrame with columns:
        subject_id, activity_code, timestamp, x, y, z
    """
    all_rows = []
    files    = sorted(sensor_dir.glob("data*.txt"))

    if not files:
        print(f"  ✘ ERROR: No data*.txt files found in {sensor_dir}")
        sys.exit(1)

    print(f"  Reading {len(files)} files from {sensor_dir.name} …")

    for fpath in files:
        subject_id = int(re.search(r"data(\d+)", fpath.stem).group(1))
        with open(fpath, "r", errors="replace") as f:
            content = f.read()

        # Each record ends with ';' — split on semicolons to handle multiline
        records = content.replace("\n", "").split(";")
        for record in records:
            record = record.strip().strip(",")
            if not record:
                continue
            parts = [p.strip() for p in record.split(",")]
            if len(parts) < 6:
                continue
            try:
                sid       = int(parts[0])
                act_code  = parts[1].strip().upper()
                timestamp = int(parts[2])
                x         = float(parts[3])
                y         = float(parts[4])
                z         = float(parts[5])
                all_rows.append((sid, act_code, timestamp, x, y, z))
            except (ValueError, IndexError):
                continue   # skip malformed lines

    df = pd.DataFrame(all_rows, columns=["subject_id", "activity_code", "timestamp", "x", "y", "z"])
    print(f"  ✔ {sensor_name}: {len(df):,} raw readings loaded from {len(files)} subjects.")
    return df

section("Step 3 — Reading watch sensor data (WATCH ONLY)")
df_acc = read_sensor_dir(watch_acc_dir, "watch_accelerometer")
df_gyr = read_sensor_dir(watch_gyr_dir, "watch_gyroscope")

# ── Step 4: Quality checks ────────────────────────────────────────────────────
section("Step 4 — Quality checks")

for name, df in [("Accel", df_acc), ("Gyro", df_gyr)]:
    null_count = df.isnull().sum().sum()
    print(f"  {name}: {df.shape}, nulls={null_count}, "
          f"subjects={df['subject_id'].nunique()}, "
          f"activities={sorted(df['activity_code'].unique())}")

# ── Step 5: Window-based feature extraction ────────────────────────────────────

def extract_features(df: pd.DataFrame, prefix: str) -> pd.DataFrame:
    """
    Segment each (subject, activity) sequence into non-overlapping 10-second
    windows and extract statistical features for axes x, y, z.

    Features per axis: mean, std, min, max, avg_abs_diff
    Total per sensor: 3 axes × 5 features = 15 feature columns
    """
    # Sort for deterministic windowing
    df = df.sort_values(["subject_id", "activity_code", "timestamp"]).reset_index(drop=True)

    records = []
    axes    = ["x", "y", "z"]
    stats   = ["mean", "std", "min", "max", "avg_abs_diff"]

    for (subject_id, activity_code), group in df.groupby(["subject_id", "activity_code"], sort=False):
        data   = group[["x", "y", "z"]].values
        n_rows = len(data)
        n_windows = n_rows // WINDOW_SIZE

        for w in range(n_windows):
            window = data[w * WINDOW_SIZE: (w + 1) * WINDOW_SIZE]
            row = {
                "subject_id"    : subject_id,
                "activity_code" : activity_code,
                "window_index"  : w,
            }
            for i, axis in enumerate(axes):
                col = window[:, i]
                row[f"{prefix}_{axis}_mean"]         = float(np.mean(col))
                row[f"{prefix}_{axis}_std"]          = float(np.std(col))
                row[f"{prefix}_{axis}_min"]          = float(np.min(col))
                row[f"{prefix}_{axis}_max"]          = float(np.max(col))
                row[f"{prefix}_{axis}_avg_abs_diff"] = float(np.mean(np.abs(col - np.mean(col))))
            records.append(row)

    result = pd.DataFrame(records)
    print(f"  ✔ {prefix}: extracted {len(result):,} windows from "
          f"{df['subject_id'].nunique()} subjects.")
    return result

section("Step 5 — Extracting statistical features (10-second windows)")
feat_acc = extract_features(df_acc, prefix="acc")
feat_gyr = extract_features(df_gyr, prefix="gyr")

# ── Step 6: Join accelerometer and gyroscope features ────────────────────────
section("Step 6 — Joining accelerometer + gyroscope features")

feat_acc_key = feat_acc[["subject_id", "activity_code", "window_index"]]
feat_gyr_key = feat_gyr[["subject_id", "activity_code", "window_index"]]

merged = pd.merge(
    feat_acc,
    feat_gyr.drop(columns=["subject_id", "activity_code"]),
    on="window_index",
    how="inner"
)

# Better join: merge on all three key columns
merged = pd.merge(
    feat_acc,
    feat_gyr,
    on=["subject_id", "activity_code", "window_index"],
    how="inner",
    suffixes=("_acc", "_gyr")
)

print(f"  Merged shape: {merged.shape}")
print(f"  Columns     : {list(merged.columns)}")

# ── Step 7: Map activity codes to labels ──────────────────────────────────────
section("Step 7 — Mapping activity codes to labels")
merged["activity_label"] = merged["activity_code"].map(activity_map)
unmapped = merged["activity_label"].isnull().sum()
if unmapped > 0:
    print(f"  ⚠  {unmapped} rows with unmapped activity codes → keeping raw code as label")
    merged["activity_label"].fillna(merged["activity_code"], inplace=True)

print(f"  Activity distribution:")
print(merged["activity_label"].value_counts().to_string())

# ── Step 8: Prepare final feature matrix ─────────────────────────────────────
section("Step 8 — Preparing final feature matrix")

# Drop join keys that aren't features; keep subject_id for potential stratification
drop_cols = ["window_index", "activity_code"]
# Remove any duplicate-suffixed columns from the merge
dup_cols = [c for c in merged.columns if c.endswith("_acc") or c.endswith("_gyr")]
# These are the _acc/_gyr suffixed keys if they appeared — drop them
extra_drops = [c for c in dup_cols if "_acc" in c and c.replace("_acc", "_gyr") in merged.columns]

final = merged.drop(columns=drop_cols, errors="ignore")

# The target variable is "activity_label"
print(f"  Final shape before split: {final.shape}")
print(f"  Columns: {list(final.columns)}")

# ── Step 9: Stratified train/test split ──────────────────────────────────────
section("Step 9 — Stratified train/test split (80/20)")

# Use activity_label as stratification target
X = final.drop(columns=["activity_label"])
y = final["activity_label"]

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

# ── Step 10: Save processed files ─────────────────────────────────────────────
section("Step 10 — Saving processed files")
train_path = PROCESSED_DIR / "train.csv"
test_path  = PROCESSED_DIR / "test.csv"

train_df.to_csv(train_path, index=False)
test_df.to_csv(test_path,  index=False)

print(f"  ✔ Saved: {train_path}")
print(f"  ✔ Saved: {test_path}")

# ── Step 11: Summary report ───────────────────────────────────────────────────
section("WISDM Preprocessing Complete — Summary")
print(f"\n  4. WISDM train dataset shape     : {train_df.shape}")
print(f"  5. WISDM test  dataset shape     : {test_df.shape}")
print(f"\n  6. WISDM activity/class distribution (train):")
print(train_df["activity_label"].value_counts().to_string())
print(f"\n  6b. WISDM activity/class distribution (test):")
print(test_df["activity_label"].value_counts().to_string())
print(f"\n  7. Generated files:")
print(f"     • {train_path}")
print(f"     • {test_path}")
print()

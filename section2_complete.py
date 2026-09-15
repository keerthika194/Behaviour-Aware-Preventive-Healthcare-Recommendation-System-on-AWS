"""
Section 2 - Complete Dataset Pipeline (fixed for actual WISDM zip structure)
=============================================================================
WISDM actual structure inside zip:
  wisdm-dataset/
  |-- activity_key.txt
  |-- raw/
  |   |-- watch/
  |   |   |-- accel/   data_XXXX_accel_watch.txt  (51 files)
  |   |   `-- gyro/    data_XXXX_gyro_watch.txt   (51 files)
  |   `-- phone/       (IGNORED)
  `-- arff_files/      (IGNORED - pre-extracted features)

Run from E:\\AWS Project:
    python section2_complete.py
"""
import sys, os, pathlib, zipfile, shutil
import subprocess

ROOT = pathlib.Path(__file__).resolve().parent

# --- Install missing packages ---
def install_if_missing(packages):
    for pkg in packages:
        mod = pkg.split("==")[0].replace("-","_")
        try:
            __import__(mod)
        except ImportError:
            print("  Installing %s ..." % pkg)
            subprocess.check_call([sys.executable, "-m", "pip", "install", pkg, "-q"])

print("=" * 60)
print("  Step 0 - Checking / installing packages")
print("=" * 60)
install_if_missing(["pandas", "numpy", "scikit-learn"])
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.utils import resample
print("  [OK] All packages ready.\n")

# --- Paths ---
BRFSS_RAW  = ROOT / "datasets" / "brfss_diabetes"   / "raw"
BRFSS_PROC = ROOT / "datasets" / "brfss_diabetes"   / "processed"
WISDM_RAW  = ROOT / "datasets" / "wisdm_smartwatch" / "raw"
WISDM_PROC = ROOT / "datasets" / "wisdm_smartwatch" / "processed"
for d in [BRFSS_RAW, BRFSS_PROC, WISDM_RAW, WISDM_PROC]:
    d.mkdir(parents=True, exist_ok=True)

WISDM_ZIP    = WISDM_RAW / "wisdm-dataset.zip"
RANDOM_STATE = 42
TARGET_COL   = "Diabetes_binary"
SAMPLE_RATE  = 20
WINDOW_SIZE  = 200   # 10s x 20Hz


# =============================================================================
# PART 1 - BRFSS
# =============================================================================
BRFSS_BALANCED = "diabetes_binary_5050split_health_indicators_BRFSS2015.csv"
BRFSS_FALLBACK = "diabetes_binary_health_indicators_BRFSS2015.csv"

def find_brfss_csv():
    for fname in [BRFSS_BALANCED, BRFSS_FALLBACK]:
        p = BRFSS_RAW / fname
        if p.exists():
            return p
    for sub in BRFSS_RAW.iterdir():
        if sub.is_dir():
            for fname in [BRFSS_BALANCED, BRFSS_FALLBACK]:
                p = sub / fname
                if p.exists():
                    return p
    return None

def preprocess_brfss(csv_path):
    print("\n" + "=" * 60)
    print("  BRFSS Preprocessing: %s" % csv_path.name)
    print("=" * 60)
    is_balanced = "5050split" in csv_path.name

    df = pd.read_csv(csv_path)
    print("  Raw shape: %s" % str(df.shape))

    before = len(df)
    df.drop_duplicates(inplace=True)
    print("  Dropped %d duplicates." % (before - len(df)))

    total_missing = df.isnull().sum().sum()
    print("  Missing values: %d" % total_missing)
    if total_missing > 0:
        df.dropna(subset=[TARGET_COL], inplace=True)
        for col in df.select_dtypes(include=[np.number]).columns:
            if df[col].isnull().any():
                df[col].fillna(df[col].median(), inplace=True)

    non_num = df.select_dtypes(exclude=[np.number]).columns.tolist()
    if non_num:
        for col in non_num:
            df[col] = pd.to_numeric(df[col], errors="coerce")
        df.dropna(inplace=True)

    counts = df[TARGET_COL].value_counts()
    print("  Class counts: %s" % str(counts.to_dict()))
    if not is_balanced:
        maj, minn = counts.idxmax(), counts.idxmin()
        df_down = resample(df[df[TARGET_COL]==maj], replace=False,
                           n_samples=counts[minn], random_state=RANDOM_STATE)
        df = pd.concat([df_down, df[df[TARGET_COL]==minn]]).sample(
            frac=1, random_state=RANDOM_STATE).reset_index(drop=True)

    X, y = df.drop(columns=[TARGET_COL]), df[TARGET_COL]
    X_tr, X_te, y_tr, y_te = train_test_split(
        X, y, test_size=0.20, random_state=RANDOM_STATE, stratify=y)
    train_df = pd.concat([X_tr, y_tr], axis=1)
    test_df  = pd.concat([X_te, y_te], axis=1)

    train_df.to_csv(BRFSS_PROC / "train.csv", index=False)
    test_df.to_csv(BRFSS_PROC  / "test.csv",  index=False)
    print("  [OK] train.csv saved  shape=%s" % str(train_df.shape))
    print("  [OK] test.csv  saved  shape=%s" % str(test_df.shape))
    return train_df, test_df


# =============================================================================
# PART 2 - WISDM
# =============================================================================

def find_wisdm_root():
    """
    Find the extracted wisdm-dataset root.
    Actual structure: wisdm-dataset/raw/watch/accel/ and .../gyro/
    We return the directory that contains raw/watch/accel/
    """
    candidates = [
        WISDM_RAW / "wisdm-dataset",
        WISDM_RAW,
    ]
    for c in candidates:
        if (c / "raw" / "watch" / "accel").exists():
            return c
    # Search one level deeper
    for sub in WISDM_RAW.iterdir():
        if sub.is_dir() and (sub / "raw" / "watch" / "accel").exists():
            return sub
    return None

def extract_wisdm():
    """Extract the WISDM zip. Handles single-level zip (no nested zip)."""
    root = find_wisdm_root()
    if root:
        print("  [OK] WISDM already extracted at: %s" % root)
        return root

    if not WISDM_ZIP.exists():
        print("  [FAIL] wisdm-dataset.zip not found at: %s" % WISDM_ZIP)
        return None

    print("  Validating zip (%.1f MB) ..." % (WISDM_ZIP.stat().st_size/(1024*1024)))
    try:
        with zipfile.ZipFile(WISDM_ZIP, "r") as zf:
            members = zf.namelist()
            top = sorted(set(m.split("/")[0] for m in members))
            print("  Top-level items: %s  |  Total members: %d" % (top, len(members)))
    except (zipfile.BadZipFile, EOFError) as e:
        print("  [FAIL] Zip is corrupt: %s" % e)
        return None

    print("  Extracting (this may take a minute) ...")
    with zipfile.ZipFile(WISDM_ZIP, "r") as zf:
        zf.extractall(WISDM_RAW)
    print("  [OK] Extraction complete.")

    root = find_wisdm_root()
    if not root:
        print("  [FAIL] Could not find raw/watch/accel/ after extraction.")
        print("  Contents:")
        for item in sorted(WISDM_RAW.iterdir()):
            print("    %s" % item.name)
    return root

def load_activity_key(dataset_root):
    import re
    key_path = dataset_root / "activity_key.txt"
    activity_map = {}
    if key_path.exists():
        with open(key_path, "r", errors="replace") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                # Format: "A = Walking" or "A - Walking" etc.
                m = re.match(r"^([A-S])\s*[=:\-,\t ]+(.+)$", line, re.IGNORECASE)
                if m:
                    activity_map[m.group(1).upper()] = m.group(2).strip()
        print("  [OK] Loaded %d activity labels:" % len(activity_map))
        for k, v in sorted(activity_map.items()):
            print("       %s -> %s" % (k, v))
    if not activity_map:
        print("  [WARN] Using hardcoded fallback activity labels")
        activity_map = {
            "A":"Walking","B":"Jogging","C":"Stairs","D":"Sitting",
            "E":"Standing","F":"Typing","G":"Brushing_Teeth",
            "H":"Eating_Soup","I":"Eating_Chips","J":"Eating_Pasta",
            "K":"Drinking_from_Cup","L":"Eating_Sandwich",
            "M":"Kicking_Soccer_Ball","O":"Catch_Tennis_Ball",
            "P":"Dribbling_Basketball","Q":"Writing",
            "R":"Clapping","S":"Folding_Clothes",
        }
    return activity_map

def read_sensor_dir(sensor_dir, sensor_name):
    """
    Read all .txt files from a sensor directory.
    Each file: data_XXXX_accel_watch.txt or data_XXXX_gyro_watch.txt
    Format per line: subject_id,activity_code,timestamp,x,y,z;
    """
    import re
    all_rows = []
    files = sorted(sensor_dir.glob("*.txt"))
    print("  Reading %d files from %s ..." % (len(files), sensor_dir.name))

    for fpath in files:
        try:
            with open(fpath, "r", errors="replace") as f:
                content = f.read()
        except Exception as e:
            print("    [WARN] Skipping %s: %s" % (fpath.name, e))
            continue

        # Split on semicolons (each record ends with ;)
        records = content.replace("\n", "").split(";")
        for rec in records:
            rec = rec.strip().strip(",")
            if not rec:
                continue
            parts = [p.strip() for p in rec.split(",")]
            if len(parts) < 6:
                continue
            try:
                sid      = int(float(parts[0]))
                act_code = parts[1].strip().upper()
                ts       = int(float(parts[2]))
                x        = float(parts[3])
                y        = float(parts[4])
                z        = float(parts[5])
                all_rows.append((sid, act_code, ts, x, y, z))
            except (ValueError, IndexError):
                continue

    df = pd.DataFrame(all_rows, columns=["subject_id","activity_code","timestamp","x","y","z"])
    print("  [OK] %s: %d readings, %d subjects, activities: %s" % (
        sensor_name, len(df), df["subject_id"].nunique(),
        sorted(df["activity_code"].unique())))
    return df

def extract_features(df, prefix):
    """Extract 5 statistical features per axis in 10-sec non-overlapping windows."""
    df = df.sort_values(["subject_id","activity_code","timestamp"]).reset_index(drop=True)
    records = []
    for (sid, act), group in df.groupby(["subject_id","activity_code"], sort=False):
        data  = group[["x","y","z"]].values
        n_win = len(data) // WINDOW_SIZE
        for w in range(n_win):
            win = data[w*WINDOW_SIZE:(w+1)*WINDOW_SIZE]
            row = {"subject_id": sid, "activity_code": act, "window_index": w}
            for i, axis in enumerate(["x","y","z"]):
                col = win[:, i]
                row["%s_%s_mean"        % (prefix,axis)] = float(np.mean(col))
                row["%s_%s_std"         % (prefix,axis)] = float(np.std(col))
                row["%s_%s_min"         % (prefix,axis)] = float(np.min(col))
                row["%s_%s_max"         % (prefix,axis)] = float(np.max(col))
                row["%s_%s_avg_abs_diff"% (prefix,axis)] = float(np.mean(np.abs(col - np.mean(col))))
            records.append(row)
    result = pd.DataFrame(records)
    print("  [OK] %s: %d windows from %d subjects" % (prefix, len(result), df["subject_id"].nunique()))
    return result

def preprocess_wisdm(dataset_root):
    print("\n" + "=" * 60)
    print("  WISDM Preprocessing")
    print("=" * 60)

    activity_map = load_activity_key(dataset_root)

    # Actual paths in this zip version
    watch_acc_dir = dataset_root / "raw" / "watch" / "accel"
    watch_gyr_dir = dataset_root / "raw" / "watch" / "gyro"

    print("\n  Watch accel dir : %s  exists=%s  files=%d" % (
        watch_acc_dir, watch_acc_dir.exists(),
        len(list(watch_acc_dir.glob("*.txt"))) if watch_acc_dir.exists() else 0))
    print("  Watch gyro  dir : %s  exists=%s  files=%d" % (
        watch_gyr_dir, watch_gyr_dir.exists(),
        len(list(watch_gyr_dir.glob("*.txt"))) if watch_gyr_dir.exists() else 0))

    if not watch_acc_dir.exists() or not watch_gyr_dir.exists():
        print("  [FAIL] Watch directories not found. Checking dataset root structure ...")
        for item in sorted(dataset_root.iterdir()):
            print("    %s" % item)
        return None, None

    # Read WATCH ONLY sensor data
    df_acc = read_sensor_dir(watch_acc_dir, "watch_accel")
    df_gyr = read_sensor_dir(watch_gyr_dir, "watch_gyro")

    # Quality check
    for name, df in [("Accel", df_acc), ("Gyro", df_gyr)]:
        print("  %s: shape=%s  nulls=%d" % (name, str(df.shape), df.isnull().sum().sum()))

    # Feature extraction
    print("\n  Extracting windowed features (10s x 20Hz = 200 samples/window) ...")
    feat_acc = extract_features(df_acc, "acc")
    feat_gyr = extract_features(df_gyr, "gyr")

    # Join on (subject_id, activity_code, window_index)
    merged = pd.merge(
        feat_acc, feat_gyr,
        on=["subject_id","activity_code","window_index"],
        how="inner"
    )
    print("  Merged shape: %s" % str(merged.shape))

    # Map activity codes to labels
    merged["activity_label"] = merged["activity_code"].map(activity_map)
    unmapped = merged["activity_label"].isnull().sum()
    if unmapped > 0:
        print("  [WARN] %d windows have unmapped activity codes; using code as label" % unmapped)
        merged["activity_label"].fillna(merged["activity_code"], inplace=True)

    print("\n  Activity label distribution:")
    print(merged["activity_label"].value_counts().to_string())

    # Drop non-feature columns; keep subject_id for traceability
    final = merged.drop(columns=["window_index","activity_code"], errors="ignore")

    X = final.drop(columns=["activity_label"])
    y = final["activity_label"]

    X_tr, X_te, y_tr, y_te = train_test_split(
        X, y, test_size=0.20, random_state=RANDOM_STATE, stratify=y)
    train_df = pd.concat([X_tr, y_tr], axis=1)
    test_df  = pd.concat([X_te,  y_te], axis=1)

    train_df.to_csv(WISDM_PROC / "train.csv", index=False)
    test_df.to_csv(WISDM_PROC  / "test.csv",  index=False)
    print("  [OK] train.csv saved  shape=%s" % str(train_df.shape))
    print("  [OK] test.csv  saved  shape=%s" % str(test_df.shape))
    return train_df, test_df


# =============================================================================
# MAIN
# =============================================================================
if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("  SECTION 2 - Complete Dataset Pipeline")
    print("=" * 60)

    # --- BRFSS ---
    print("\n### PART 1: BRFSS 2015 ###")
    brfss_csv = find_brfss_csv()
    if brfss_csv is None:
        print("  [SKIP] BRFSS CSV not in raw/ - checking if processed files already exist ...")
        bt = BRFSS_PROC / "train.csv"
        be = BRFSS_PROC / "test.csv"
        if bt.exists() and be.exists():
            print("  [OK] BRFSS processed files already exist - loading for summary.")
            brfss_train = pd.read_csv(bt)
            brfss_test  = pd.read_csv(be)
        else:
            print("  [FAIL] BRFSS CSV not found. Download from Kaggle.")
            brfss_train = brfss_test = None
    else:
        brfss_train, brfss_test = preprocess_brfss(brfss_csv)

    # --- WISDM ---
    print("\n### PART 2: WISDM Smartwatch ###")
    wisdm_root = extract_wisdm()
    if wisdm_root is None:
        print("  [FAIL] Could not extract WISDM dataset.")
        sys.exit(1)
    wisdm_train, wisdm_test = preprocess_wisdm(wisdm_root)
    if wisdm_train is None:
        sys.exit(1)

    # --- Verification ---
    output_files = [
        BRFSS_PROC / "train.csv",
        BRFSS_PROC / "test.csv",
        WISDM_PROC / "train.csv",
        WISDM_PROC / "test.csv",
    ]
    print("\n" + "=" * 60)
    print("  VERIFICATION - Output files")
    print("=" * 60)
    all_ok = True
    for f in output_files:
        if f.exists() and f.stat().st_size > 0:
            print("  [OK]      %s  (%d KB)" % (f.relative_to(ROOT), f.stat().st_size//1024))
        else:
            print("  [MISSING] %s" % f.relative_to(ROOT))
            all_ok = False

    # --- Final Summary ---
    print("\n" + "=" * 60)
    print("  FINAL SUMMARY REPORT")
    print("=" * 60)

    if brfss_train is not None:
        print("\n  1. BRFSS train dataset shape    : %s" % str(brfss_train.shape))
        print("  2. BRFSS test  dataset shape    : %s" % str(brfss_test.shape))
        print("\n  3. BRFSS Diabetes_binary class distribution (train):")
        vc = brfss_train[TARGET_COL].value_counts()
        for cls, cnt in vc.items():
            label = "No Diabetes" if cls == 0.0 else "Diabetes/Prediabetes"
            print("       %.1f  (%s) : %d" % (cls, label, cnt))
    else:
        print("\n  BRFSS: [MISSING] - processed files not found.")

    n_feat    = len(wisdm_train.columns) - 2   # minus subject_id and activity_label
    n_classes = wisdm_train["activity_label"].nunique()

    print("\n  4. WISDM train dataset shape    : %s" % str(wisdm_train.shape))
    print("  5. WISDM test  dataset shape    : %s" % str(wisdm_test.shape))
    print("\n  6. WISDM activity class distribution (train):")
    print(wisdm_train["activity_label"].value_counts().to_string())
    print("\n     Number of WISDM activity classes : %d" % n_classes)
    print("     Number of WISDM sensor features  : %d  (excl. subject_id and label)" % n_feat)

    print("\n  7. Generated files:")
    for f in output_files:
        status = "[OK]" if (f.exists() and f.stat().st_size > 0) else "[MISSING]"
        print("     %s  %s" % (status, f.relative_to(ROOT)))

    if all_ok:
        print("\n  *** Section 2 COMPLETE - all 4 processed files verified ***\n")
    else:
        print("\n  [INCOMPLETE] Some files are missing.\n")
        sys.exit(1)

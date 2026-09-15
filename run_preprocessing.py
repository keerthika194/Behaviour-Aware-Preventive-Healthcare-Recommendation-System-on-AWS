"""
Section 2 Master Runner — Dataset Preprocessing
================================================
Runs both preprocessing scripts in sequence and prints the combined summary.

Usage (from E:\\AWS Project):
    python run_preprocessing.py

Requirements:
    pip install pandas numpy scikit-learn
"""

import subprocess
import sys
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent

BRFSS_SCRIPT  = ROOT / "datasets" / "brfss_diabetes"    / "preprocess.py"
WISDM_SCRIPT  = ROOT / "datasets" / "wisdm_smartwatch"  / "preprocess.py"

def run_script(script_path: pathlib.Path) -> None:
    name = script_path.parent.name
    print(f"\n{'#' * 65}")
    print(f"#  Running: {name}/preprocess.py")
    print(f"{'#' * 65}\n")
    result = subprocess.run(
        [sys.executable, str(script_path)],
        check=False
    )
    if result.returncode != 0:
        print(f"\n  ✘ {name} preprocessing FAILED with exit code {result.returncode}")
        print("  Check the error messages above and ensure:")
        print("  • Required packages are installed: pip install pandas numpy scikit-learn")
        print("  • Raw data files are present in the correct directories")
    else:
        print(f"\n  ✔ {name} preprocessing completed successfully.")

if __name__ == "__main__":
    run_script(BRFSS_SCRIPT)
    run_script(WISDM_SCRIPT)
    print(f"\n{'=' * 65}")
    print("  Section 2 — All preprocessing complete.")
    print(f"{'=' * 65}\n")

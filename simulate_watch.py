#!/usr/bin/env python3
"""
Root-level wrapper for portable_demo/simulate_watch.py
Allows running 'python simulate_watch.py' directly from the repository root.
"""
import sys
import subprocess
from pathlib import Path

def main():
    root_dir = Path(__file__).resolve().parent
    script_path = root_dir / "portable_demo" / "simulate_watch.py"
    
    if not script_path.exists():
        print(f"[ERROR] Cannot locate {script_path}", file=sys.stderr)
        sys.exit(1)
        
    cmd = [sys.executable, str(script_path)] + sys.argv[1:]
    try:
        proc = subprocess.run(cmd)
        sys.exit(proc.returncode)
    except KeyboardInterrupt:
        sys.exit(0)

if __name__ == "__main__":
    main()

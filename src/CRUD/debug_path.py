import sys
import os
from pathlib import Path

# Add project root to sys.path
project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root))

try:
    from src.config import ROOT_DIR
    print(f"ROOT_DIR from config: {ROOT_DIR}")
    print(f"Expected root: {project_root}")
    
    if str(ROOT_DIR) == str(project_root):
        print("✅ ROOT_DIR matches expected project root.")
    else:
        print("❌ ROOT_DIR does NOT match expected project root.")

except Exception as e:
    print(f"Error: {e}")

import os
import subprocess
import sys
from pathlib import Path

APP = Path(__file__).with_name("app.py")

def main():
    cmd = [sys.executable, "-m", "streamlit", "run", str(APP), "--server.headless=false"]
    subprocess.run(cmd, check=False)

if __name__ == "__main__":
    main()

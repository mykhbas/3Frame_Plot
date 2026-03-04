import sys
import subprocess

def install(package):
    subprocess.check_call(
        [sys.executable, "-m", "pip", "install", package]
    )

# รายชื่อ library ที่ต้องใช้
packages = [
    "numpy",
    "pandas",
    "matplotlib",
    "requests",
    "pyserial",
    "mplcyberpunk",
    "seaborn",
    "openpyxl",
    "scikit-learn",

]

for pkg in packages:
    try:
        __import__(pkg)
    except ImportError:
        print(f"Installing {pkg} ...")
        install(pkg)


import subprocess
from pathlib import Path
import sys

BASE = Path(__file__).resolve().parent  # папка py
PY = sys.executable  # текущий интерпретатор, из .venv

commands = [
    [PY, str(BASE / "01_normalize_financial.py")],
    [PY, str(BASE / "02_normalize_prolongations.py")],
    [PY, str(BASE / "03_build_fact.py")],
    [PY, str(BASE / "04_report_department.py")],
    [PY, str(BASE / "05_report_am.py")],
]

for cmd in commands:
    print(" Запуск:", " ".join(cmd))
    result = subprocess.run(cmd)
    if result.returncode != 0:
        print(" ОШИБКА, выполнение остановлено.")
        break
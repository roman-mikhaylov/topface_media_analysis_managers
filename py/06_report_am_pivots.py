import pandas as pd
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent

# Загружаем построчный отчёт по AM
am_path = BASE / "out" / "am_2023.csv"
df = pd.read_csv(am_path)

# На всякий случай приводим тип месяца к int
df["Месяц"] = df["Месяц"].astype(int)

# Коэффициент 1 (пролонгация в первый месяц)
pivot_k1 = df.pivot_table(
    index="AM",
    columns="Месяц",
    values="Коэффицент в первый месяц",
    aggfunc="first"
)

pivot_k1.reset_index(inplace=True)
pivot_k1.columns.name = None  # убираем имя оси колонок

# Коэффициент 2 (пролонгация во второй месяц)
pivot_k2 = df.pivot_table(
    index="AM",
    columns="Месяц",
    values="Коэффицент через месяц",
    aggfunc="first"
)

pivot_k2.reset_index(inplace=True)
pivot_k2.columns.name = None

# Сохраняем в CSV
out_k1 = BASE / "out" / "am_k1_pivot_2023.csv"
out_k2 = BASE / "out" / "am_k2_pivot_2023.csv"

out_k1.parent.mkdir(parents=True, exist_ok=True)
pivot_k1.to_csv(out_k1, index=False, encoding="utf-8-sig")
pivot_k2.to_csv(out_k2, index=False, encoding="utf-8-sig")

print(f"Сводка K1: {out_k1}")
print(f"Сводка K2: {out_k2}")
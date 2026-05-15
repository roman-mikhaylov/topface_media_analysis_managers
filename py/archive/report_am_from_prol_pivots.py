import pandas as pd
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent

MONTH_LABEL_RU = {
    202211: "ноябрь 2022",
    202212: "декабрь 2022",
    202301: "январь 2023",
    202302: "февраль 2023",
    202303: "март 2023",
    202304: "апрель 2023",
    202305: "май 2023",
    202306: "июнь 2023",
    202307: "июль 2023",
    202308: "август 2023",
    202309: "сентябрь 2023",
    202310: "октябрь 2023",
    202311: "ноябрь 2023",
    202312: "декабрь 2023",
    202401: "январь 2024",
    202402: "февраль 2024",
}

# Загружаем построчный отчёт по AM (от prolongations)
am_path = BASE / "out" / "am_from_prol_2023.csv"
df = pd.read_csv(am_path)

df["Месяц"] = df["Месяц"].astype(int)

# Сводка по K1: пролонгация в первый месяц
pivot_k1 = df.pivot_table(
    index="AM",
    columns="Месяц",
    values="Коэффицент в первый месяц",
    aggfunc="first"
)
pivot_k1.reset_index(inplace=True)

pivot_k1.columns.name = None

# Сводка по K2: пролонгация во второй месяц
pivot_k2 = df.pivot_table(
    index="AM",
    columns="Месяц",
    values="Коэффицент через месяц",
    aggfunc="first"
)
pivot_k2.reset_index(inplace=True)
pivot_k2.columns.name = None

# Сохраняем в CSV
out_k1 = BASE / "out" / "am_from_prol_k1_pivot_2023.csv"
out_k2 = BASE / "out" / "am_from_prol_k2_pivot_2023.csv"

out_k1.parent.mkdir(parents=True, exist_ok=True)
pivot_k1.to_csv(out_k1, index=False, encoding="utf-8-sig")
pivot_k2.to_csv(out_k2, index=False, encoding="utf-8-sig")

print(f"K1 по AM (от prolongations): {out_k1}")
print(f"K2 по AM (от prolongations): {out_k2}")
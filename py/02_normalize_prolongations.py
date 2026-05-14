import pandas as pd
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent

df = pd.read_csv(BASE / "data" / "prolongations_raw.csv")

df["month"] = df["month"].astype(str).str.strip().str.lower()

month_map = {
    "ноябрь 2022": 202211,
    "декабрь 2022": 202212,
    "январь 2023": 202301,
    "февраль 2023": 202302,
    "март 2023": 202303,
    "апрель 2023": 202304,
    "май 2023": 202305,
    "июнь 2023": 202306,
    "июль 2023": 202307,
    "август 2023": 202308,
    "сентябрь 2023": 202309,
    "октябрь 2023": 202310,
    "ноябрь 2023": 202311,
    "декабрь 2023": 202312,
    "январь 2024": 202401,
    "февраль 2024": 202402,
}

df["last_month_code"] = df["month"].map(month_map).astype(int)
df = df.rename(columns={"AM": "AM_primary"})

df = df[["id", "AM_primary", "last_month_code"]].drop_duplicates("id")

df.to_csv(BASE / "data" / "prolongations_norm.csv", index=False)
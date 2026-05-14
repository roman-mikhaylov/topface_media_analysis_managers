import pandas as pd
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent

# 1. Читаем raw
df = pd.read_csv(BASE / "data" / "financial_raw.csv")

# Месячные колонки (точно по твоему файлу)
month_cols = [
    "Ноябрь 2022",
    "Декабрь 2022",
    "Январь 2023",
    "Февраль 2023",
    "Март 2023",
    "Апрель 2023",
    "Май 2023",
    "Июнь 2023",
    "Июль 2023",
    "Август 2023",
    "Сентябрь 2023",
    "Октябрь 2023",
    "Ноябрь 2023",
    "Декабрь 2023",
    "Январь 2024",
    "Февраль 2024",
]

# 2. Флаг наличия 'стоп' / 'end' по id
stop_mask = df[month_cols].astype(str).apply(
    lambda s: s.str.lower().str.contains("стоп") | s.str.lower().str.contains("end")
)
ids_with_stop = df.loc[stop_mask.any(axis=1), "id"].unique()

# 3. Переводим в long
long = df.melt(
    id_vars=["id", "Account", "Причина дубля"],
    value_vars=month_cols,
    var_name="month_name",
    value_name="raw_value",
)

# 4. Разбор чисел и спец-меток
# нормализуем строку
s = long["raw_value"].astype(str).str.strip()

# флаги
long["is_stop"] = s.str.lower().str.contains("стоп") | s.str.lower().str.contains("end")
long["is_v_nol"] = s.str.lower().str.contains("в ноль")

# числовая часть (без пробелов и с точкой)
num = (
    s.str.replace(" ", "", regex=False)
     .str.replace("\u00a0", "", regex=False)  # неразрывный пробел
     .str.replace(",", ".", regex=False)
)

# то, что реально можно парсить как число
long["amount"] = pd.to_numeric(num, errors="coerce")

# 5. Агрегируем по id + month_name: сумма чисел, флаги
agg = (
    long.groupby(["id", "Account", "month_name"], as_index=False)
        .agg(
            amount=("amount", "sum"),
            any_stop=("is_stop", "any"),
            any_v_nol=("is_v_nol", "any"),
        )
)

# 6. Помечаем id с 'стоп'
agg["has_stop_id"] = agg["id"].isin(ids_with_stop)

# 7. Мапим month_name -> month_code (ГГГГММ)
month_map = {
    "Ноябрь 2022": 202211,
    "Декабрь 2022": 202212,
    "Январь 2023": 202301,
    "Февраль 2023": 202302,
    "Март 2023": 202303,
    "Апрель 2023": 202304,
    "Май 2023": 202305,
    "Июнь 2023": 202306,
    "Июль 2023": 202307,
    "Август 2023": 202308,
    "Сентябрь 2023": 202309,
    "Октябрь 2023": 202310,
    "Ноябрь 2023": 202311,
    "Декабрь 2023": 202312,
    "Январь 2024": 202401,
    "Февраль 2024": 202402,
}
agg["month_code"] = agg["month_name"].map(month_map).astype(int)

# 8. Сохраняем нормализованный long
out_cols = ["id", "Account", "month_code", "amount", "any_stop", "any_v_nol", "has_stop_id"]
agg[out_cols].to_csv(BASE / "data" / "financial_long_clean.csv", index=False)
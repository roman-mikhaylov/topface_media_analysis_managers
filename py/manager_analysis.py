import pandas as pd
from pathlib import Path

# Корень проекта (папка AD_test), если скрипт лежит в py/
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
OUT_DIR = BASE_DIR / "out"
OUT_DIR.mkdir(exist_ok=True)

# -----------------------------
# 1. Загрузка и нормализация финансовых данных
# -----------------------------

# 1.1. Чтение исходных финансовых данных
financial = pd.read_csv(DATA_DIR / "financial_raw.csv")

# Список колонок-месяцев строго по структуре файла
MONTH_COLS = [
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

# 1.2. Находим id, где где‑нибудь стоит 'стоп' или 'end' — такие договоры исключаем
s_months = financial[MONTH_COLS].astype(str)
stop_mask = s_months.apply(
    lambda s: s.str.lower().str.contains("стоп") | s.str.lower().str.contains("end")
)
ids_with_stop = financial.loc[stop_mask.any(axis=1), "id"].unique()

# 1.3. wide -> long
long_fin = financial.melt(
    id_vars=["id", "Account", "Причина дубля"],
    value_vars=MONTH_COLS,
    var_name="month_name",
    value_name="raw_value",
)

# 1.4. Выделяем числовые суммы и спец‑метки ('стоп', 'в ноль')
s = long_fin["raw_value"].astype(str).str.strip()

long_fin["is_stop"] = s.str.lower().str.contains("стоп") | s.str.lower().str.contains(
    "end"
)
long_fin["is_v_nol"] = s.str.lower().str.contains("в ноль")

num = (
    s.str.replace(" ", "", regex=False)
    .str.replace("\u00a0", "", regex=False)  # неразрывный пробел
    .str.replace(",", ".", regex=False)
)
long_fin["amount"] = pd.to_numeric(num, errors="coerce")

# 1.5. Агрегация по id+месяц (суммируем дубли, собираем флаги)
agg_fin = (
    long_fin.groupby(["id", "Account", "month_name"], as_index=False)
    .agg(
        amount=("amount", "sum"),
        any_stop=("is_stop", "any"),
        any_v_nol=("is_v_nol", "any"),
    )
)

# Флаг: у id вообще был 'стоп' где-то
agg_fin["has_stop_id"] = agg_fin["id"].isin(ids_with_stop)

# 1.6. Маппинг month_name -> числовой month_code (ГГГГММ)
MONTH_MAP = {
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

agg_fin["month_code"] = agg_fin["month_name"].map(MONTH_MAP).astype(int)

# Итог: long-факт по деньгам
financial_long_clean = agg_fin[
    ["id", "Account", "month_code", "amount", "any_stop", "any_v_nol", "has_stop_id"]
].copy()

financial_long_clean.to_csv(DATA_DIR / "financial_long_clean.csv", index=False)

# -----------------------------
# 2. Нормализация prolongations
# -----------------------------

prol_raw = pd.read_csv(DATA_DIR / "prolongations_raw.csv")

# Приводим текст месяца к нижнему регистру и убираем пробелы
prol_raw["month"] = prol_raw["month"].astype(str).str.strip().str.lower()

MONTH_MAP_PROL = {
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

prol_raw["last_month_code"] = prol_raw["month"].map(MONTH_MAP_PROL).astype(int)
prol_raw = prol_raw.rename(columns={"AM": "AM_primary"})

# На случай дублей по id берём одну строку
prolongations_norm = prol_raw[["id", "AM_primary", "last_month_code"]].drop_duplicates(
    "id"
)

prolongations_norm.to_csv(DATA_DIR / "prolongations_norm.csv", index=False)

# -----------------------------
# 3. Факт‑таблица для расчёта по prolongations
# -----------------------------

# Берём только договоры без стопа
fin_ok = financial_long_clean.loc[~financial_long_clean["has_stop_id"]].copy()

# Склейка: у каждой строчки по id+месяц есть AM и last_month_code
fact = fin_ok.merge(prolongations_norm, on="id", how="inner")
fact["month_code"] = fact["month_code"].astype(int)
fact["last_month_code"] = fact["last_month_code"].astype(int)

fact.to_csv(DATA_DIR / "fact_from_prol.csv", index=False)

# -----------------------------
# 4. Расчёт K1 и K2 по отделу (от prolongations)
# -----------------------------

YEAR = 2023
min_m = YEAR * 100 + 1  # 202301
max_m = YEAR * 100 + 12  # 202312

rows_dep = []

for M in range(min_m, max_m + 1):
    prev1 = M - 1  # месяц окончания для пролонгации в первый месяц
    prev2 = M - 2  # месяц окончания для пролонгации во второй месяц

    # --- K1: пролонгация в первый месяц после окончания ---
    # База: договоры, чей last_month_code = prev1
    base1_ids = fact.loc[fact["last_month_code"] == prev1, "id"].unique()

    # Сумма базы: отгрузка в месяц окончания
    base1_sum = fact.loc[
        (fact["id"].isin(base1_ids)) & (fact["month_code"] == prev1), "amount"
    ].sum()

    # Факт K1: отгрузка в первый месяц после окончания (M), strictly > 0
    fact1_sum = fact.loc[
        (fact["id"].isin(base1_ids))
        & (fact["month_code"] == M)
        & (fact["amount"] > 0),
        "amount",
    ].sum()

    # --- K2: пролонгация во второй месяц после окончания ---
    # Кандидаты: договоры, чей last_month_code = prev2
    cand2_ids = fact.loc[fact["last_month_code"] == prev2, "id"].unique()

    # Первый месяц после окончания для них
    first_after = prev2 + 1

    # Смотрим, кто имеет положительную отгрузку в первый месяц после окончания
    first_after_amounts = fact.loc[
        (fact["id"].isin(cand2_ids)) & (fact["month_code"] == first_after),
        ["id", "amount"],
    ]
    ids_with_first_pos = first_after_amounts.loc[
        first_after_amounts["amount"] > 0, "id"
    ].unique()

    # База K2: только те id, у кого НЕТ отгрузки в первый месяц после окончания
    base2_ids = [i for i in cand2_ids if i not in ids_with_first_pos]

    # Сумма базы K2: отгрузка в месяц окончания prev2
    base2_sum = fact.loc[
        (fact["id"].isin(base2_ids)) & (fact["month_code"] == prev2), "amount"
    ].sum()

    # Факт K2: отгрузка во второй месяц после окончания (M)
    fact2_sum = fact.loc[
        (fact["id"].isin(base2_ids))
        & (fact["month_code"] == M)
        & (fact["amount"] > 0),
        "amount",
    ].sum()

    K1 = fact1_sum / base1_sum if base1_sum > 0 else 0
    K2 = fact2_sum / base2_sum if base2_sum > 0 else 0

    rows_dep.append(
        {
            "Месяц": M,
            "к пролонгации первый месяц": base1_sum,
            "пролонгировано в первый месяц": fact1_sum,
            "Коэффицент в первый месяц": K1,
            "к пролонгации через месяц": base2_sum,
            "пролонгировано через месяц": fact2_sum,
            "Коэффицент через месяц": K2,
        }
    )

dept_df = pd.DataFrame(rows_dep)
dept_df = dept_df[
    (dept_df["к пролонгации первый месяц"] > 0)
    | (dept_df["к пролонгации через месяц"] > 0)
].sort_values("Месяц")

dept_out = OUT_DIR / "department_from_prol_2023.csv"
dept_df.to_csv(dept_out, index=False, encoding="utf-8-sig")
print(f"[DEPARTMENT] saved: {dept_out}")

# -----------------------------
# 5. Расчёт K1 и K2 по AM (от prolongations)
# -----------------------------

ams = fact["AM_primary"].dropna().unique()
rows_am = []

for am in ams:
    fact_am = fact.loc[fact["AM_primary"] == am]

    for M in range(min_m, max_m + 1):
        prev1 = M - 1
        prev2 = M - 2

        # --- K1 для конкретного AM ---
        base1_ids = fact_am.loc[fact_am["last_month_code"] == prev1, "id"].unique()
        base1_sum = fact_am.loc[
            (fact_am["id"].isin(base1_ids)) & (fact_am["month_code"] == prev1),
            "amount",
        ].sum()
        fact1_sum = fact_am.loc[
            (fact_am["id"].isin(base1_ids))
            & (fact_am["month_code"] == M)
            & (fact_am["amount"] > 0),
            "amount",
        ].sum()

        # --- K2 для конкретного AM ---
        cand2_ids = fact_am.loc[fact_am["last_month_code"] == prev2, "id"].unique()
        first_after = prev2 + 1

        first_after_amounts = fact_am.loc[
            (fact_am["id"].isin(cand2_ids))
            & (fact_am["month_code"] == first_after),
            ["id", "amount"],
        ]
        ids_with_first_pos = first_after_amounts.loc[
            first_after_amounts["amount"] > 0, "id"
        ].unique()

        base2_ids = [i for i in cand2_ids if i not in ids_with_first_pos]
        base2_sum = fact_am.loc[
            (fact_am["id"].isin(base2_ids)) & (fact_am["month_code"] == prev2),
            "amount",
        ].sum()
        fact2_sum = fact_am.loc[
            (fact_am["id"].isin(base2_ids))
            & (fact_am["month_code"] == M)
            & (fact_am["amount"] > 0),
            "amount",
        ].sum()

        K1 = fact1_sum / base1_sum if base1_sum > 0 else 0
        K2 = fact2_sum / base2_sum if base2_sum > 0 else 0

        rows_am.append(
            {
                "AM": am,
                "Месяц": M,
                "к пролонгации первый месяц": base1_sum,
                "пролонгировано в первый месяц": fact1_sum,
                "Коэффицент в первый месяц": K1,
                "к пролонгации через месяц": base2_sum,
                "пролонгировано через месяц": fact2_sum,
                "Коэффицент через месяц": K2,
            }
        )

am_df = pd.DataFrame(rows_am)
am_df = am_df[
    (am_df["к пролонгации первый месяц"] > 0)
    | (am_df["к пролонгации через месяц"] > 0)
].sort_values(["AM", "Месяц"])

am_out = OUT_DIR / "am_from_prol_2023.csv"
am_df.to_csv(am_out, index=False, encoding="utf-8-sig")
print(f"[AM DETAIL] saved: {am_out}")

# -----------------------------
# 6. Пивоты K1/K2 по AM
# -----------------------------

pivot_k1 = am_df.pivot_table(
    index="AM",
    columns="Месяц",
    values="Коэффицент в первый месяц",
    aggfunc="first",
).reset_index()
pivot_k1.columns.name = None

pivot_k2 = am_df.pivot_table(
    index="AM",
    columns="Месяц",
    values="Коэффицент через месяц",
    aggfunc="first",
).reset_index()
pivot_k2.columns.name = None

k1_out = OUT_DIR / "am_from_prol_k1_pivot_2023.csv"
k2_out = OUT_DIR / "am_from_prol_k2_pivot_2023.csv"

pivot_k1.to_csv(k1_out, index=False, encoding="utf-8-sig")
pivot_k2.to_csv(k2_out, index=False, encoding="utf-8-sig")

print(f"[AM K1 PIVOT] saved: {k1_out}")
print(f"[AM K2 PIVOT] saved: {k2_out}")
import pandas as pd
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent

fact = pd.read_csv(BASE / "data" / "fact_projects.csv")

# работаем только с 2023 годом
YEAR = 2023
min_m = YEAR * 100 + 1   # 202301
max_m = YEAR * 100 + 12  # 202312

# только строки в периоде наблюдения
fact["month_code"] = fact["month_code"].astype(int)
fact["last_real_month"] = fact["last_real_month"].astype(int)

rows = []

for M in sorted(fact["month_code"].unique()):
    if not (min_m <= M <= max_m):
        continue

    prev1 = M - 1
    prev2 = M - 2

    # --- K1: пролонгация в первый месяц ---
    # база: проекты, чей last_real_month == prev1
    base1_ids = fact.loc[fact["last_real_month"] == prev1, "id"].unique()

    base1_sum = fact.loc[
        (fact["id"].isin(base1_ids)) &
        (fact["month_code"] == prev1),
        "amount"
    ].sum()

    fact1_sum = fact.loc[
        (fact["id"].isin(base1_ids)) &
        (fact["month_code"] == M) &
        (fact["amount"] > 0),
        "amount"
    ].sum()

    # --- K2: пролонгация во второй месяц ---
    # кандидаты: last_real_month == prev2
    cand2_ids = fact.loc[fact["last_real_month"] == prev2, "id"].unique()

    # среди них выбираем тех, кто в M-1 не пролонгировался (отгрузка в M-1 == 0)
    prev1_amounts = fact.loc[
        (fact["id"].isin(cand2_ids)) &
        (fact["month_code"] == prev1),
        ["id", "amount"]
    ]

    zero_prev1_ids = prev1_amounts.loc[
        prev1_amounts["amount"] == 0,
        "id"
    ].unique()

    base2_ids = zero_prev1_ids

    base2_sum = fact.loc[
        (fact["id"].isin(base2_ids)) &
        (fact["month_code"] == prev2),
        "amount"
    ].sum()

    fact2_sum = fact.loc[
        (fact["id"].isin(base2_ids)) &
        (fact["month_code"] == M) &
        (fact["amount"] > 0),
        "amount"
    ].sum()

    K1 = fact1_sum / base1_sum if base1_sum > 0 else 0
    K2 = fact2_sum / base2_sum if base2_sum > 0 else 0

    rows.append({
        "Месяц": M,
        "к пролонгации первый месяц": base1_sum,
        "пролонгировано в первый месяц": fact1_sum,
        "Коэффицент в первый месяц": K1,
        "к пролонгации через месяц": base2_sum,
        "пролонгировано через месяц": fact2_sum,
        "Коэффицент через месяц": K2,
    })

df_dep = pd.DataFrame(rows).sort_values("Месяц")

df_dep.to_csv(BASE / "out" / "department_2023.csv", index=False)
print(df_dep)
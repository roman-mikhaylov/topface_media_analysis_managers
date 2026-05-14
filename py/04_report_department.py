import pandas as pd
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent

fact = pd.read_csv(BASE / "data" / "fact_projects.csv")

fact["month_code"] = fact["month_code"].astype(int)
fact["last_real_month"] = fact["last_real_month"].astype(int)

YEAR = 2023
min_m = YEAR * 100 + 1
max_m = YEAR * 100 + 12

rows = []

for M in range(min_m, max_m + 1):
    prev1 = M - 1
    prev2 = M - 2

    # --- K1: пролонгация в первый месяц ---
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
    cand2_ids = fact.loc[fact["last_real_month"] == prev2, "id"].unique()

    prev1_amounts = fact.loc[
        (fact["id"].isin(cand2_ids)) &
        (fact["month_code"] == prev1),
        ["id", "amount"]
    ]

    ids_with_prev1_pos = prev1_amounts.loc[
        prev1_amounts["amount"] > 0,
        "id"
    ].unique()

    base2_ids = [i for i in cand2_ids if i not in ids_with_prev1_pos]

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

df_dep = pd.DataFrame(rows)

df_dep = df_dep[
    (df_dep["к пролонгации первый месяц"] > 0) |
    (df_dep["к пролонгации через месяц"] > 0)
].sort_values("Месяц")

out_path = BASE / "out" / "department_2023.csv"
out_path.parent.mkdir(parents=True, exist_ok=True)
df_dep.to_csv(out_path, index=False, encoding="utf-8-sig")
print(f"Отдел: сохранено {len(df_dep)} строк в {out_path}")
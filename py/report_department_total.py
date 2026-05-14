
import pandas as pd
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent

# 1. Загружаем нормализованные данные
fin = pd.read_csv(BASE / "data" / "financial_long_clean.csv")
prol = pd.read_csv(BASE / "data" / "prolongations_norm.csv")

# fin: id, Account, month_code, amount, any_stop, any_v_nol, has_stop_id
# prol: id, AM_primary, last_month_code

# 2. Убираем проекты со стопом
fin_ok = fin.loc[~fin["has_stop_id"]].copy()

# 3. Определяем фактический последний месяц реализации по каждому id
def get_last_real_month(group: pd.DataFrame) -> int:
    g = group.sort_values("month_code")
    pos = g.loc[g["amount"] > 0, "month_code"]
    if not pos.empty:
        return int(pos.max())
    return int(g["month_code"].max())

last_real = (
    fin_ok.groupby("id", as_index=False)
          .apply(get_last_real_month)
          .rename(columns={None: "last_real_month"})
)

# 4. Собираем факт-таблицу
fact = (
    fin_ok.merge(last_real, on="id", how="left")
          .merge(prol, on="id", how="left")
)

fact["month_code"] = fact["month_code"].astype(int)
fact["last_real_month"] = fact["last_real_month"].astype(int)

YEAR = 2023
min_m = YEAR * 100 + 1   # 202301
max_m = YEAR * 100 + 12  # 202312

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

df_dep.to_csv(BASE / "out" / "department_2023_total.csv", index=False)
print(df_dep)
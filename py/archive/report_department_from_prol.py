import pandas as pd
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent

# Берём уже нормализованные long-данные и prolongations_norm
fin = pd.read_csv(BASE / "data" / "financial_long_clean.csv")
prol = pd.read_csv(BASE / "data" / "prolongations_norm.csv")

# Убираем проекты со стопом
fin_ok = fin.loc[~fin["has_stop_id"]].copy()

# Склеиваем, чтобы у каждого id был last_month_code
fact = fin_ok.merge(prol, on="id", how="inner")

fact["month_code"] = fact["month_code"].astype(int)
fact["last_month_code"] = fact["last_month_code"].astype(int)

YEAR = 2023
min_m = YEAR * 100 + 1
max_m = YEAR * 100 + 12

rows = []

for M in range(min_m, max_m + 1):
    prev1 = M - 1   # месяц окончания для K1
    prev2 = M - 2   # месяц окончания для K2

    # --- K1: пролонгация в первый месяц после окончания (M = last_month + 1) ---

    # проекты, окончившиеся в prev1
    base1_ids = fact.loc[fact["last_month_code"] == prev1, "id"].unique()

    # база: сумма отгрузки в месяц окончания (prev1)
    base1_sum = fact.loc[
        (fact["id"].isin(base1_ids)) &
        (fact["month_code"] == prev1),
        "amount"
    ].sum()

    # факт: отгрузка в первый месяц после окончания (M)
    fact1_sum = fact.loc[
        (fact["id"].isin(base1_ids)) &
        (fact["month_code"] == M) &
        (fact["amount"] > 0),
        "amount"
    ].sum()

    # --- K2: пролонгация во второй месяц после окончания (M = last_month + 2) ---

    # кандидаты: проекты, окончившиеся в prev2
    cand2_ids = fact.loc[fact["last_month_code"] == prev2, "id"].unique()

    # среди них оставляем тех, у кого НЕТ отгрузки в первый месяц после окончания (prev2 + 1)
    first_after = prev2 + 1
    first_after_amounts = fact.loc[
        (fact["id"].isin(cand2_ids)) &
        (fact["month_code"] == first_after),
        ["id", "amount"]
    ]

    ids_with_first_pos = first_after_amounts.loc[
        first_after_amounts["amount"] > 0,
        "id"
    ].unique()

    base2_ids = [i for i in cand2_ids if i not in ids_with_first_pos]

    # база K2: сумма в месяц окончания (prev2)
    base2_sum = fact.loc[
        (fact["id"].isin(base2_ids)) &
        (fact["month_code"] == prev2),
        "amount"
    ].sum()

    # факт K2: сумма во второй месяц после окончания (M)
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

out_path = BASE / "out" / "department_from_prol_2023.csv"
out_path.parent.mkdir(parents=True, exist_ok=True)
df_dep.to_csv(out_path, index=False, encoding="utf-8-sig")
print(f"Отдел (от prolongations): сохранено {len(df_dep)} строк в {out_path}")
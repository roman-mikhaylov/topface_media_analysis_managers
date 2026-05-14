import pandas as pd
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent

fact = pd.read_csv(BASE / "data" / "fact_projects.csv")

fact["month_code"] = fact["month_code"].astype(int)
fact["last_real_month"] = fact["last_real_month"].astype(int)

YEAR = 2023
min_m = YEAR * 100 + 1
max_m = YEAR * 100 + 12

ams = fact["AM_primary"].dropna().unique()
rows = []

for am in ams:
    fact_am = fact.loc[fact["AM_primary"] == am]

    for M in range(min_m, max_m + 1):
        prev1 = M - 1
        prev2 = M - 2

        # K1 для этого AM
        base1_ids = fact_am.loc[fact_am["last_real_month"] == prev1, "id"].unique()

        base1_sum = fact_am.loc[
            (fact_am["id"].isin(base1_ids)) &
            (fact_am["month_code"] == prev1),
            "amount"
        ].sum()

        fact1_sum = fact_am.loc[
            (fact_am["id"].isin(base1_ids)) &
            (fact_am["month_code"] == M) &
            (fact_am["amount"] > 0),
            "amount"
        ].sum()

        # K2 для этого AM
        cand2_ids = fact_am.loc[fact_am["last_real_month"] == prev2, "id"].unique()

        prev1_amounts = fact_am.loc[
            (fact_am["id"].isin(cand2_ids)) &
            (fact_am["month_code"] == prev1),
            ["id", "amount"]
        ]

        ids_with_prev1_pos = prev1_amounts.loc[
            prev1_amounts["amount"] > 0,
            "id"
        ].unique()

        base2_ids = [i for i in cand2_ids if i not in ids_with_prev1_pos]

        base2_sum = fact_am.loc[
            (fact_am["id"].isin(base2_ids)) &
            (fact_am["month_code"] == prev2),
            "amount"
        ].sum()

        fact2_sum = fact_am.loc[
            (fact_am["id"].isin(base2_ids)) &
            (fact_am["month_code"] == M) &
            (fact_am["amount"] > 0),
            "amount"
        ].sum()

        K1 = fact1_sum / base1_sum if base1_sum > 0 else 0
        K2 = fact2_sum / base2_sum if base2_sum > 0 else 0

        rows.append({
            "AM": am,
            "Месяц": M,
            "к пролонгации первый месяц": base1_sum,
            "пролонгировано в первый месяц": fact1_sum,
            "Коэффицент в первый месяц": K1,
            "к пролонгации через месяц": base2_sum,
            "пролонгировано через месяц": fact2_sum,
            "Коэффицент через месяц": K2,
        })

df_am = pd.DataFrame(rows)

df_am = df_am[
    (df_am["к пролонгации первый месяц"] > 0) |
    (df_am["к пролонгации через месяц"] > 0)
].sort_values(["AM", "Месяц"])

out_path = BASE / "out" / "am_2023.csv"
out_path.parent.mkdir(parents=True, exist_ok=True)
df_am.to_csv(out_path, index=False, encoding="utf-8-sig")
print(f"AM: сохранено {len(df_am)} строк в {out_path}")
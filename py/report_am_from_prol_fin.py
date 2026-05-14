import pandas as pd
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent

# Человекочитаемые подписи месяцев
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

# Нормализованные данные
fin = pd.read_csv(BASE / "data" / "financial_long_clean.csv")
prol = pd.read_csv(BASE / "data" / "prolongations_norm.csv")

# Убираем проекты со стопом
fin_ok = fin.loc[~fin["has_stop_id"]].copy()

# Склейка: у каждого id есть AM_primary и last_month_code
fact = fin_ok.merge(prol, on="id", how="inner")

fact["month_code"] = fact["month_code"].astype(int)
fact["last_month_code"] = fact["last_month_code"].astype(int)

YEAR = 2023
min_m = YEAR * 100 + 1
max_m = YEAR * 100 + 12

ams = fact["AM_primary"].dropna().unique()
rows = []

for am in ams:
    fact_am = fact.loc[fact["AM_primary"] == am]

    for M in range(min_m, max_m + 1):
        prev1 = M - 1   # месяц окончания для K1
        prev2 = M - 2   # месяц окончания для K2

        # --- K1: пролонгация в первый месяц после окончания ---

        base1_ids = fact_am.loc[
            fact_am["last_month_code"] == prev1, "id"
        ].unique()

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

        # --- K2: пролонгация во второй месяц после окончания ---

        cand2_ids = fact_am.loc[
            fact_am["last_month_code"] == prev2, "id"
        ].unique()

        first_after = prev2 + 1
        first_after_amounts = fact_am.loc[
            (fact_am["id"].isin(cand2_ids)) &
            (fact_am["month_code"] == first_after),
            ["id", "amount"]
        ]

        ids_with_first_pos = first_after_amounts.loc[
            first_after_amounts["amount"] > 0,
            "id"
        ].unique()

        base2_ids = [i for i in cand2_ids if i not in ids_with_first_pos]

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
            "Период": MONTH_LABEL_RU.get(M, str(M)),  # добавили человекочитаемый месяц
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

out_path = BASE / "out" / "am_from_prol_2023.csv"
out_path.parent.mkdir(parents=True, exist_ok=True)
df_am.to_csv(out_path, index=False, encoding="utf-8-sig")
print(f"AM (от prolongations): сохранено {len(df_am)} строк в {out_path}")
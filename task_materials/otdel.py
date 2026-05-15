import pandas as pd

# 1. Загружаем данные
financial = pd.read_csv("financial_data.csv")      # wide-таблица по месяцам
prolong = pd.read_csv("prolongations.csv")         # id, month (месяц завершения), AM

# 2. Маппинг названий столбцов-месяцев в коды ГГГГММ
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

month_cols = list(month_map.keys())

# 3. Разворачиваем financial_data в формат id–месяц–сумма
fin_long = (
    financial
    .melt(
        id_vars=["id", "Account"],
        value_vars=month_cols,
        var_name="month_name",
        value_name="amount",
    )
)

fin_long["month_code"] = fin_long["month_name"].map(month_map)

# Жёстко приводим amount к float: заменяем запятые, пробелы, нечисловые → NaN → 0.0
fin_long["amount"] = (
    fin_long["amount"]
    .astype(str)
    .str.replace(",", ".", regex=False)        # если вдруг есть запятые
    .str.replace(" ", "", regex=False)         # убираем пробелы-разделители тысяч
)

#fin_long["amount"] = pd.to_numeric(fin_long["amount"], errors="coerce").fillna(0.0)

#fin_long["month_code"] = fin_long["month_name"].map(month_map)
#fin_long["amount"] = fin_long["amount"].fillna(0.0)

# 4. Присоединяем инфо о последнем месяце (prolongations)
# В prolongations: month = последний месяц реализации (в формате ГГГГММ или ГГГГ-ММ/ГГГГ.ММ)
prolong = prolong.rename(columns={"month": "last_code", "AM": "AM_primary"})

# Приводим last_code к числу ГГГГММ
prolong["last_code"] = (
    prolong["last_code"]
    .astype(str)
    .str.replace(r"\D", "", regex=True)   # убираем все нецифры
    .astype(int)
)

projects = prolong[["id", "AM_primary", "last_code"]].drop_duplicates("id")

# 5. Объединяем помесячные суммы с информацией о проекте
fin_proj = fin_long.merge(projects, on="id", how="inner")

# 6. Список месяцев отчёта: только 2023 год
report_months = [m for m in sorted(fin_proj["month_code"].unique())
                 if 202301 <= m <= 202312]

rows = []

for M in report_months:
    prev1 = M - 1     # месяц M-1 в коде ГГГГММ (для K1)
    prev2 = M - 2     # месяц M-2 в коде ГГГГММ (для K2)

    # --- K1: пролонгация в первый месяц ---

    # База: проекты, завершившиеся в M-1 (last_code = prev1), берём сумму за prev1
    base1_ids = projects.loc[projects["last_code"] == prev1, "id"]

    base1 = fin_proj.loc[
        (fin_proj["id"].isin(base1_ids)) &
        (fin_proj["month_code"] == prev1),
        "amount"
    ].sum()

    # Факт: те же id, отгрузка в месяц M > 0
    fact1 = fin_proj.loc[
        (fin_proj["id"].isin(base1_ids)) &
        (fin_proj["month_code"] == M) &
        (fin_proj["amount"] > 0),
        "amount"
    ].sum()

    # --- K2: пролонгация во второй месяц ---

    # База: проекты, завершившиеся в M-2 (last_code = prev2),
    # у которых НЕТ отгрузки в M-1
    base2_ids = projects.loc[projects["last_code"] == prev2, "id"]

    # Смотрим их суммы в M-1
    prev1_amounts = fin_proj.loc[
        (fin_proj["id"].isin(base2_ids)) &
        (fin_proj["month_code"] == prev1),
        ["id", "amount"]
    ]

    # id, у которых amount в M-1 == 0
    base2_ids_final = prev1_amounts.loc[prev1_amounts["amount"] == 0, "id"].unique()

    # База: сумма за M-2 по этим id
    base2 = fin_proj.loc[
        (fin_proj["id"].isin(base2_ids_final)) &
        (fin_proj["month_code"] == prev2),
        "amount"
    ].sum()

    # Факт: сумма за M по этим id, где amount > 0
    fact2 = fin_proj.loc[
        (fin_proj["id"].isin(base2_ids_final)) &
        (fin_proj["month_code"] == M) &
        (fin_proj["amount"] > 0),
        "amount"
    ].sum()

    K1 = fact1 / base1 if base1 > 0 else 0
    K2 = fact2 / base2 if base2 > 0 else 0

    rows.append({
        "Месяц": M,
        "к пролонгации первый месяц": base1,
        "пролонгировано в первый месяц": fact1,
        "Коэффицент в первый месяц": K1,
        "к пролонгации через месяц": base2,
        "пролонгировано через месяц": fact2,
        "Коэффицент через месяц": K2,
    })

# 7. Формируем итоговый DataFrame и сохраняем
df_department = pd.DataFrame(rows).sort_values("Месяц")

# Сохраняем в CSV для загрузки в лист «Весь отдел»
df_department.to_csv("metrics_department_2023.csv", index=False)
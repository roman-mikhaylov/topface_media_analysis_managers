import pandas as pd
from pathlib import Path

# Базовый путь к корню проекта (папка AD_test)
BASE = Path(__file__).resolve().parent.parent

# Пути к исходным данным
prolongations_path = BASE / "data" / "prolongations_raw.csv"      #  поправь имя, если другое
financial_path = BASE / "data" / "financial_raw.csv"         # или financial_raw.csv

# Загружаем данные
prolongations = pd.read_csv(prolongations_path)
financial = pd.read_csv(financial_path)

# Убираем дубликаты строк по id в financial_data (если есть)
financial = financial.drop_duplicates(subset=["id"])

# Месячные колонки (всё, кроме служебных)
month_columns = [
    col
    for col in financial.columns
    if col not in ["id", "Причина дубля", "Account"]
]
months = sorted(month_columns)

# Агрегируем фин. данные по id (суммируем по дублям)
financial_agg = financial.groupby("id").agg({m: "sum" for m in months}).reset_index()

# Строим словарь: id -> {month -> value}
financial_dict = {
    row["id"]: {m: row[m] for m in months}
    for _, row in financial_agg.iterrows()
}

# Сюда будем складывать все посчитанные позиции
rows = []

for current_month in months:
    current_idx = months.index(current_month)

    # Объединяем prolongations с фин. данными
    merged = pd.merge(prolongations, financial, on="id", how="left")

    # Предполагаем, что поле month в prolongations совпадает по названию с колонками месяцев
    projects_in_month = merged[merged["month"] == current_month]

    prolong_first_month = []
    prolong_second_month = []

    for _, proj in projects_in_month.iterrows():
        proj_id = proj["id"]
        manager = proj["AM"]
        last_month = proj["month"]

        fin_data = financial_dict.get(proj_id, {})

        # Сумма в последний месяц реализации
        sum_last_month = fin_data.get(last_month, 0)

        # Сумма в текущем месяце (первая пролонгация)
        sum_curr_month = fin_data.get(current_month, 0)

        # Следующий месяц (для второй пролонгации)
        next_month_idx = current_idx + 1
        next_month = months[next_month_idx] if next_month_idx < len(months) else None
        sum_next_month = fin_data.get(next_month, 0) if next_month else 0

        coeff_first = sum_curr_month / sum_last_month if sum_last_month != 0 else None
        coeff_second = (
            sum_next_month / sum_last_month
            if sum_last_month != 0 and sum_next_month != 0
            else None
        )

        if coeff_first is not None:
            prolong_first_month.append(
                {"manager": manager, "month": current_month, "coefficient": coeff_first}
            )

        if coeff_second is not None:
            prolong_second_month.append(
                {"manager": manager, "month": current_month, "coefficient": coeff_second}
            )

    df_first = pd.DataFrame(prolong_first_month)
    df_second = pd.DataFrame(prolong_second_month)

    # Менеджерские коэффициенты
    if not df_first.empty:
        for _, row in df_first.iterrows():
            rows.append(
                {
                    "month": row["month"],
                    "manager": row["manager"],
                    "type": "Первый месяц",
                    "coefficient": row["coefficient"],
                }
            )

    if not df_second.empty:
        for _, row in df_second.iterrows():
            rows.append(
                {
                    "month": row["month"],
                    "manager": row["manager"],
                    "type": "Второй месяц",
                    "coefficient": row["coefficient"],
                }
            )

    # Общий показатель отдела (средний по всем менеджерам)
    if not df_first.empty:
        dept_first = df_first["coefficient"].mean()
        rows.append(
            {
                "month": current_month,
                "manager": "Отдел",
                "type": "Первый месяц",
                "coefficient": dept_first,
            }
        )

    if not df_second.empty:
        dept_second = df_second["coefficient"].mean()
        rows.append(
            {
                "month": current_month,
                "manager": "Отдел",
                "type": "Второй месяц",
                "coefficient": dept_second,
            }
        )

# Собираем всё в DataFrame
df_res = pd.DataFrame(rows)

# Сохраняем в CSV
out_path = BASE / "out" / "analitk_metrics.csv"
out_path.parent.mkdir(parents=True, exist_ok=True)
df_res.to_csv(out_path, index=False, encoding="utf-8-sig")

print(f"Сохранено {len(df_res)} строк в {out_path}")
print(df_res)
import pandas as pd
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
OUT = BASE / "out"
OUT.mkdir(exist_ok=True)

# 1. Отчёт по отделу (department_from_prol_2023.csv)
dept = pd.read_csv(OUT / "department_from_prol_2023.csv")

dept["ReportType"] = "Department"
dept["AM"] = "Отдел"

dept_cols = [
    "ReportType",
    "AM",
    "Месяц",
    "Период",  # этой колонки может ещё не быть
    "к пролонгации первый месяц",
    "пролонгировано в первый месяц",
    "Коэффицент в первый месяц",
    "к пролонгации через месяц",
    "пролонгировано через месяц",
    "Коэффицент через месяц",
]

# если какой‑то из столбцов отсутствует, reindex добавит его с NaN
dept = dept.reindex(columns=dept_cols)


# # 1. Отчёт по отделу (department_from_prol_2023.csv)
# dept = pd.read_csv(OUT / "department_from_prol_2023.csv")

# # Добавляем обязательные поля
# dept["ReportType"] = "Department"
# dept["AM"] = "Отдел"  # можно оставить пустым, если не хочешь
# dept_cols = [
#     "ReportType",
#     "AM",
#     "Месяц",
#     "Период",
#     "к пролонгации первый месяц",
#     "пролонгировано в первый месяц",
#     "Коэффицент в первый месяц",
#     "к пролонгации через месяц",
#     "пролонгировано через месяц",
#     "Коэффицент через месяц",
# ]

# dept = dept[dept_cols]

# 2. Детальный отчёт по AM (am_from_prol_2023.csv)
am_detail = pd.read_csv(OUT / "am_from_prol_2023.csv")

am_detail["ReportType"] = "AM_detail"
am_detail_cols = [
    "ReportType",
    "AM",
    "Месяц",
    "Период",
    "к пролонгации первый месяц",
    "пролонгировано в первый месяц",
    "Коэффицент в первый месяц",
    "к пролонгации через месяц",
    "пролонгировано через месяц",
    "Коэффицент через месяц",
]

# am_detail = am_detail[am_detail_cols]
am_detail = am_detail.reindex(columns=am_detail_cols)

# 3. Пивоты по AM (K1 и K2) — опционально добавляем как «широкий» вид

# K1
am_k1 = pd.read_csv(OUT / "am_from_prol_k1_pivot_2023.csv")
# Преобразуем пивот обратно в long, чтобы структура была ближе к двум другим отчётам
am_k1_long = am_k1.melt(
    id_vars=["AM"],
    var_name="Месяц",
    value_name="Коэффицент в первый месяц"
)

am_k1_long["Месяц"] = am_k1_long["Месяц"].astype(int)

# K2
am_k2 = pd.read_csv(OUT / "am_from_prol_k2_pivot_2023.csv")
am_k2_long = am_k2.melt(
    id_vars=["AM"],
    var_name="Месяц",
    value_name="Коэффицент через месяц"
)
am_k2_long["Месяц"] = am_k2_long["Месяц"].astype(int)

# Объединяем K1 и K2 по AM+Месяц
am_pivot_long = pd.merge(
    am_k1_long,
    am_k2_long,
    on=["AM", "Месяц"],
    how="outer"
)

# Добавляем текстовый период (если уже есть маппинг MONTH_LABEL_RU – используем его)
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

am_pivot_long["Период"] = am_pivot_long["Месяц"].map(MONTH_LABEL_RU).fillna(
    am_pivot_long["Месяц"].astype(str)
)

am_pivot_long["ReportType"] = "AM_pivot"

am_pivot_cols = [
    "ReportType",
    "AM",
    "Месяц",
    "Период",
    # для пивота баз/фактов нет — только коэффициенты
    "Коэффицент в первый месяц",
    "Коэффицент через месяц",
]

am_pivot_long = am_pivot_long[am_pivot_cols]

# 4. Объединяем все три набора в один DataFrame

combined = pd.concat(
    [dept, am_detail, am_pivot_long],
    axis=0,
    ignore_index=True
)

# Для совместимости: заполним отсутствующие колоноки NaN, если в каких-то отчётах их нет
# (у AM_pivot нет баз/фактов – их можно оставить пустыми)

combined_out = OUT / "all_reports_2023.csv"
combined.to_csv(combined_out, index=False, encoding="utf-8-sig")

print(f"Объединённый отчёт сохранён в {combined_out}")
import pandas as pd
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent

fin = pd.read_csv(BASE / "data" / "financial_long_clean.csv")
prol = pd.read_csv(BASE / "data" / "prolongations_norm.csv")

# 1. Убираем проекты со стопом
fin_ok = fin.loc[~fin["has_stop_id"]].copy()

# 2. Определяем фактический последний месяц реализации по каждому id

def get_last_real_month(group: pd.DataFrame) -> int:
    """
    group: строки по одному id, с колонками month_code, amount, any_v_nol.
    Логика по сноске 1:
    - если все amount == 0 и при этом где-то есть 'в ноль' в последнем месяце -> сдвигаем на предыдущий месяц, если там есть отгрузка;
    - если вообще нет положительных сумм, возвращаем максимальный month_code (будем считать базой 0).
    """
    g = group.sort_values("month_code")
    # последняя строка по календарю
    last_row = g.iloc[-1]
    # есть ли какая-то положительная сумма
    has_positive = (g["amount"] > 0).any()

    if not has_positive:
        # нет положительных сумм вообще -> возвращаем последний календарный месяц
        return int(last_row["month_code"])

    # индекс последнего месяца с положительной суммой
    last_pos = g.loc[g["amount"] > 0, "month_code"].max()
    return int(last_pos)

# считаем фактический last_real_month для каждого id
last_real = (
    fin_ok.groupby("id", as_index=False)
          .apply(get_last_real_month)
          .rename(columns={None: "last_real_month"})
)

# 3. Объединяем с prolongations (там last_month_code из ТЗ)
fact = (
    fin_ok.merge(last_real, on="id", how="left")
          .merge(prol, left_on="id", right_on="id", how="left")
)

# last_real_month и last_month_code могут отличаться,
# но в качестве базы для пролонгации будем использовать last_real_month
fact["last_real_month"] = fact["last_real_month"].astype(int)
fact["month_code"] = fact["month_code"].astype(int)

# Сохраняем факт-таблицу
fact.to_csv(BASE / "data" / "fact_projects.csv", index=False)
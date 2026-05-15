from pathlib import Path
import pandas as pd


def format_am(fio: str) -> str:
    if not isinstance(fio, str):
        return ""
    parts = fio.strip().split()
    if len(parts) == 0:
        return ""
    surname = parts[0]
    name_initial = parts[1][0] if len(parts) > 1 and parts[1] else ""
    patr_initial = parts[2][0] if len(parts) > 2 and parts[2] else ""
    return f"{surname}_{name_initial}_{patr_initial}"


BASE_DIR = Path(__file__).parent

financial_path = BASE_DIR / "financial_data.csv"
output_path = BASE_DIR / "model_projects_clean.csv"


# 1. Читаем исходный financial_data
df = pd.read_csv(financial_path)

# Месяцы (подгони под реальные заголовки в CSV, если нужно)
month_cols = [
    'Ноябрь 2022', 'Декабрь 2022',
    'Январь 2023', 'Февраль 2023', 'Март 2023', 'Апрель 2023', 'Май 2023', 'Июнь 2023', 'Июль 2023', 'Август 2023',
    'Сентябрь 2023', 'Октябрь 2023', 'Ноябрь 2023', 'Декабрь 2023',
    'Январь 2024', 'Февраль 2024',
]

month_codes = [
    202211, 202212,
    202301, 202302, 202303, 202304, 202305, 202306, 202307, 202308,
    202309, 202310, 202311, 202312,
    202401, 202402,
]


# 2. Убираем проекты со "стоп"/"end" по всему id
stop_mask_row = df[month_cols].apply(
    lambda row: row.astype(str).str.contains("стоп|end", case=False, regex=True).any(),
    axis=1
)
ids_with_stop = df.loc[stop_mask_row, 'id'].unique()
df_clean = df.loc[~df['id'].isin(ids_with_stop)].copy()


# 3. Приводим месяцы к числам
def parse_value(x):
    try:
        if isinstance(x, str):
            x = x.replace(" ", "").replace("\u00A0", "").replace(",", ".")
        return float(x)
    except Exception:
        return pd.NA


values = df_clean[month_cols].map(parse_value)

# Флаг "в ноль" по ячейкам
is_vnol = df_clean[month_cols].apply(
    lambda row: row.astype(str).str.contains("в ноль", case=False),
    axis=1,
    result_type="expand"
)
is_vnol.columns = month_cols

# Сумма по проекту (id) и месяцу с учётом только чисел
group_sum = values.groupby(df_clean['id'])[month_cols].transform('sum')

# 4. Обработка "в ноль": переносим предыдущий месяц,
#    если в ячейке стоит "в ноль", числовое значение 0/NaN,
#    и по этому id и месяцу суммарная отгрузка = 0
values_filled = values.copy()

for idx, col in enumerate(month_cols):
    if idx == 0:
        continue
    prev_col = month_cols[idx - 1]

    base_cond = is_vnol[col] & ((values_filled[col].isna()) | (values_filled[col] == 0))
    cond_all_zero = group_sum[col].fillna(0) == 0

    cond = base_cond & cond_all_zero
    values_filled.loc[cond, col] = values_filled.loc[cond, prev_col]


# 5. last_code / last_year / last_month
def compute_last_code(row):
    for code, col in reversed(list(zip(month_codes, month_cols))):
        v = row[col]
        if pd.notna(v) and v != 0:
            return code
    return pd.NA


df_clean['last_code'] = values_filled.apply(compute_last_code, axis=1)
df_clean['last_year'] = df_clean['last_code'].astype('Int64') // 100
df_clean['last_month'] = df_clean['last_code'].astype('Int64') % 100


# 6. sum_last_month, sum_plus1, sum_plus2 по values_filled
def sum_at_offset(row, offset):
    code = row['last_code']
    if pd.isna(code):
        return 0
    idx = month_codes.index(code) + offset
    if idx < 0 or idx >= len(month_codes):
        return 0
    col = month_cols[idx]
    v = values_filled.loc[row.name, col]
    return 0 if pd.isna(v) else v


df_clean['sum_last_month'] = df_clean.apply(lambda r: sum_at_offset(r, 0), axis=1)
df_clean['sum_plus1'] = df_clean.apply(lambda r: sum_at_offset(r, 1), axis=1)
df_clean['sum_plus2'] = df_clean.apply(lambda r: sum_at_offset(r, 2), axis=1)


# 7. Собираем итоговый model_projects
result = pd.DataFrame({
    'id': df_clean['id'],
    'AM': df_clean['Account'].map(format_am),
    'last_year': df_clean['last_year'],
    'last_month': df_clean['last_month'],
})

for col in month_cols:
    result[col] = values_filled[col]

result['last_code'] = df_clean['last_code']
result['sum_last_month'] = df_clean['sum_last_month']
result['sum_plus1'] = df_clean['sum_plus1']
result['sum_plus2'] = df_clean['sum_plus2']


# 8. Сохраняем
output_path.parent.mkdir(parents=True, exist_ok=True)
result.to_csv(output_path, index=False)
print("Saved:", output_path)
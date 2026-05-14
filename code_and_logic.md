
# Код и логика решения теста — расчёт коэффициентов пролонгации

## 1. Назначение расчёта

Цель расчёта – оценить, насколько эффективно аккаунт‑менеджеры (AM) пролонгируют договоры клиентов, на основе данных за 2022–2024 годы. Для этого рассчитываются два коэффициента пролонгации:

- **K1** — пролонгация в первый месяц после окончания договора.
- **K2** — пролонгация во второй месяц после окончания договора, при условии отсутствия пролонгации в первый месяц.

Расчёт ведётся как по отделу в целом, так и по каждому менеджеру отдельно.

---

## 2. Используемые источники данных

Входные данные представлены в виде двух таблиц в формате CSV:

### `financial_raw.csv`

Помесячные финансовые показатели по договорам.

- **Уровень строк:** договор (`id`).
- **Столбцы:** `Account`, `Причина дубля`, а также помесячные суммы и текстовые статусы по периодам (Ноябрь 2022, Декабрь 2022, … Февраль 2024).
- **В ячейках** могут быть числовые суммы, а также спец‑значения «стоп», `end`, «в ноль».

### `prolongations_raw.csv`

Информация о договорах, подлежащих пролонгации.

- **Уровень строк:** договор (`id`).
- **Основное содержание:** последний месяц реализации договора (`month`) и закреплённый за ним аккаунт‑менеджер (`AM`).

Все расчёты выполняются на нормализованных версиях этих таблиц (`financial_long_clean.csv`, `prolongations_norm.csv`), которые автоматически формируются скриптом.

---

## 3. Ключевые допущения и бизнес‑правила

При расчётах используются следующие правила, основанные на ТЗ и сносках:

### Последний месяц реализации договора

- Базовым считается месяц, указанный в `prolongations_raw` как `month` (последний месяц реализации).
- Договоры, в которых в любом месяце встречается статус «стоп» или `end`, **исключаются** из расчёта пролонгаций.
- Случаи «в ноль» учитываются при нормализации финансов, но не меняют факт последнего месяца реализации (последний месяц по‑прежнему берётся из `prolongations`, за исключением явно описанных в ТЗ ситуаций).

### База для пролонгации

- Для договора с последним месяцем реализации \(L\) база пролонгации — это **сумма отгрузки в месяце \(L\)**.
- База K1 в месяце \(M\) формируется по договорам, для которых \(L = M - 1\).
- База K2 в месяце \(M\) формируется по договорам, для которых \(L = M - 2\), и которые **не были пролонгированы** в первый месяц после окончания.

### Факт пролонгации

- Договор считается **пролонгированным в первый месяц (K1)**, если в месяце \(M = L + 1\) для него есть положительная сумма отгрузки (> 0).
- Договор считается **пролонгированным во второй месяц (K2)**, если в месяце \(M = L + 2\) есть положительная сумма отгрузки (> 0), при этом в месяце \(L + 1\) отгрузки не было (или она равна 0).

### Коэффициенты пролонгации

**На уровне отдела:**

\[
K1(M) = \frac{\text{сумма пролонгированных договоров в } M}{\text{сумма базовых договоров, заканчивающихся в } M-1}
\]

\[
K2(M) = \frac{\text{сумма пролонгированных договоров в } M}{\text{сумма базовых договоров, заканчивающихся в } M-2 \text{ и не пролонгированных в } M-1}
\]

**На уровне менеджера:** те же формулы считаются отдельно в разрезе каждого AM.

---

## 4. Структура выходных отчётов

В результате работы скрипта формируются несколько отчётных файлов (CSV), которые используются для построения итогового отчёта в Google Sheets:

### Отчёт по отделу — `department_from_prol_2023.csv`

**Уровень агрегирования:** весь отдел.

**Поля:**

| Поле                             | Описание                                      |
|----------------------------------|-----------------------------------------------|
| `Месяц`                          | Технический код месяца в формате ГГГГММ (например, 202303). |
| `Период`                         | Человекочитаемый период (март 2023).          |
| `к пролонгации первый месяц`     | База K1.                                      |
| `пролонгировано в первый месяц`  | Факт K1.                                      |
| `Коэффицент в первый месяц`      | K1.                                           |
| `к пролонгации через месяц`      | База K2.                                      |
| `пролонгировано через месяц`     | Факт K2.                                      |
| `Коэффицент через месяц`         | K2.                                           |

### Отчёт по менеджерам — `am_from_prol_2023.csv`

**Уровень агрегирования:** AM × месяц.

Те же показатели, что и в отчёте по отделу, но рассчитанные отдельно для каждого менеджера.

### Сводные матрицы коэффициентов по AM

- `am_from_prol_k1_pivot_2023.csv`
- `am_from_prol_k2_pivot_2023.csv`

**Строки:** менеджеры (AM).  
**Столбцы:** месяцы (в человекочитаемом формате, например март 2023).  
**Значения:** соответствующие коэффициенты K1 и K2.

---

## 5. Реализация

Ниже приведён полный код на Python, реализующий описанную выше логику:

- нормализацию исходных данных;
- фильтрацию договоров со статусом «стоп»;
- расчёт баз и фактов пролонгации;
- вычисление коэффициентов K1 и K2 по отделу и по каждому AM;
- формирование отчётных файлов в формате CSV для дальнейшей загрузки в Google Sheets.

---

### 0. Импорт и базовые настройки

```python
import pandas as pd
from pathlib import Path

# Корень проекта (папка AD_test), если скрипт лежит в py/
BASE = Path(__file__).resolve().parent.parent

DATA_DIR = BASE / "data"
OUT_DIR = BASE / "out"
OUT_DIR.mkdir(exist_ok=True)
```

---

### 1. Загрузка и нормализация финансовых данных

**Задача блока:**  
Из wide‑таблицы `financial_raw.csv` (id, Account, Причина дубля, месяцы) получить long‑таблицу с суммами по id+месяц и флагами стоп / в ноль.

```python
# 1.1. Чтение исходных финансовых данных
financial = pd.read_csv(DATA_DIR / "financial_raw.csv")

# Список колонок-месяцев строго по структуре файла
MONTH_COLS = [
    "Ноябрь 2022",
    "Декабрь 2022",
    "Январь 2023",
    "Февраль 2023",
    "Март 2023",
    "Апрель 2023",
    "Май 2023",
    "Июнь 2023",
    "Июль 2023",
    "Август 2023",
    "Сентябрь 2023",
    "Октябрь 2023",
    "Ноябрь 2023",
    "Декабрь 2023",
    "Январь 2024",
    "Февраль 2024",
]

# 1.2. Находим id, где где‑нибудь стоит 'стоп' или 'end' — такие договоры исключаем
stop_mask = financial[MONTH_COLS].astype(str).apply(
    lambda s: s.str.lower().str.contains("стоп") | s.str.lower().str.contains("end")
)
ids_with_stop = financial.loc[stop_mask.any(axis=1), "id"].unique()

# 1.3. Перевод wide -> long
long_fin = financial.melt(
    id_vars=["id", "Account", "Причина дубля"],
    value_vars=MONTH_COLS,
    var_name="month_name",
    value_name="raw_value",
)

# 1.4. Выделяем числовые суммы и спец-метки ('стоп', 'в ноль')
s = long_fin["raw_value"].astype(str).str.strip()

long_fin["is_stop"] = s.str.lower().str.contains("стоп") | s.str.lower().str.contains("end")
long_fin["is_v_nol"] = s.str.lower().str.contains("в ноль")

num = (
    s.str.replace(" ", "", regex=False)
     .str.replace("\u00a0", "", regex=False)  # неразрывный пробел
     .str.replace(",", ".", regex=False)
)

long_fin["amount"] = pd.to_numeric(num, errors="coerce")

# 1.5. Агрегация по id+месяц (суммируем дубли, собираем флаги)
agg_fin = (
    long_fin.groupby(["id", "Account", "month_name"], as_index=False)
            .agg(
                amount=("amount", "sum"),
                any_stop=("is_stop", "any"),
                any_v_nol=("is_v_nol", "any"),
            )
)

# Флаг: у id вообще был 'стоп' где-то
agg_fin["has_stop_id"] = agg_fin["id"].isin(ids_with_stop)

# 1.6. Маппинг month_name -> числовой month_code (ГГГГММ)
MONTH_MAP = {
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
agg_fin["month_code"] = agg_fin["month_name"].map(MONTH_MAP).astype(int)

# Итог: long-факт по деньгам
financial_long_clean = agg_fin[
    ["id", "Account", "month_code", "amount", "any_stop", "any_v_nol", "has_stop_id"]
].copy()

financial_long_clean.to_csv(DATA_DIR / "financial_long_clean.csv", index=False)
```

**Логика:**  
Мы приводим все суммы к числам, суммируем дубли по id и месяцу; помечаем договоры со стоп как `has_stop_id`; дальше в расчётах пролонгаций такие id не участвуют, как требует сноска (досрочно прекращённые договоры исключаем).

---

### 2. Нормализация prolongations

**Задача:**  
Из `prolongations_raw.csv` получить таблицу id → (AM, last_month_code).

```python
prol_raw = pd.read_csv(DATA_DIR / "prolongations_raw.csv")

# Приводим текст месяца к нижнему регистру и убираем пробелы
prol_raw["month"] = prol_raw["month"].astype(str).str.strip().str.lower()

MONTH_MAP_PROL = {
    "ноябрь 2022": 202211,
    "декабрь 2022": 202212,
    "январь 2023": 202301,
    "февраль 2023": 202302,
    "март 2023": 202303,
    "апрель 2023": 202304,
    "май 2023": 202305,
    "июнь 2023": 202306,
    "июль 2023": 202307,
    "август 2023": 202308,
    "сентябрь 2023": 202309,
    "октябрь 2023": 202310,
    "ноябрь 2023": 202311,
    "декабрь 2023": 202312,
    "январь 2024": 202401,
    "февраль 2024": 202402,
}

prol_raw["last_month_code"] = prol_raw["month"].map(MONTH_MAP_PROL).astype(int)
prol_raw = prol_raw.rename(columns={"AM": "AM_primary"})

# На случай дублей по id берём одну строку
prolongations_norm = prol_raw[["id", "AM_primary", "last_month_code"]].drop_duplicates("id")
prolongations_norm.to_csv(DATA_DIR / "prolongations_norm.csv", index=False)
```

**Логика:**  
`last_month_code` — это последний месяц реализации по договору, заданный бизнесом (согласно ТЗ); именно от него мы будем отсчитывать пролонгацию в 1‑й и 2‑й месяц.

---

### 3. Факт‑таблица для расчёта по prolongations

Создадим объединённый факт.

```python
# Берём только договоры без стопа
fin_ok = financial_long_clean.loc[~financial_long_clean["has_stop_id"]].copy()

# Склейка: у каждой строчки по id+месяц есть AM и last_month_code
fact = fin_ok.merge(prolongations_norm, on="id", how="inner")

fact["month_code"] = fact["month_code"].astype(int)
fact["last_month_code"] = fact["last_month_code"].astype(int)

fact.to_csv(DATA_DIR / "fact_from_prol.csv", index=False)
```

**Логика:**  
Договоры с стоп полностью исключены; `last_month_code` — «якорь» окончания договора; дальше мы трактуем всё, что идёт после `last_month_code`, как пролонгации, по ТЗ (K1/K2).

---

### 4. Расчёт K1 и K2 по отделу (от prolongations)

**Задача:**  
Получить CSV под лист «Весь отдел»: месяц → (база K1, факт K1, коэф K1, база K2, факт K2, коэф K2).

```python
YEAR = 2023
min_m = YEAR * 100 + 1   # 202301
max_m = YEAR * 100 + 12  # 202312

rows_dep = []

for M in range(min_m, max_m + 1):
    prev1 = M - 1   # месяц окончания для пролонгации в первый месяц
    prev2 = M - 2   # месяц окончания для пролонгации во второй месяц

    # --- K1: пролонгация в первый месяц после окончания ---

    # База: договоры, чей last_month_code = prev1
    base1_ids = fact.loc[fact["last_month_code"] == prev1, "id"].unique()

    # Сумма базы: отгрузка в месяц окончания
    base1_sum = fact.loc[
        (fact["id"].isin(base1_ids)) &
        (fact["month_code"] == prev1),
        "amount"
    ].sum()

    # Факт K1: отгрузка в первый месяц после окончания (M), strictly > 0
    fact1_sum = fact.loc[
        (fact["id"].isin(base1_ids)) &
        (fact["month_code"] == M) &
        (fact["amount"] > 0),
        "amount"
    ].sum()

    # --- K2: пролонгация во второй месяц после окончания ---

    # Кандидаты: договоры, чей last_month_code = prev2
    cand2_ids = fact.loc[fact["last_month_code"] == prev2, "id"].unique()

    # Первый месяц после окончания для них
    first_after = prev2 + 1

    # Смотрим, кто имеет положительную отгрузку в первый месяц после окончания
    first_after_amounts = fact.loc[
        (fact["id"].isin(cand2_ids)) &
        (fact["month_code"] == first_after),
        ["id", "amount"]
    ]

    ids_with_first_pos = first_after_amounts.loc[
        first_after_amounts["amount"] > 0,
        "id"
    ].unique()

    # База K2: только те id, у кого НЕТ отгрузки в первый месяц после окончания
    base2_ids = [i for i in cand2_ids if i not in ids_with_first_pos]

    # Сумма базы K2: отгрузка в месяц окончания prev2
    base2_sum = fact.loc[
        (fact["id"].isin(base2_ids)) &
        (fact["month_code"] == prev2),
        "amount"
    ].sum()

    # Факт K2: отгрузка во второй месяц после окончания (M)
    fact2_sum = fact.loc[
        (fact["id"].isin(base2_ids)) &
        (fact["month_code"] == M) &
        (fact["amount"] > 0),
        "amount"
    ].sum()

    K1 = fact1_sum / base1_sum if base1_sum > 0 else 0
    K2 = fact2_sum / base2_sum if base2_sum > 0 else 0

    rows_dep.append({
        "Месяц": M,
        "к пролонгации первый месяц": base1_sum,
        "пролонгировано в первый месяц": fact1_sum,
        "Коэффицент в первый месяц": K1,
        "к пролонгации через месяц": base2_sum,
        "пролонгировано через месяц": fact2_sum,
        "Коэффицент через месяц": K2,
    })

dept_df = pd.DataFrame(rows_dep)

dept_df = dept_df[
    (dept_df["к пролонгации первый месяц"] > 0) |
    (dept_df["к пролонгации через месяц"] > 0)
].sort_values("Месяц")

dept_out = OUT_DIR / "department_from_prol_2023.csv"
dept_df.to_csv(dept_out, index=False, encoding="utf-8-sig")
print(f"[DEPARTMENT] saved: {dept_out}")
```

**Логика расчёта K1/K2:**

- **K1:**
  - База = сумма отгрузки в последний месяц реализации (prev1) договоров, заканчивающихся в prev1.
  - Факт = сумма отгрузки этих договоров в первый месяц после окончания (M = prev1+1).
  - Коэффициент = факт / база.

- **K2:**
  - Берём договоры, заканчивающиеся в prev2.
  - Выбрасываем те, у кого есть отгрузка в первый месяц после окончания (prev2+1).
  - База = сумма отгрузки в prev2.
  - Факт = сумма отгрузки во второй месяц после окончания (M = prev2+2).
  - Коэффициент = факт / база.

---

### 5. Расчёт K1 и K2 по AM (от prolongations)

**Задача:**  
Получить построчную таблицу: (AM, Месяц, база/факт/K1/K2).

```python
ams = fact["AM_primary"].dropna().unique()
rows_am = []

for am in ams:
    fact_am = fact.loc[fact["AM_primary"] == am]

    for M in range(min_m, max_m + 1):
        prev1 = M - 1
        prev2 = M - 2

        # --- K1 для конкретного AM ---
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

        # --- K2 для конкретного AM ---
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

        rows_am.append({
            "AM": am,
            "Месяц": M,
            "к пролонгации первый месяц": base1_sum,
            "пролонгировано в первый месяц": fact1_sum,
            "Коэффицент в первый месяц": K1,
            "к пролонгации через месяц": base2_sum,
            "пролонгировано через месяц": fact2_sum,
            "Коэффицент через месяц": K2,
        })

am_df = pd.DataFrame(rows_am)
am_df = am_df[
    (am_df["к пролонгации первый месяц"] > 0) |
    (am_df["к пролонгации через месяц"] > 0)
].sort_values(["AM", "Месяц"])

am_out = OUT_DIR / "am_from_prol_2023.csv"
am_df.to_csv(am_out, index=False, encoding="utf-8-sig")
print(f"[AM DETAIL] saved: {am_out}")
```

---

### 6. Базовые сводные отчёты по AM (K1/K2, строки менеджеры, столбцы месяцы)

```python
# Пивоты по K1 и K2 для менеджеров
pivot_k1 = am_df.pivot_table(
    index="AM",
    columns="Месяц",
    values="Коэффицент в первый месяц",
    aggfunc="first"
).reset_index()
pivot_k1.columns.name = None

pivot_k2 = am_df.pivot_table(
    index="AM",
    columns="Месяц",
    values="Коэффицент через месяц",
    aggfunc="first"
).reset_index()
pivot_k2.columns.name = None

k1_out = OUT_DIR / "am_from_prol_k1_pivot_2023.csv"
k2_out = OUT_DIR / "am_from_prol_k2_pivot_2023.csv"

pivot_k1.to_csv(k1_out, index=False, encoding="utf-8-sig")
pivot_k2.to_csv(k2_out, index=False, encoding="utf-8-sig")

print(f"[AM K1 PIVOT] saved: {k1_out}")
print(f"[AM K2 PIVOT] saved: {k2_out}")
```

---

## Заключение

Данный скрипт полностью автоматизирует процесс расчёта коэффициентов пролонгации K1 и K2 на основе исходных данных `financial_raw.csv` и `prolongations_raw.csv`. Результаты сохраняются в формате CSV и готовы для загрузки в Google Sheets или другие инструменты визуализации.
```

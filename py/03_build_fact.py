import pandas as pd
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent

fin = pd.read_csv(BASE / "data" / "financial_long_clean.csv")
prol = pd.read_csv(BASE / "data" / "prolongations_norm.csv")

# выбрасываем проекты со стопом
fin_ok = fin.loc[~fin["has_stop_id"]].copy()

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

fact = (
    fin_ok.merge(last_real, on="id", how="left")
          .merge(prol, on="id", how="left")
)

fact["month_code"] = fact["month_code"].astype(int)
fact["last_real_month"] = fact["last_real_month"].astype(int)

fact.to_csv(BASE / "data" / "fact_projects.csv", index=False)
import tabula
import pandas as pd

# 读取 PDF 中所有表格
dfs = tabula.read_pdf(
    "uscc_china_stocks.pdf",
    pages="all",
    lattice=True
)

# 合并
df = pd.concat(dfs, ignore_index=True)

print(df.head())
print(df.columns)
print(len(df))

# 从 USCC 官方 PDF 或行情网站抓取
# 输出结果接近 286 个中概股
# 可直接保存到 CSV / DataFrame

import requests
from bs4 import BeautifulSoup
import pandas as pd

# 示例结构 — 具体代码可根据目标数据源调整
url = 'https://www.uscc.gov/sites/default/files/2025-03/Chinese_Companies_Listed_on_US_Stock_Exchanges_03_2025.pdf'
r = requests.get(url)
with open('uscc_china_stocks.pdf', 'wb') as f:
    f.write(r.content)

# 进一步：解析 PDF -> 提取 ticker

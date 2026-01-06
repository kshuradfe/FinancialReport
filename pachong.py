import requests
import pandas as pd
import yfinance as yf
import time
from datetime import datetime

# ================= 配置区 =================
# 如果想测试代码，把这里设为 True (只跑前 5 家)
# 如果要跑全量，设为 False
TEST_MODE = True


# =========================================

def get_market_and_list_data():
    """
    【爬虫】满足 需求1(名单) 和 需求3(市值)
    直接从东方财富接口获取，数据最全，自带中文
    """
    print("🚀 正在爬取东方财富-美股中概股全量榜单...")
    url = "http://4.push2.eastmoney.com/api/qt/clist/get"

    all_data = []
    page = 1

    while True:
        params = {
            "pn": page, "pz": 100, "po": 1, "np": 1,
            "ut": "bd1d9ddb04089700cf9c27f6f7426281", "fltt": 2, "invt": 2,
            "fid": "f3", "fs": "b:MK0201",
            # f12=代码, f14=名称, f2=最新价, f20=市值, f9=市盈率动态, f23=市净率, f13=交易所ID
            "fields": "f12,f14,f2,f20,f9,f23,f5,f6,f15,f16,f17,f18,f13"
        }
        try:
            res = requests.get(url, params=params, timeout=5).json()
            if res["data"] is None or not res["data"]["diff"]:
                break

            data_list = res["data"]["diff"]
            for item in data_list:
                # 交易所映射
                market_map = {105: "纳斯达克", 106: "纽交所", 107: "美交所"}
                exchange_name = market_map.get(item.get('f13'), "美股其他")

                # 基础清洗
                row = {
                    "股票代码": item['f12'],
                    "股票简称": item['f14'],
                    "上市交易所": exchange_name,
                    "日期": datetime.now().strftime("%Y-%m-%d"),
                    "最新价": item['f2'],
                    "总市值": item['f20'],  # 东财单位通常是元，需注意
                    "市盈率(动态)": item['f9'],
                    "市净率": item['f23'],
                    "成交量(手)": item['f5'],
                    "成交额": item['f6'],
                    "最高": item['f15'],
                    "最低": item['f16'],
                    "开盘": item['f17'],
                    "昨收": item['f18']
                }
                all_data.append(row)

            print(f"  - 已获取第 {page} 页，累计 {len(all_data)} 家")
            page += 1
            time.sleep(0.5)

        except Exception as e:
            print(f"❌ 爬取中断: {e}")
            break

    return pd.DataFrame(all_data)


def get_financial_mapping(symbol):
    """
    【核心】满足 需求2(财务数据)
    使用 yfinance 拉取英文财报，强行映射到文档要求的中文表头
    """
    try:
        stock = yf.Ticker(symbol)

        # 获取最近季度的三张表
        q_fin = stock.quarterly_financials  # 利润表
        q_bs = stock.quarterly_balance_sheet  # 资产负债表
        q_cf = stock.quarterly_cashflow  # 现金流表

        # 结果字典（必须包含文档所有列，没有的填None）
        # 按照文档顺序初始化
        res = {
            "股票代码": symbol,
            "报告期间": None,
            "币种": "USD",  # yfinance 默认美元
            "单位": "元",  # yfinance 默认是原始数值
            # --- 资产负债表 ---
            "资产负债表.货币资金": None,
            "资产负债表.流动资产": None,
            "资产负债表.非流动资产": None,  # 需计算
            "资产负债表.总资产": None,
            "资产负债表.实收资本": None,
            "资产负债表.资本公积": None,
            "资产负债表.股东权益合计": None,
            "资产负债表.流动负债": None,
            "资产负债表.非流动负债": None,  # 需计算
            "资产负债表.总负债": None,
            # --- 现金流量表 ---
            "现金流量表.经营性现金流入": None,  # 美股少见
            "现金流量表.经营性现金流出": None,  # 美股少见
            "现金流量表.经营活动产生的现金流量净额": None,
            "现金流量表.投资活动产生的现金流量净额": None,
            "现金流量表.筹资活动产生的现金流量净额": None,
            # --- 利润表 ---
            "利润表.营业总收入": None,
            "利润表.营业成本": None,
            "利润表.研发费用": None,
            "利润表.净利润": None,
            "利润表.利润总额": None,
            "利润表.所得税": None,
            "研发投入占比": None
        }

        # 如果数据为空，直接返回空模版
        if q_fin.empty:
            return res

        # 锁定最近一个报告期
        date_col = q_fin.columns[0]
        res["报告期间"] = date_col.strftime("%Y-%m-%d")

        # === 辅助取值函数 ===
        def get_val(df, keys):
            # 尝试多个英文别名，找到为止
            for key in keys:
                if key in df.index:
                    val = df.loc[key, date_col]
                    # 处理 NaN
                    if pd.isna(val): continue
                    return val
            return None

        # === 1. 资产负债表映射 ===
        res["资产负债表.货币资金"] = get_val(q_bs, ['Cash And Cash Equivalents', 'Cash'])
        res["资产负债表.流动资产"] = get_val(q_bs, ['Current Assets'])
        res["资产负债表.总资产"] = get_val(q_bs, ['Total Assets'])
        res["资产负债表.股东权益合计"] = get_val(q_bs, ['Stockholders Equity', 'Total Equity'])
        res["资产负债表.流动负债"] = get_val(q_bs, ['Current Liabilities'])
        res["资产负债表.总负债"] = get_val(q_bs, ['Total Liabilities Net Minority Interest', 'Total Liabilities'])
        res["资产负债表.实收资本"] = get_val(q_bs, ['Share Issued', 'Ordinary Shares Number'])  # 近似值
        res["资产负债表.资本公积"] = get_val(q_bs, ['Capital Surplus', 'Additional Paid In Capital'])

        # 计算字段
        if res["资产负债表.总资产"] and res["资产负债表.流动资产"]:
            res["资产负债表.非流动资产"] = res["资产负债表.总资产"] - res["资产负债表.流动资产"]

        # === 2. 现金流量表映射 ===
        # 美股通常直接给净额，很少给“流入/流出”总额
        res["现金流量表.经营活动产生的现金流量净额"] = get_val(q_cf, ['Operating Cash Flow'])
        res["现金流量表.投资活动产生的现金流量净额"] = get_val(q_cf, ['Investing Cash Flow'])
        res["现金流量表.筹资活动产生的现金流量净额"] = get_val(q_cf, ['Financing Cash Flow'])

        # === 3. 利润表映射 ===
        res["利润表.营业总收入"] = get_val(q_fin, ['Total Revenue'])
        res["利润表.营业成本"] = get_val(q_fin, ['Cost Of Revenue'])
        res["利润表.研发费用"] = get_val(q_fin, ['Research And Development'])
        res["利润表.净利润"] = get_val(q_fin, ['Net Income'])
        res["利润表.利润总额"] = get_val(q_fin, ['Pretax Income'])
        res["利润表.所得税"] = get_val(q_fin, ['Tax Provision'])

        # === 4. 衍生指标计算 ===
        # 研发投入占比
        if res["利润表.研发费用"] and res["利润表.营业总收入"]:
            res["研发投入占比"] = res["利润表.研发费用"] / res["利润表.营业总收入"]

        return res

    except Exception as e:
        print(f"  ⚠️ 获取财务数据异常 {symbol}: {e}")
        return {}


# === 主程序 ===
if __name__ == "__main__":
    # 1. 获取名单和市值 (需求1 & 3)
    df_market = get_market_and_list_data()
    print(f"✅ 名单获取完成，共 {len(df_market)} 家。")

    # 2. 循环获取财务数据 (需求2)
    if TEST_MODE:
        target_list = df_market.head(5)
        print("🚩 测试模式：仅处理前 5 家...")
    else:
        target_list = df_market
        print("🚩 全量模式：开始处理所有企业 (请耐心等待)...")

    financial_data_list = []

    for index, row in target_list.iterrows():
        symbol = row['股票代码']
        name = row['股票简称']
        print(f"[{index + 1}/{len(target_list)}] 正在获取财报: {name} ({symbol})...")

        # 调用映射函数
        fin_row = get_financial_mapping(symbol)

        # 补全股票简称（因为 get_financial_mapping 里没传）
        fin_row['股票简称'] = name
        fin_row['企业全称'] = name  # 暂时用简称替代，全称需要查详情页

        financial_data_list.append(fin_row)

        # 休息一下防止封IP
        time.sleep(1)

    # 3. 按照文档要求导出
    df_fin = pd.DataFrame(financial_data_list)

    # 调整列顺序（把股票代码放在前面）
    cols = ['股票简称', '股票代码'] + [c for c in df_fin.columns if c not in ['股票简称', '股票代码']]
    df_fin = df_fin[cols]

    filename = f"海外上市企业数据_按需求文档_{datetime.now().strftime('%Y%m%d')}.xlsx"

    with pd.ExcelWriter(filename) as writer:
        # Sheet 1: 需求1_名单
        df_market[['股票简称', '股票代码', '最新价', '上市交易所', '日期']].to_excel(writer, sheet_name='需求1_名单',
                                                                                     index=False)

        # Sheet 2: 需求2_财务数据
        df_fin.to_excel(writer, sheet_name='需求2_财务数据', index=False)

        # Sheet 3: 需求3_市值数据
        df_market.to_excel(writer, sheet_name='需求3_市值数据', index=False)

    print(f"\n🎉 完美！所有数据已根据需求文档生成: {filename}")
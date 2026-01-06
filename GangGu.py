import requests
import pandas as pd
import yfinance as yf
import time
from datetime import datetime

# ================= 配置区 =================
# True: 测试模式 (只跑前 5 家，快速看效果)
# False: 生产模式 (跑全量 2600+ 家)
TEST_MODE = True


# =========================================

def get_hk_market_list():
    """
    【爬虫】满足 需求1(名单) 和 需求3(市值)
    抓取范围：港股主板 + 港股创业板 (涵盖几乎所有在港上市的中资企业)
    """
    print("🚀 正在爬取东方财富-港股全量榜单 (主板+创业板)...")
    url = "http://4.push2.eastmoney.com/api/qt/clist/get"

    all_data = []
    page = 1

    while True:
        params = {
            "pn": page, "pz": 100, "po": 1, "np": 1,
            "ut": "bd1d9ddb04089700cf9c27f6f7426281", "fltt": 2, "invt": 2,
            "fid": "f3",
            # fs参数解释: m:128 t:3 (港股主板), m:128 t:4 (港股创业板)
            "fs": "m:128 t:3,m:128 t:4",
            # f12=代码, f14=名称, f2=最新价, f20=市值, f9=市盈率, f23=市净率
            "fields": "f12,f14,f2,f20,f9,f23,f5,f6,f15,f16,f17,f18"
        }
        try:
            res = requests.get(url, params=params, timeout=5).json()
            if res["data"] is None or not res["data"]["diff"]:
                break

            data_list = res["data"]["diff"]

            for item in data_list:
                # 东方财富代码清洗：00700 -> 0700.HK
                # 逻辑：取后4位，加上 .HK
                raw_code = item['f12']  # 字符串 '00700'
                if len(raw_code) >= 4:
                    yahoo_code = raw_code[-4:] + ".HK"
                else:
                    yahoo_code = raw_code + ".HK"  # 防御性代码

                row = {
                    "股票代码": yahoo_code,  # 给 Yahoo 用的 (0700.HK)
                    "原始代码": raw_code,  # 保留原始代码 (00700)
                    "股票简称": item['f14'],
                    "上市交易所": "香港证券交易所",
                    "日期": datetime.now().strftime("%Y-%m-%d"),
                    "最新价": item['f2'],
                    "总市值": item['f20'],
                    "市盈率(动态)": item['f9'],
                    "市净率": item['f23'],
                    "成交量(手)": item['f5'],
                    "成交额": item['f6']
                }
                all_data.append(row)

            print(f"  - 已获取第 {page} 页，累计 {len(all_data)} 家")
            page += 1
            # 港股数据量大，稍微快一点点没事
            time.sleep(0.3)

        except Exception as e:
            print(f"❌ 爬取中断: {e}")
            break

    return pd.DataFrame(all_data)


def get_financial_mapping(symbol):
    """
    【核心】满足 需求2(财务数据)
    针对港股财报进行字段映射
    """
    try:
        stock = yf.Ticker(symbol)

        # 获取财报
        q_fin = stock.quarterly_financials
        q_bs = stock.quarterly_balance_sheet
        q_cf = stock.quarterly_cashflow

        # 初始化结果 (按需求文档)
        res = {
            "股票代码": symbol,
            "报告期间": None,
            "币种": "HKD/CNY",  # 港股通常是港币或人民币
            # --- 资产负债表 ---
            "资产负债表.货币资金": None,
            "资产负债表.流动资产": None,
            "资产负债表.非流动资产": None,
            "资产负债表.总资产": None,
            "资产负债表.实收资本": None,
            "资产负债表.资本公积": None,
            "资产负债表.股东权益合计": None,
            "资产负债表.流动负债": None,
            "资产负债表.非流动负债": None,
            "资产负债表.总负债": None,
            # --- 现金流量表 ---
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

        if q_fin.empty:
            return res

        date_col = q_fin.columns[0]
        res["报告期间"] = date_col.strftime("%Y-%m-%d")

        def get_val(df, keys):
            for key in keys:
                if key in df.index:
                    val = df.loc[key, date_col]
                    if pd.isna(val): continue
                    return val
            return None

        # === 映射逻辑 (与美股通用) ===
        res["资产负债表.货币资金"] = get_val(q_bs, ['Cash And Cash Equivalents', 'Cash'])
        res["资产负债表.流动资产"] = get_val(q_bs, ['Current Assets'])
        res["资产负债表.总资产"] = get_val(q_bs, ['Total Assets'])
        res["资产负债表.股东权益合计"] = get_val(q_bs, ['Stockholders Equity', 'Total Equity'])
        res["资产负债表.流动负债"] = get_val(q_bs, ['Current Liabilities'])
        res["资产负债表.总负债"] = get_val(q_bs, ['Total Liabilities Net Minority Interest', 'Total Liabilities'])
        res["资产负债表.实收资本"] = get_val(q_bs, ['Share Issued', 'Ordinary Shares Number'])

        # 计算字段
        if res["资产负债表.总资产"] and res["资产负债表.流动资产"]:
            res["资产负债表.非流动资产"] = res["资产负债表.总资产"] - res["资产负债表.流动资产"]

        res["现金流量表.经营活动产生的现金流量净额"] = get_val(q_cf, ['Operating Cash Flow'])
        res["现金流量表.投资活动产生的现金流量净额"] = get_val(q_cf, ['Investing Cash Flow'])
        res["现金流量表.筹资活动产生的现金流量净额"] = get_val(q_cf, ['Financing Cash Flow'])

        res["利润表.营业总收入"] = get_val(q_fin, ['Total Revenue'])
        res["利润表.营业成本"] = get_val(q_fin, ['Cost Of Revenue'])
        res["利润表.研发费用"] = get_val(q_fin, ['Research And Development'])
        res["利润表.净利润"] = get_val(q_fin, ['Net Income'])
        res["利润表.利润总额"] = get_val(q_fin, ['Pretax Income'])
        res["利润表.所得税"] = get_val(q_fin, ['Tax Provision'])

        if res["利润表.研发费用"] and res["利润表.营业总收入"]:
            res["研发投入占比"] = res["利润表.研发费用"] / res["利润表.营业总收入"]

        return res

    except Exception as e:
        print(f"  ⚠️ 获取财报失败 {symbol}: {e}")
        return {}


# === 主程序 ===
if __name__ == "__main__":
    # 1. 获取名单
    df_market = get_hk_market_list()
    print(f"✅ 港股名单获取完成，共 {len(df_market)} 家。")

    # 2. 获取财务数据
    if TEST_MODE:
        target_list = df_market.head(5)
        print("🚩 测试模式：仅处理前 5 家...")
    else:
        target_list = df_market
        print("🚩 全量模式：开始处理所有港股 (可能需要较长时间)...")

    financial_data_list = []

    for index, row in target_list.iterrows():
        symbol = row['股票代码']  # 0700.HK
        name = row['股票简称']
        print(f"[{index + 1}/{len(target_list)}] 获取财报: {name} ({symbol})...")

        fin_row = get_financial_mapping(symbol)
        fin_row['股票简称'] = name
        fin_row['企业全称'] = name
        financial_data_list.append(fin_row)

        time.sleep(1)  # 港股请求频率限制较严，保持 1秒/次

    # 3. 导出 Excel
    df_fin = pd.DataFrame(financial_data_list)
    # 调整列顺序
    cols = ['股票简称', '股票代码'] + [c for c in df_fin.columns if c not in ['股票简称', '股票代码']]
    if not df_fin.empty:
        df_fin = df_fin[cols]

    filename = f"港股上市企业数据_按需求文档_{datetime.now().strftime('%Y%m%d')}.xlsx"

    with pd.ExcelWriter(filename) as writer:
        df_market.to_excel(writer, sheet_name='需求3_市值数据', index=False)
        df_fin.to_excel(writer, sheet_name='需求2_财务数据', index=False)

    print(f"\n🎉 港股任务完成！文件已生成: {filename}")
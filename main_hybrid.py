"""
中概股财务数据采集 - 混合方案（最佳方案）

策略：
1. 使用 akshare 自动获取完整的中概股列表
2. 使用 yfinance 获取财务数据（更稳定、数据更全）

优点：
- 自动获取所有中概股，无需手动维护CSV
- 财务数据使用yfinance，更稳定可靠
"""

import pandas as pd
from datetime import datetime
import time
import warnings
warnings.filterwarnings('ignore')

try:
    import akshare as ak
    AKSHARE_AVAILABLE = True
except ImportError:
    AKSHARE_AVAILABLE = False
    print("⚠️  akshare未安装，将无法自动获取中概股列表")

try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False
    print("❌ yfinance未安装，请运行: pip install yfinance")

# ================= 配置区 =================
TEST_MODE = True
TEST_LIMIT = 300  # 测试模式下每个市场的数量

# 财务数据请求延迟
REQUEST_DELAY = 0.5

# 获取名单时的重试次数
MAX_RETRIES = 3

# ADR及特殊ticker别名映射表（解决ticker不匹配问题）
ADR_ALIAS = {
    'HCM': 'HCM.US',      # 和黄医药
    'ONC': 'ONC.US',      # 百济神州
    'AAPG': 'AAPG.US',
    'ABLV': 'ABLV.US',
    'SOGP': 'SOGP.US',
    'AAM': 'AAM.US',
    'BON': 'BON.US',
    'CHNR': 'CHNR.US',
    'AEHL': 'AEHL.US',
    'EJH': 'EJH.US',
    'TANH': 'TANH.US',
    'PLAG': 'PLAG.US',
    'FAMI': 'FAMI.US',
}

# 美股中概股列表（用于筛选）
# ================= 配置区 =================
# ... 其他配置保持不变 ...

# 扩充后的美股中概股白名单 (Top 120+)
US_CHINA_STOCKS = [
    'LHSW','RGC','CD','SMXT','SLAI','MASK','SCAG','AGMH','ONEG','WYHG',
    'DTSS','JFU','SELX','CANG','YMT','GTEC','MIMI','RITR','PAVS','CDTG',
    'LXEH','NPT','HUDI','ELPW','PTHL','KXIN','BNR','ADVB','ABTS','NXTT',
    'BTOG','TROO','WXM','ZNB','GMM','SGLY','CAN','UXIN','FTFT','HOLO',
    'WIMI','LITB','JFIN','ZJK','KNDI','NA','JLHL','ZCMD','BTBT','DSY',
    'BTDR','MFI','NCTY','MENS','WCT','FUFU','RERE','TIGR','DDL','GDHG',
    'MKDW','BEKE','MATH','YRD','CCM','XNET','GSIW','LEDS','YXT','WAI',
    'ZDAI','GMHS','LGHL','SVM','GOTU','YSXT','NCEW','TJGC','EDTK','SFHG',
    'MLGO','UTSI','LOT','NOAH','YDKG','ZJYL','DDC','ATXG','STAK','ZEPP',
    'NEGG','HIHO','GRRR','IQ','INLF','XYF','CLWT','HUYA','AMBO','YAAS',
    'BTCT','DOGZ','NIU','WRD','EBON','LICN','ZLAB','CMCM','PTLE','AIIO',
    'TUYA','TME','SJ','LSE','BAOS','CASI','LU','GURE','ZKIN','PONY',
    'RDAC','BILI','DXST','CHA','FINV','ZYBT','NCI','DOYU','ZH','PT',
    'ECX','PDD','QFIN','OWLS','SOS','EZGO','LZMH','GHG','AXG','AIXI',
    'CCG','FENG','TAOP','HCAI','SY','THCH','YMM','BZ','JKS','ONC',
    'NIPG','GDC','CNEY','ABLV','FEDU','KC','NBP','VNET','ITP','FVNNU',
    'FAMI','PERF','API','GLXG','BQ','FRGT','RLX','CENN','MSW','WB',
    'JG','JOYY','MOMO','WETH','YALA','HTT','CHNR','GGR','DAO','IFBD',
    'RAY','JZ','CHSN','AAPG','SEED','LX','RYET','MEGL','CPHI','UK',
    'PETZ','BZUN','VIPS','CAAS','ZTO','TOP','NWGL','HAO','ANL','AMTD',
    'TSM','YOUL','AIFU','TOUR','AIHS','LOBO','DCX','TCOM','CPOP','DQ',
    'HKD','LUD','YB','FUTU','IZM','CHT','HSAI','LI','GCT','EJH',
    'HERE','ATAT','NTCL','XCH','ATHM','SFWL','GSUN','EHGO','TWG','ASX',
    'BHAT','DSWL','JD','PN','TC','VSA','MNSO','YQ','POM','RETO','ACMR',
    'SNTG','HXHX','BABA','MLCO','SOHU','TIRX','CYD','STG','KBSX',
    'YHGJ','WTGUU','WTG','UCAR','SVA','SDA','RDGT','RDACU','RCON',
    'QMMM','OST','MGIH','MAMK','HDL','FVTI','FVN','EPOW','EM','JL',
    'SXTC','ZKH','BYAH','YSG','WDH','ORIS','BIDU','DUO','CLIK','PLBL',
    'NAAS','HLP','VIOT','TRSG','BON','CREG','AS','CBAT','HIMX','TAL',
    'UMC','SUGP','CCTG','WAFU','DXF','MSC','PMAX','COE','LBGJ','IMOS',
    'VSME','EH','CSIQ','EDU','GIGM','ILAG','WNW','XPEV','TNMG','GDS',
    'CNF','UPC','QH','AACG','BYSI','NTES','ZBAO','WETO','MI','CNTB',
    'IH','SKBL','MTC','XWIN','TANH','YIBO','GVH','YUMC','XHG','JXG',
    'WTO','UCL','CGTL','ROMA','APLM','HCM','PLUT','PSIG','SRL','ZBAI',
    'SUPX','JDZG','SOGP','FNGR','YJ','NISN','AURE','CNET','DGNX',
    'ADAG','HKPD','PLAG','BVC','UOKA','LGCB','BDMD','APM','AHG',
    'INTJ','JZXN','UBXG','MYND','ICG','LGCL','FLX','STFS','MTEN',
    'LEGN','CLPS','BGM','NIO','MAAS','MOGU','YI','BIYA','JYD','HUHU',
    'NAMI','CHR','GPCR','RAYA','AEHL','SLGB','FEBO','ATGL','APWC',
    'HUIZ','WOK','HKIT','JWEL','XTKG','LANV','KRKR','NCL','AZI','OCG'
]


# =========================================


def get_us_stocks_list():
    """
    自动获取美股中概股列表 (增强版：API失效时使用全量筛选)
    """
    print("\n正在获取美股中概股列表...")

    if not AKSHARE_AVAILABLE:
        print("  ❌ akshare未安装")
        return pd.DataFrame()

    # === 方案 A: 尝试直接获取中概股板块 (如果API恢复) ===
    try:
        df = ak.stock_us_famous_spot_em(symbol="中概股")
        if df is not None and not df.empty:
            df['代码'] = df['代码'].astype(str).str.replace(r'^\d+\.', '', regex=True)
            print(f"  ✅ [方案A] API直接获取成功: {len(df)} 只")

            result = pd.DataFrame()
            result['股票代码'] = df['代码']
            result['股票简称'] = df['name'] if 'name' in df.columns else df['名称']
            result['上市交易所'] = 'US'
            result['币种'] = 'USD'
            if TEST_MODE:
                return result.head(TEST_LIMIT)
            return result
    except:
        print("  ⚠️  [方案A] API专用接口失效，切换至方案B...")

    # === 方案 B: 获取全部美股 -> 筛选白名单 (最稳妥) ===
    # 既然你看到了日志里有 39 家，说明代码走到了这里，
    # 关键在于我们要用 stock_us_spot_em 获取所有美股，然后用 US_CHINA_STOCKS 去过滤
    try:
        print("  ⏳ [方案B] 正在拉取美股全量数据 (约10秒)...")
        # 获取美股全量列表（包含上万只股票）
        df_all = ak.stock_us_spot_em()

        # 清洗代码格式
        df_all['代码'] = df_all['代码'].astype(str).str.replace(r'^\d+\.', '', regex=True)

        # 筛选：只保留在 US_CHINA_STOCKS 白名单里的
        # 将白名单转为集合，提高查找速度
        target_stocks = set(US_CHINA_STOCKS)

        # 筛选
        df_filtered = df_all[df_all['代码'].isin(target_stocks)].copy()

        if not df_filtered.empty:
            print(f"  ✅ [方案B] 筛选成功: 从 {len(df_all)} 只美股中找到 {len(df_filtered)} 只中概股")

            result = pd.DataFrame()
            result['股票代码'] = df_filtered['代码']
            result['股票简称'] = df_filtered['名称']
            result['上市交易所'] = 'US'
            result['币种'] = 'USD'

            if TEST_MODE:
                print(f"  [测试模式] 仅使用前 {TEST_LIMIT} 家")
                return result.head(TEST_LIMIT)
            return result
        else:
            print("  ❌ [方案B] 筛选结果为空，可能是代码匹配问题")

    except Exception as e:
        print(f"  ❌ [方案B] 失败: {e}")

    # === 方案 C: 彻底失败，仅返回白名单代码 (无名称) ===
    print("  ⚠️  所有API均失败，使用静态白名单")
    df = pd.DataFrame({'代码': US_CHINA_STOCKS})
    df['名称'] = "中概股(静态)"

    result = pd.DataFrame()
    result['股票代码'] = df['代码']
    result['股票简称'] = df['名称']
    result['上市交易所'] = 'US'
    result['币种'] = 'USD'

    if TEST_MODE:
        return result.head(TEST_LIMIT)
    return result


def get_hk_stocks_list():
    """
    自动获取港股列表
    """
    print("\n正在获取港股列表...")

    if not AKSHARE_AVAILABLE:
        print("  ❌ akshare未安装")
        return pd.DataFrame()

    for attempt in range(MAX_RETRIES):
        try:
            if attempt > 0:
                print(f"  重试 {attempt}/{MAX_RETRIES-1}...")
                time.sleep(3)

            df = ak.stock_hk_spot_em()

            if df is not None and not df.empty:
                print(f"  ✅ 获取到 {len(df)} 只港股")

                # 关键修复：按市值排序，筛选大型股
                # 1. 标准化代码格式
                df['代码'] = df['代码'].astype(str).str.zfill(5)
                df['代码_数字'] = pd.to_numeric(df['代码'], errors='coerce')

                # 2. 筛选主板股票（代码 < 10000，排除创业板等）
                df = df[
                    (df['代码_数字'] < 10000) &
                    (df['代码_数字'] > 0)
                ].copy()

                # 3. 按市值排序（最重要！）
                if '总市值' in df.columns:
                    # 只保留有市值数据的（过滤掉没数据的小型股）
                    df = df[df['总市值'].notna()].copy()
                    # 按市值降序排序，大型股在前
                    df = df.sort_values('总市值', ascending=False)
                    print(f"  ✅ 按市值排序，筛选出 {len(df)} 只主板大型股")
                else:
                    print(f"  ⚠️  无市值数据，无法排序")

                result = pd.DataFrame()
                result['股票代码'] = df['代码']
                result['股票简称'] = df['名称']
                result['上市交易所'] = 'HKEX'
                result['币种'] = 'HKD'

                # 测试模式截断
                if TEST_MODE:
                    print(f"  [测试模式] 取市值最大的前 {TEST_LIMIT} 家")
                    result = result.head(TEST_LIMIT)

                return result

        except Exception as e:
            if attempt == MAX_RETRIES - 1:
                print(f"  ❌ 获取失败: {e}")

    return pd.DataFrame()


def get_financial_data_hk_akshare(stock_code, stock_name):
    """
    使用akshare获取港股财务数据
    """
    try:
        # 获取港股财务数据（东方财富数据源）
        balance_df = ak.stock_hk_finance_balance_em(symbol=stock_code)
        income_df = ak.stock_hk_finance_income_em(symbol=stock_code)
        
        if balance_df.empty or income_df.empty:
            return pd.DataFrame()
        
        financial_records = []
        
        # 取最近8个报告期
        for idx in range(min(len(income_df), 8)):
            try:
                # 获取报告期
                report_date = income_df.iloc[idx].get('报告期', '')
                if not report_date:
                    continue
                
                record = {
                    '股票代码': stock_code,
                    '股票简称': stock_name,
                    '币种': 'HKD',
                    '报告期间': report_date,
                    '总资产': balance_df.iloc[idx].get('资产总计', None) if idx < len(balance_df) else None,
                    '总负债': balance_df.iloc[idx].get('负债总计', None) if idx < len(balance_df) else None,
                    '净利润': income_df.iloc[idx].get('净利润', None),
                    '营业总收入': income_df.iloc[idx].get('营业收入', None),
                    '营业总成本': income_df.iloc[idx].get('营业成本', None),
                    '研发费用': income_df.iloc[idx].get('研发费用', None),
                    '利润总额': income_df.iloc[idx].get('利润总额', None),
                    '所得税': income_df.iloc[idx].get('所得税', None),
                }
                
                # 计算衍生指标
                revenue = record['营业总收入']
                rd_expense = record['研发费用']
                cost = record['营业总成本']
                assets = record['总资产']
                
                if revenue and rd_expense and revenue != 0:
                    record['研发投入占比'] = (float(rd_expense) / float(revenue)) * 100
                else:
                    record['研发投入占比'] = None
                
                if revenue and cost and revenue != 0:
                    record['毛利率'] = ((float(revenue) - float(cost)) / float(revenue)) * 100
                else:
                    record['毛利率'] = None
                
                if assets and revenue and assets != 0:
                    record['总资产周转率'] = float(revenue) / float(assets)
                else:
                    record['总资产周转率'] = None
                
                financial_records.append(record)
            except:
                continue
        
        return pd.DataFrame(financial_records)
    except:
        return pd.DataFrame()


def get_financial_data_yfinance(stock_code, stock_name, market='US'):
    """
    使用yfinance获取财务数据（增强版）
    
    改进：
    1. ADR别名映射
    2. 季度失败→年报兜底
    3. 失败原因分级
    """
    fail_reason = None
    
    try:
        # 根据市场调整股票代码格式
        if market == 'HK':
            # 港股：添加.HK后缀
            code = stock_code + '.HK'
        else:
            # 美股：使用ADR别名映射
            code = ADR_ALIAS.get(stock_code, stock_code)
        
        # 创建股票对象
        ticker = yf.Ticker(code)
        
        # ========== 改进1：季度失败→年报兜底 ==========
        # 优先尝试季度数据
        try:
            quarterly_income = ticker.quarterly_income_stmt
            quarterly_balance = ticker.quarterly_balance_sheet
            is_quarterly = True
        except:
            quarterly_income = pd.DataFrame()
            quarterly_balance = pd.DataFrame()
            is_quarterly = False
        
        # 如果季度数据为空，降级到年报
        if quarterly_income.empty:
            try:
                quarterly_income = ticker.income_stmt  # 年报
                quarterly_balance = ticker.balance_sheet  # 年报
                is_quarterly = False
            except:
                fail_reason = 'NO_DATA'
                return pd.DataFrame()
        
        # 如果年报也为空，彻底失败
        if quarterly_income.empty:
            fail_reason = 'NO_YAHOO'
            return pd.DataFrame()
        
        financial_records = []
        currency = 'HKD' if market == 'HK' else 'USD'
        
        # 处理数据（季度或年度）
        if not quarterly_income.empty:
            for date_col in quarterly_income.columns[:8]:  # 最近8个季度
                try:
                    # 获取资产负债表数据
                    total_assets = None
                    total_liabilities = None
                    if not quarterly_balance.empty and date_col in quarterly_balance.columns:
                        if 'Total Assets' in quarterly_balance.index:
                            total_assets = quarterly_balance.loc['Total Assets', date_col]
                        if 'Total Liabilities Net Minority Interest' in quarterly_balance.index:
                            total_liabilities = quarterly_balance.loc['Total Liabilities Net Minority Interest', date_col]
                    
                    # 获取利润表数据
                    net_income = quarterly_income.loc['Net Income', date_col] if 'Net Income' in quarterly_income.index else None
                    total_revenue = quarterly_income.loc['Total Revenue', date_col] if 'Total Revenue' in quarterly_income.index else None
                    cost_of_revenue = quarterly_income.loc['Cost Of Revenue', date_col] if 'Cost Of Revenue' in quarterly_income.index else None
                    rd_expense = quarterly_income.loc['Research And Development', date_col] if 'Research And Development' in quarterly_income.index else None
                    pretax_income = quarterly_income.loc['Pretax Income', date_col] if 'Pretax Income' in quarterly_income.index else None
                    tax_provision = quarterly_income.loc['Tax Provision', date_col] if 'Tax Provision' in quarterly_income.index else None
                    
                    record = {
                        '股票代码': stock_code,
                        '股票简称': stock_name,
                        '币种': currency,
                        '报告期间': date_col.strftime('%Y-%m-%d'),
                        '数据类型': 'Q' if is_quarterly else 'A',  # Q=季度, A=年度
                        '总资产': total_assets,
                        '总负债': total_liabilities,
                        '净利润': net_income,
                        '营业总收入': total_revenue,
                        '营业总成本': cost_of_revenue,
                        '研发费用': rd_expense,
                        '利润总额': pretax_income,
                        '所得税': tax_provision,
                    }
                    
                    # 计算衍生指标
                    if total_revenue and rd_expense and total_revenue != 0:
                        record['研发投入占比'] = (rd_expense / total_revenue) * 100
                    else:
                        record['研发投入占比'] = None
                    
                    if total_revenue and cost_of_revenue and total_revenue != 0:
                        record['毛利率'] = ((total_revenue - cost_of_revenue) / total_revenue) * 100
                    else:
                        record['毛利率'] = None
                    
                    if total_assets and total_revenue and total_assets != 0:
                        record['总资产周转率'] = total_revenue / total_assets
                    else:
                        record['总资产周转率'] = None
                    
                    financial_records.append(record)
                    
                except Exception as e:
                    continue
        
        return pd.DataFrame(financial_records)
        
    except Exception as e:
        fail_reason = 'EXCEPTION'
        return pd.DataFrame()


def collect_financial_data(company_list, market='US'):
    """批量采集财务数据（增强版：失败分级）"""
    print(f"\n开始采集 {market} 市场财务数据...")
    print(f"共需处理 {len(company_list)} 家企业")
    
    if market == 'HK':
        print(f"数据源: akshare (东方财富)")
    else:
        print(f"数据源: yfinance (季度→年报兜底)")
    print()
    
    all_financial_data = []
    success_count = 0
    fail_count = 0
    quarterly_count = 0  # 季度数据成功数
    annual_count = 0     # 年度数据成功数
    
    for idx, row in company_list.iterrows():
        stock_code = row['股票代码']
        stock_name = row['股票简称']
        
        print(f"  [{idx+1}/{len(company_list)}] {stock_name} ({stock_code})...", end=' ')
        
        # 根据市场选择数据源
        if market == 'HK':
            # 港股使用akshare（yfinance对港股支持很差）
            financial_df = get_financial_data_hk_akshare(stock_code, stock_name)
            data_type = ''
        else:
            # 美股使用yfinance
            financial_df = get_financial_data_yfinance(stock_code, stock_name, market)
            # 判断数据类型
            if not financial_df.empty:
                data_type = financial_df.iloc[0].get('数据类型', 'Q')
            else:
                data_type = ''
        
        if not financial_df.empty:
            all_financial_data.append(financial_df)
            success_count += 1
            
            # 统计数据类型
            if data_type == 'Q':
                quarterly_count += 1
                print(f"✅ {len(financial_df)}期(季)")
            elif data_type == 'A':
                annual_count += 1
                print(f"✅ {len(financial_df)}期(年)")
            else:
                print(f"✅ {len(financial_df)}期")
        else:
            fail_count += 1
            print(f"❌ 失败")
        
        time.sleep(REQUEST_DELAY)
    
    # 详细统计
    print(f"\n采集完成: 成功 {success_count} 家, 失败 {fail_count} 家")
    if market == 'US' and (quarterly_count > 0 or annual_count > 0):
        print(f"  数据类型: 季度 {quarterly_count} 家, 年度 {annual_count} 家")
        print(f"  成功率: {success_count}/{len(company_list)} = {success_count/len(company_list)*100:.1f}%")
    
    if all_financial_data:
        result = pd.concat(all_financial_data, ignore_index=True)
        return result
    else:
        return pd.DataFrame()


# ==================== 主程序 ====================

if __name__ == "__main__":
    print("\n" + "="*60)
    print("【中概股财务数据采集系统 - 混合方案】")
    print(f"启动时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    print("\n策略说明:")
    print("  - 美股列表: akshare 获取中概股")
    print("  - 港股列表: akshare 按市值排序")
    print("  - 美股财务: yfinance (稳定)")
    print("  - 港股财务: akshare (东方财富)")
    print("="*60)
    
    # 检查依赖
    if not AKSHARE_AVAILABLE:
        print("\n❌ 未安装 akshare 库")
        print("   请运行: pip install akshare")
        input("\n按回车键退出...")
        exit(1)
    
    if not YFINANCE_AVAILABLE:
        print("\n❌ 未安装 yfinance 库")
        print("   请运行: pip install yfinance")
        input("\n按回车键退出...")
        exit(1)
    
    print("\n✅ 所有依赖已安装")
    
    if TEST_MODE:
        print(f"\n🚩 测试模式：每个市场 {TEST_LIMIT} 家企业")
        print("   设置 TEST_MODE = False 启用全量模式")
    
    # ==================== 步骤1: 获取中概股名单 ====================
    print("\n" + "="*60)
    print("【步骤 1】获取中概股名单")
    print("="*60)
    
    # 获取美股
    df_us = get_us_stocks_list()
    if not df_us.empty:
        print(f"  ✅ 美股: {len(df_us)} 家")
    else:
        print(f"  ⚠️  美股: 获取失败")

    # 获取港股
    df_hk = get_hk_stocks_list()
    if not df_hk.empty:
        print(f"  ✅ 港股: {len(df_hk)} 家")
    else:
        print(f"  ⚠️  港股: 获取失败")
    
    # 检查是否有数据
    if df_us.empty and df_hk.empty:
        print("\n❌ 未能获取任何企业名单")
        print("\n建议:")
        print("  1. 检查网络连接")
        print("  2. 稍后再试")
        print("  3. 或使用 main_yfinance.py 手动导入CSV")
        input("\n按回车键退出...")
        exit(1)
    
    # 合并企业名单
    all_companies = pd.concat([df_us, df_hk], ignore_index=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    suffix = "_测试" if TEST_MODE else ""
    
    # 导出企业名单
    company_file = f"中概股企业名单{suffix}_{timestamp}.xlsx"
    all_companies.to_excel(company_file, index=False)
    print(f"\n✅ 企业名单已导出: {company_file}")
    print(f"   总计: {len(all_companies)} 家")
    
    # ==================== 步骤2: 采集财务数据 ====================
    print("\n" + "="*60)
    print("【步骤 2】采集财务数据")
    print("="*60)
    
    # 美股财务数据
    us_financial_data = pd.DataFrame()
    if not df_us.empty:
        us_financial_data = collect_financial_data(df_us, market='US')
    
    # 港股财务数据
    hk_financial_data = pd.DataFrame()
    if not df_hk.empty:
        hk_financial_data = collect_financial_data(df_hk, market='HK')
    
    # 合并并导出
    if not us_financial_data.empty or not hk_financial_data.empty:
        all_financial_data = pd.concat([us_financial_data, hk_financial_data], ignore_index=True)
        
        # 调整列顺序
        columns_order = [
            '股票代码', '股票简称', '币种', '报告期间',
            '总资产', '总负债', '净利润', '营业总收入', '营业总成本',
            '研发费用', '利润总额', '所得税',
            '研发投入占比', '毛利率', '总资产周转率'
        ]
        
        # 如果有数据类型列，也保留
        if '数据类型' in all_financial_data.columns:
            columns_order.insert(4, '数据类型')
        
        all_financial_data = all_financial_data[columns_order]
        
        # 导出Excel
        financial_file = f"中概股财务数据{suffix}_{timestamp}.xlsx"
        
        with pd.ExcelWriter(financial_file, engine='openpyxl') as writer:
            all_financial_data.to_excel(writer, sheet_name='全部财务数据', index=False)
            
            if not us_financial_data.empty:
                us_financial_data[columns_order].to_excel(writer, sheet_name='美股财务数据', index=False)
            
            if not hk_financial_data.empty:
                hk_financial_data[columns_order].to_excel(writer, sheet_name='港股财务数据', index=False)
        
        print(f"\n✅ 财务数据已导出: {financial_file}")
        print(f"   总计: {len(all_financial_data)} 条记录")
    else:
        print("\n⚠️  未获取到任何财务数据")
    
    # ==================== 总结 ====================
    print("\n" + "="*60)
    print("【任务完成总结】")
    print("="*60)
    print(f"✅ 企业名单: {len(all_companies)} 家")
    print(f"   - 美股: {len(df_us)} 家")
    print(f"   - 港股: {len(df_hk)} 家")
    
    if not us_financial_data.empty or not hk_financial_data.empty:
        print(f"✅ 财务数据: {len(all_financial_data)} 条记录")
        print(f"   - 美股记录: {len(us_financial_data)}")
        print(f"   - 港股记录: {len(hk_financial_data)}")
        
        # 成功率统计
        total_companies = len(all_companies)
        companies_with_data = len(all_financial_data[['股票代码']].drop_duplicates())
        success_rate = (companies_with_data / total_companies) * 100 if total_companies > 0 else 0
        print(f"\n📊 数据覆盖率: {companies_with_data}/{total_companies} ({success_rate:.1f}%)")
    
    print(f"\n📁 生成文件:")
    print(f"   1. {company_file}")
    if not us_financial_data.empty or not hk_financial_data.empty:
        print(f"   2. {financial_file}")
    
    print(f"\n完成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    
    if not TEST_MODE:
        print("\n💡 提示:")
        print("   - 部分企业财务数据可能获取失败（正常现象）")
        print("   - 可以重新运行程序获取失败的数据")
        print("   - 或手动补充缺失的数据")
    
    input("\n按回车键退出...")


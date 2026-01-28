"""
美股市场财务数据采集 - 全量美股财报数据

策略：
1. 从 Nasdaq 官方 FTP 自动获取全部美股列表
2. 智能过滤：自动排除 ETF、权证、债券等无财报产品
3. 使用 yfinance 获取完整财务报表数据（资产负债表、利润表、现金流量表）

数据来源：
- Nasdaq Trader FTP: ftp://ftp.nasdaqtrader.com
- 包含 NASDAQ、NYSE、NYSE American、NYSE Arca、BATS、IEX 等所有美国交易所
- 官方数据，每日更新，完全免费

过滤规则：
自动排除以下类型（这些产品没有财务报表）：
- ETF（交易所交易基金）
- Warrant/Rights（认股权证）
- Units（股票+权证组合）
- Preferred Stock（优先股）
- Bond/Note（债券）
- Leveraged Products（杠杆产品）

预期结果：
- 原始股票数：8,000-10,000 只
- 过滤后（有财报）：约 4,000-5,000 只普通股和 ADR
- 成功率：预计 70-85%（部分小型股可能无财报）
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
TEST_LIMIT = 30  # 测试模式下的股票数量

# 财务数据请求延迟
REQUEST_DELAY = 0.5

# 获取名单时的重试次数
MAX_RETRIES = 3

# 是否过滤掉市值过小的股票（建议开启，避免垃圾股）
FILTER_BY_MARKET_CAP = True
MIN_MARKET_CAP = 100_000_000  # 最小市值（美元），1亿美元

# ADR及特殊ticker别名映射表（解决ticker不匹配问题）
# 注意：yfinance 中美股代码通常不需要后缀，直接使用代码即可
# 只有在特殊情况下（如股票代码改变）才需要映射
ADR_ALIAS = {
    # 如果发现某些股票代码在 yfinance 中查不到，可以在这里添加映射
    # 例如：'OLD_CODE': 'NEW_CODE'
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


def clean_stock_name(name):
    """
    清理股票简称，去掉证券类型后缀
    """
    if not isinstance(name, str):
        return name
    
    # 需要去除的后缀模式
    suffixes_to_remove = [
        ' - Common Stock',
        ' - Common Shares',
        ' - Class A Common Stock',
        ' - Class A Ordinary Shares',
        ' - Class B Common Stock',
        ' - American Depositary Shares',
        ' - American Depository Shares',
        ' - Ordinary Shares',
        ' - Depositary Shares',
    ]
    
    cleaned_name = name
    for suffix in suffixes_to_remove:
        if suffix in cleaned_name:
            cleaned_name = cleaned_name.replace(suffix, '')
    
    return cleaned_name.strip()


def get_nasdaq_stocks():
    """从 Nasdaq 官方 FTP 获取 NASDAQ 交易所完整股票列表"""
    print("\n正在从 Nasdaq 官方获取股票列表...")
    
    try:
        # Nasdaq 官方 FTP 服务器提供的股票列表（实时更新）
        url = "ftp://ftp.nasdaqtrader.com/SymbolDirectory/nasdaqlisted.txt"
        
        print("  ⏳ 正在从 Nasdaq FTP 下载...")
        df = pd.read_csv(url, sep='|')
        
        # 移除最后一行（统计信息）
        df = df[:-1]
        
        # 过滤掉测试股票
        df = df[df['Test Issue'] == 'N']
        
        # 过滤掉 ETF（ETF 没有财务报表）
        df = df[df['ETF'] == 'N']
        
        initial_count = len(df)
        
        # 过滤掉特殊证券类型（这些通常没有完整财务报表）
        # 排除：Warrant, Right, Unit, Preferred Stock 等
        exclude_keywords = [
            'ETF', 'Fund', 'Trust',  # 基金类
            'Warrant', 'Rights', 'Right',  # 权证类
            'Unit', 'Units',  # 单位（通常是股票+权证组合）
            'Preferred',  # 优先股
            'Note', 'Bond', 'Debenture',  # 债券类
            'Index', 'Leverag',  # 指数和杠杆产品
        ]
        
        # 基于证券名称过滤
        for keyword in exclude_keywords:
            df = df[~df['Security Name'].str.contains(keyword, case=False, na=False)]
        
        filtered_count = initial_count - len(df)
        
        result = pd.DataFrame()
        result['股票代码'] = df['Symbol']
        result['股票简称'] = df['Security Name'].apply(clean_stock_name)  # 简称去掉后缀
        result['企业全称'] = df['Security Name']  # 全称保留后缀
        result['上市交易所'] = 'NASDAQ'
        result['币种'] = 'USD'
        
        print(f"  ✅ NASDAQ: {len(result)} 只股票（过滤掉 {filtered_count} 只 ETF/权证等）")
        return result
        
    except Exception as e:
        print(f"  ❌ Nasdaq 获取失败: {e}")
        return pd.DataFrame()


def get_nyse_stocks():
    """从 Nasdaq 官方 FTP 获取 NYSE 和其他交易所的股票列表"""
    print("\n正在从 Nasdaq 官方获取 NYSE 等交易所股票列表...")
    
    try:
        # 包含 NYSE, NYSE American, NYSE Arca 等交易所
        url = "ftp://ftp.nasdaqtrader.com/SymbolDirectory/otherlisted.txt"
        
        print("  ⏳ 正在从 Nasdaq FTP 下载...")
        df = pd.read_csv(url, sep='|')
        
        # 移除最后一行
        df = df[:-1]
        
        # 过滤掉测试股票
        df = df[df['Test Issue'] == 'N']
        
        # 过滤掉 ETF
        df = df[df['ETF'] == 'N']
        
        initial_count = len(df)
        
        # 过滤掉特殊证券类型（没有完整财务报表的）
        exclude_keywords = [
            'ETF', 'Fund', 'Trust',  # 基金类
            'Warrant', 'Rights', 'Right',  # 权证类
            'Unit', 'Units',  # 单位
            'Preferred',  # 优先股
            'Note', 'Bond', 'Debenture',  # 债券类
            'Index', 'Leverag',  # 指数和杠杆产品
        ]
        
        # 基于证券名称过滤
        for keyword in exclude_keywords:
            df = df[~df['Security Name'].str.contains(keyword, case=False, na=False)]
        
        filtered_count = initial_count - len(df)
        
        result = pd.DataFrame()
        result['股票代码'] = df['ACT Symbol']
        result['股票简称'] = df['Security Name'].apply(clean_stock_name)  # 简称去掉后缀
        result['企业全称'] = df['Security Name']  # 全称保留后缀
        result['上市交易所'] = df['Exchange']
        result['币种'] = 'USD'
        
        print(f"  ✅ NYSE等交易所: {len(result)} 只股票（过滤掉 {filtered_count} 只 ETF/权证等）")
        
        # 显示交易所分布
        exchange_map = {
            'A': 'NYSE American',
            'N': 'NYSE',
            'P': 'NYSE Arca',
            'Z': 'BATS',
            'V': 'IEX'
        }
        result['上市交易所'] = result['上市交易所'].map(exchange_map).fillna(result['上市交易所'])
        
        print("  📊 交易所分布:")
        for exchange, count in result['上市交易所'].value_counts().items():
            print(f"     {exchange}: {count} 只")
        
        return result
        
    except Exception as e:
        print(f"  ❌ NYSE等交易所获取失败: {e}")
        return pd.DataFrame()


def get_all_us_stocks():
    """
    从 Nasdaq 官方 FTP 获取全部美国市场股票列表
    
    数据源：Nasdaq Trader FTP 服务器（官方、实时、免费）
    - ftp://ftp.nasdaqtrader.com/SymbolDirectory/
    - 包含 NASDAQ、NYSE、NYSE American、NYSE Arca、BATS、IEX 等所有美国交易所
    - 每日更新，包含约 8,000-10,000 只股票
    """
    print("\n正在获取美国市场全部股票列表...")
    print("="*60)
    print("📍 数据源：Nasdaq 官方 FTP 服务器")
    
    all_stocks = []
    
    # 获取 NASDAQ 交易所股票
    nasdaq_stocks = get_nasdaq_stocks()
    if not nasdaq_stocks.empty:
        all_stocks.append(nasdaq_stocks)
    
    # 获取 NYSE 等其他交易所股票
    nyse_stocks = get_nyse_stocks()
    if not nyse_stocks.empty:
        all_stocks.append(nyse_stocks)
    
    if not all_stocks:
        print("\n  ❌ 从官方源获取失败")
        print("\n  可能原因:")
        print("  1. 网络连接问题")
        print("  2. 防火墙阻止 FTP 连接（端口 21）")
        print("  3. FTP 服务器暂时不可用")
        print("\n  建议:")
        print("  - 检查网络连接")
        print("  - 检查防火墙设置")
        print("  - 稍后重试")
        
        return pd.DataFrame()
    
    # 合并所有交易所数据
    result = pd.concat(all_stocks, ignore_index=True)
    
    print("\n" + "="*60)
    print(f"✅ 总计: {len(result)} 只美股")
    
    # 去重（基于股票代码）
    initial_count = len(result)
    result = result.drop_duplicates(subset=['股票代码'], keep='first')
    if initial_count != len(result):
        print(f"   去重: {initial_count} → {len(result)} 只")
    
    # 按交易所统计
    print("\n📊 交易所分布:")
    for exchange, count in result['上市交易所'].value_counts().items():
        print(f"   {exchange}: {count} 只")
    
    # 测试模式截断
    if TEST_MODE:
        print(f"\n🚩 [测试模式] 仅使用前 {TEST_LIMIT} 只股票")
        result = result.head(TEST_LIMIT)
    
    print(f"\n📊 最终股票数: {len(result)} 只")
    
    return result


def get_us_stocks_list_old():
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


def get_financial_data_hk_akshare(stock_code, stock_name, exchange='HKEX'):
    """
    使用akshare获取港股财务数据（备用函数，当前未使用）
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
                    '交易所': exchange,
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


def get_financial_data_yfinance(stock_code, stock_name, market='US', exchange='US', company_full_name=''):
    """
    使用yfinance获取完整财务报表数据
    
    改进：
    1. ADR别名映射
    2. 季度失败→年报兜底
    3. 失败原因分级
    4. 修复港股代码重复后缀问题
    5. 添加完整的资产负债表、利润表、现金流量表字段
    """
    fail_reason = None
    
    try:
        # 清理股票代码中的不可见字符（零宽字符等）
        stock_code = ''.join(c for c in str(stock_code) if c.isprintable()).strip()
        
        # 根据交易所调整股票代码格式
        exchange_lower = str(exchange).lower()
        
        if 'hk' in exchange_lower or '港' in str(exchange):
            # 港股：保持 .HK 后缀
            if '.HK' in stock_code.upper():
                code = stock_code
            else:
                code = stock_code.zfill(5) + '.HK'
            market = 'HK'
        elif 'sh' in exchange_lower or '沪' in str(exchange):
            # 上交所：添加 .SS 后缀
            if '.SS' in stock_code.upper():
                code = stock_code
            else:
                code = stock_code + '.SS'
            market = 'CN'
        elif 'sz' in exchange_lower or '深' in str(exchange):
            # 深交所：添加 .SZ 后缀
            if '.SZ' in stock_code.upper():
                code = stock_code
            else:
                code = stock_code + '.SZ'
            market = 'CN'
        elif 'six' in exchange_lower or '瑞士' in str(exchange):
            # 瑞士证券交易所：将 .SIX 替换为 .SW（yfinance 格式）
            if stock_code.upper().endswith('.SIX'):
                code = stock_code[:-4] + '.SW'  # .SIX → .SW
            elif not stock_code.upper().endswith('.SW'):
                code = stock_code + '.SW'
            else:
                code = stock_code
            code = ADR_ALIAS.get(code, code)
            market = 'EU'
        elif 'nyse' in exchange_lower or '纽约' in str(exchange):
            # 纽约证券交易所：去除 .N 后缀
            if stock_code.upper().endswith('.N'):
                code = stock_code[:-2]
            else:
                code = stock_code
            code = ADR_ALIAS.get(code, code)
            market = 'US'
        elif 'nasdaq' in exchange_lower or '纳斯达克' in str(exchange):
            # 纳斯达克：去除 .O 后缀
            if stock_code.upper().endswith('.O'):
                code = stock_code[:-2]
            else:
                code = stock_code
            code = ADR_ALIAS.get(code, code)
            market = 'US'
        else:
            # 其他市场：尝试去除常见后缀
            clean_code = stock_code
            for suffix in ['.O', '.N', '.A', '.K', '.Z']:
                if clean_code.upper().endswith(suffix):
                    clean_code = clean_code[:-2]
                    break
            code = ADR_ALIAS.get(clean_code, clean_code)
            market = 'US'
        
        # 创建股票对象
        ticker = yf.Ticker(code)
        
        # 先检查股票是否存在（避免 404 错误）
        try:
            info = ticker.info
            if not info or len(info) <= 1:
                # 股票不存在
                return pd.DataFrame()
        except:
            # 获取信息失败
            return pd.DataFrame()
        
        # ========== 获取三大报表数据 ==========
        # 优先尝试季度数据
        try:
            quarterly_income = ticker.quarterly_income_stmt
            quarterly_balance = ticker.quarterly_balance_sheet
            quarterly_cashflow = ticker.quarterly_cashflow
            is_quarterly = True
        except:
            quarterly_income = pd.DataFrame()
            quarterly_balance = pd.DataFrame()
            quarterly_cashflow = pd.DataFrame()
            is_quarterly = False
        
        # 如果季度数据为空，降级到年报
        if quarterly_income.empty:
            try:
                quarterly_income = ticker.income_stmt
                quarterly_balance = ticker.balance_sheet
                quarterly_cashflow = ticker.cashflow
                is_quarterly = False
            except:
                fail_reason = 'NO_DATA'
                return pd.DataFrame()
        
        # 如果年报也为空，彻底失败
        if quarterly_income.empty:
            fail_reason = 'NO_YAHOO'
            return pd.DataFrame()
        
        financial_records = []
        
        # 根据市场确定币种和单位
        if market == 'HK':
            currency = 'HKD'
            unit = '港元'
        elif market == 'CN':
            currency = 'CNY'
            unit = '人民币元'
        else:
            currency = 'USD'
            unit = '美元'
        
        # 处理数据（季度或年度）
        if not quarterly_income.empty:
            for date_col in quarterly_income.columns[:8]:  # 最近8个报告期
                try:
                    # ========== 资产负债表数据 ==========
                    balance_data = {}
                    if not quarterly_balance.empty and date_col in quarterly_balance.columns:
                        # 货币资金
                        balance_data['货币资金'] = quarterly_balance.loc['Cash And Cash Equivalents', date_col] if 'Cash And Cash Equivalents' in quarterly_balance.index else None
                        
                        # 流动资产
                        balance_data['流动资产'] = quarterly_balance.loc['Current Assets', date_col] if 'Current Assets' in quarterly_balance.index else None
                        
                        # 非流动资产 = 总资产 - 流动资产
                        total_assets = quarterly_balance.loc['Total Assets', date_col] if 'Total Assets' in quarterly_balance.index else None
                        current_assets = balance_data['流动资产']
                        if total_assets and current_assets:
                            balance_data['非流动资产'] = total_assets - current_assets
                        else:
                            balance_data['非流动资产'] = None
                        
                        balance_data['总资产'] = total_assets
                        
                        # 实收资本 (普通股)
                        balance_data['实收资本'] = quarterly_balance.loc['Common Stock', date_col] if 'Common Stock' in quarterly_balance.index else None
                        
                        # 资本公积
                        balance_data['资本公积'] = quarterly_balance.loc['Capital Stock', date_col] if 'Capital Stock' in quarterly_balance.index else (
                            quarterly_balance.loc['Additional Paid In Capital', date_col] if 'Additional Paid In Capital' in quarterly_balance.index else None
                        )
                        
                        # 股东权益合计
                        balance_data['股东权益合计'] = quarterly_balance.loc['Stockholders Equity', date_col] if 'Stockholders Equity' in quarterly_balance.index else (
                            quarterly_balance.loc['Total Equity Gross Minority Interest', date_col] if 'Total Equity Gross Minority Interest' in quarterly_balance.index else None
                        )
                        
                        # 流动负债
                        balance_data['流动负债'] = quarterly_balance.loc['Current Liabilities', date_col] if 'Current Liabilities' in quarterly_balance.index else None
                        
                        # 总负债
                        total_liabilities = quarterly_balance.loc['Total Liabilities Net Minority Interest', date_col] if 'Total Liabilities Net Minority Interest' in quarterly_balance.index else None
                        balance_data['总负债'] = total_liabilities
                        
                        # 非流动负债 = 总负债 - 流动负债
                        current_liabilities = balance_data['流动负债']
                        if total_liabilities and current_liabilities:
                            balance_data['非流动负债'] = total_liabilities - current_liabilities
                        else:
                            balance_data['非流动负债'] = None
                    
                    # ========== 现金流量表数据 ==========
                    cashflow_data = {}
                    if not quarterly_cashflow.empty and date_col in quarterly_cashflow.columns:
                        # 经营活动现金流
                        operating_cf = quarterly_cashflow.loc['Operating Cash Flow', date_col] if 'Operating Cash Flow' in quarterly_cashflow.index else None
                        cashflow_data['经营活动产生的现金流量净额'] = operating_cf
                        
                        # 经营性现金流入/流出 (yfinance通常不直接提供，用净额表示)
                        if operating_cf:
                            if operating_cf >= 0:
                                cashflow_data['经营性现金流入'] = operating_cf
                                cashflow_data['经营性现金流出'] = 0
                            else:
                                cashflow_data['经营性现金流入'] = 0
                                cashflow_data['经营性现金流出'] = abs(operating_cf)
                        else:
                            cashflow_data['经营性现金流入'] = None
                            cashflow_data['经营性现金流出'] = None
                        
                        # 投资活动现金流
                        investing_cf = quarterly_cashflow.loc['Investing Cash Flow', date_col] if 'Investing Cash Flow' in quarterly_cashflow.index else None
                        cashflow_data['投资活动产生的现金流量净额'] = investing_cf
                        
                        if investing_cf:
                            if investing_cf >= 0:
                                cashflow_data['投资活动现金流入'] = investing_cf
                                cashflow_data['投资活动现金流出'] = 0
                            else:
                                cashflow_data['投资活动现金流入'] = 0
                                cashflow_data['投资活动现金流出'] = abs(investing_cf)
                        else:
                            cashflow_data['投资活动现金流入'] = None
                            cashflow_data['投资活动现金流出'] = None
                        
                        # 筹资活动现金流
                        financing_cf = quarterly_cashflow.loc['Financing Cash Flow', date_col] if 'Financing Cash Flow' in quarterly_cashflow.index else None
                        cashflow_data['筹资活动产生的现金流量净额'] = financing_cf
                        
                        if financing_cf:
                            if financing_cf >= 0:
                                cashflow_data['筹资活动现金流入'] = financing_cf
                                cashflow_data['筹资活动现金流出'] = 0
                            else:
                                cashflow_data['筹资活动现金流入'] = 0
                                cashflow_data['筹资活动现金流出'] = abs(financing_cf)
                        else:
                            cashflow_data['筹资活动现金流入'] = None
                            cashflow_data['筹资活动现金流出'] = None
                    
                    # ========== 利润表数据 ==========
                    income_data = {}
                    if not quarterly_income.empty and date_col in quarterly_income.columns:
                        # 净利润
                        income_data['净利润'] = quarterly_income.loc['Net Income', date_col] if 'Net Income' in quarterly_income.index else None
                        
                        # 营业总收入
                        total_revenue = quarterly_income.loc['Total Revenue', date_col] if 'Total Revenue' in quarterly_income.index else None
                        income_data['营业总收入'] = total_revenue
                        
                        # 营业收入 (通常等于营业总收入)
                        income_data['营业收入'] = quarterly_income.loc['Operating Revenue', date_col] if 'Operating Revenue' in quarterly_income.index else total_revenue
                        
                        # 营业总成本
                        total_expenses = quarterly_income.loc['Total Expenses', date_col] if 'Total Expenses' in quarterly_income.index else None
                        income_data['营业总成本'] = total_expenses
                        
                        # 营业成本
                        cost_of_revenue = quarterly_income.loc['Cost Of Revenue', date_col] if 'Cost Of Revenue' in quarterly_income.index else None
                        income_data['营业成本'] = cost_of_revenue
                        
                        # 研发费用
                        rd_expense = quarterly_income.loc['Research And Development', date_col] if 'Research And Development' in quarterly_income.index else None
                        income_data['研发费用'] = rd_expense
                        
                        # 营业税金及附加
                        income_data['营业税金及附加'] = quarterly_income.loc['Tax Effect Of Unusual Items', date_col] if 'Tax Effect Of Unusual Items' in quarterly_income.index else None
                        
                        # 营业利润
                        income_data['营业利润'] = quarterly_income.loc['Operating Income', date_col] if 'Operating Income' in quarterly_income.index else None
                        
                        # 营业外收入
                        income_data['营业外收入'] = quarterly_income.loc['Other Non Operating Income Expenses', date_col] if 'Other Non Operating Income Expenses' in quarterly_income.index else None
                        
                        # 营业外成本 (通常包含在其他费用中)
                        income_data['营业外支出'] = quarterly_income.loc['Other Special Charges', date_col] if 'Other Special Charges' in quarterly_income.index else None
                        
                        # 利润总额
                        pretax_income = quarterly_income.loc['Pretax Income', date_col] if 'Pretax Income' in quarterly_income.index else None
                        income_data['利润总额'] = pretax_income
                        
                        # 所得税
                        tax_provision = quarterly_income.loc['Tax Provision', date_col] if 'Tax Provision' in quarterly_income.index else None
                        income_data['所得税'] = tax_provision
                    
                    # 组合完整记录
                    record = {
                        '证券简称': stock_name,
                        '股票代码': stock_code,
                        '企业全称': company_full_name,
                        '交易所': exchange,
                        '币种': currency,
                        '单位': unit,
                        '报告期间': date_col.strftime('%Y-%m-%d'),
                        '数据类型': 'Q' if is_quarterly else 'A',
                    }
                    
                    # 添加资产负债表字段
                    record.update({
                        '资产负债表.货币资金': balance_data.get('货币资金'),
                        '资产负债表.流动资产': balance_data.get('流动资产'),
                        '资产负债表.非流动资产': balance_data.get('非流动资产'),
                        '资产负债表.总资产': balance_data.get('总资产'),
                        '资产负债表.实收资本': balance_data.get('实收资本'),
                        '资产负债表.资本公积': balance_data.get('资本公积'),
                        '资产负债表.股东权益合计': balance_data.get('股东权益合计'),
                        '资产负债表.流动负债': balance_data.get('流动负债'),
                        '资产负债表.非流动负债': balance_data.get('非流动负债'),
                        '资产负债表.总负债': balance_data.get('总负债'),
                    })
                    
                    # 添加现金流量表字段
                    record.update({
                        '现金流量表.经营性现金流入': cashflow_data.get('经营性现金流入'),
                        '现金流量表.经营性现金流出': cashflow_data.get('经营性现金流出'),
                        '现金流量表.经营活动产生的现金流量净额': cashflow_data.get('经营活动产生的现金流量净额'),
                        '现金流量表.投资活动现金流入': cashflow_data.get('投资活动现金流入'),
                        '现金流量表.投资活动现金流出': cashflow_data.get('投资活动现金流出'),
                        '现金流量表.投资活动产生的现金流量净额': cashflow_data.get('投资活动产生的现金流量净额'),
                        '现金流量表.筹资活动现金流入': cashflow_data.get('筹资活动现金流入'),
                        '现金流量表.筹资活动现金流出': cashflow_data.get('筹资活动现金流出'),
                        '现金流量表.筹资活动产生的现金流量净额': cashflow_data.get('筹资活动产生的现金流量净额'),
                    })
                    
                    # 添加利润表字段
                    record.update({
                        '利润表.净利润': income_data.get('净利润'),
                        '利润表.营业总收入': income_data.get('营业总收入'),
                        '利润表.营业收入': income_data.get('营业收入'),
                        '利润表.营业总成本': income_data.get('营业总成本'),
                        '利润表.营业成本': income_data.get('营业成本'),
                        '利润表.研发费用': income_data.get('研发费用'),
                        '利润表.营业税金及附加': income_data.get('营业税金及附加'),
                        '利润表.营业利润': income_data.get('营业利润'),
                        '利润表.营业外收入': income_data.get('营业外收入'),
                        '利润表.营业外支出': income_data.get('营业外支出'),
                        '利润表.利润总额': income_data.get('利润总额'),
                        '利润表.所得税': income_data.get('所得税'),
                    })
                    
                    # 计算衍生指标
                    total_revenue = income_data.get('营业总收入')
                    rd_expense = income_data.get('研发费用')
                    cost_of_revenue = income_data.get('营业成本')
                    total_assets = balance_data.get('总资产')
                    
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


def collect_financial_data(company_list):
    """批量采集财务数据（增强版：支持多市场）"""
    print(f"\n开始采集财务数据...")
    print(f"共需处理 {len(company_list)} 家企业")
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
        company_full_name = row.get('企业全称', stock_name)
        exchange = row.get('上市交易所', 'US')
        
        print(f"  [{idx+1}/{len(company_list)}] {stock_name} ({stock_code} @ {exchange})...", end=' ')
        
        # 使用 yfinance 获取财务数据（支持多市场）
        financial_df = get_financial_data_yfinance(stock_code, stock_name, exchange=exchange, company_full_name=company_full_name)
        
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
    if quarterly_count > 0 or annual_count > 0:
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
    print("【美股市场财务数据采集系统】")
    print(f"启动时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    print("\n策略说明:")
    print("  - 股票列表: Nasdaq 官方 FTP 获取全部美股")
    print("  - 数据范围: NASDAQ、NYSE、NYSE American、NYSE Arca、BATS、IEX 等")
    print("  - 预计股票数: 8,000 - 10,000 只")
    print("  - 财务数据: yfinance 获取完整财报")
    print("  - 输出数据: 资产负债表、利润表、现金流量表")
    print("="*60)
    
    # 检查依赖
    if not YFINANCE_AVAILABLE:
        print("\n❌ 未安装 yfinance 库")
        print("   请运行: pip install yfinance")
        input("\n按回车键退出...")
        exit(1)
    
    print("\n✅ yfinance 依赖已安装")
    
    if TEST_MODE:
        print(f"\n🚩 测试模式：仅处理 {TEST_LIMIT} 只股票")
        print("   设置 TEST_MODE = False 启用全量模式")
    
    # ==================== 步骤1: 获取股票名单 ====================
    print("\n" + "="*60)
    print("【步骤 1】获取美国市场全部股票")
    print("="*60)
    
    # 获取全部美股列表
    all_companies = get_all_us_stocks()
    
    # 检查是否有数据
    if all_companies.empty:
        print("\n❌ 未能获取任何股票数据")
        print("\n建议:")
        print("  1. 检查网络连接（需要访问 ftp.nasdaqtrader.com）")
        print("  2. 检查防火墙是否允许 FTP 连接（端口 21）")
        print("  3. 稍后重试")
        input("\n按回车键退出...")
        exit(1)
    
    print(f"\n✅ 成功获取 {len(all_companies)} 只美股")
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    suffix = "_测试" if TEST_MODE else "_全量"
    
    # 导出企业名单
    company_file = f"美股企业名单{suffix}_{timestamp}.csv"
    all_companies.to_csv(company_file, index=False, encoding='utf-8-sig')
    print(f"\n✅ 企业名单已导出: {company_file}")
    print(f"   总计: {len(all_companies)} 只美股")
    
    # ==================== 步骤2: 采集财务数据 ====================
    print("\n" + "="*60)
    print("【步骤 2】采集财务数据")
    print("="*60)
    
    # 采集所有股票的财务数据
    all_financial_data = collect_financial_data(all_companies)
    
    # 合并并导出
    if not all_financial_data.empty:
        # 按照用户要求的列顺序调整
        columns_order = [
            # 基本信息
            '证券简称',
            '股票代码',
            '企业全称',
            '交易所',
            '币种',
            '单位',
            '报告期间',
            '数据类型',
            
            # 资产负债表
            '资产负债表.货币资金',
            '资产负债表.流动资产',
            '资产负债表.非流动资产',
            '资产负债表.总资产',
            '资产负债表.实收资本',
            '资产负债表.资本公积',
            '资产负债表.股东权益合计',
            '资产负债表.流动负债',
            '资产负债表.非流动负债',
            '资产负债表.总负债',
            
            # 现金流量表
            '现金流量表.经营性现金流入',
            '现金流量表.经营性现金流出',
            '现金流量表.经营活动产生的现金流量净额',
            '现金流量表.投资活动现金流入',
            '现金流量表.投资活动现金流出',
            '现金流量表.投资活动产生的现金流量净额',
            '现金流量表.筹资活动现金流入',
            '现金流量表.筹资活动现金流出',
            '现金流量表.筹资活动产生的现金流量净额',
            
            # 利润表
            '利润表.净利润',
            '利润表.营业总收入',
            '利润表.营业收入',
            '利润表.营业总成本',
            '利润表.营业成本',
            '利润表.研发费用',
            '利润表.营业税金及附加',
            '利润表.营业利润',
            '利润表.营业外收入',
            '利润表.营业外支出',
            '利润表.利润总额',
            '利润表.所得税',
            
            # 衍生指标
            '研发投入占比',
            '毛利率',
            '总资产周转率',
        ]
        
        # 只保留存在的列
        columns_order = [col for col in columns_order if col in all_financial_data.columns]
        all_financial_data = all_financial_data[columns_order]
        
        # 导出CSV
        financial_file = f"美股财务数据{suffix}_{timestamp}.csv"
        
        # 导出主文件
        all_financial_data.to_csv(financial_file, index=False, encoding='utf-8-sig')
        print(f"\n✅ 财务数据已导出: {financial_file}")
        print(f"   总计: {len(all_financial_data)} 条记录")
        
        # 注意：由于数据量可能很大，全量美股财报文件会非常大
        # 建议使用数据库或者按批次处理
    else:
        print("\n⚠️  未获取到任何财务数据")
    
    # ==================== 总结 ====================
    print("\n" + "="*60)
    print("【任务完成总结】")
    print("="*60)
    print(f"✅ 美股总数: {len(all_companies)} 只")
    
    if not all_financial_data.empty:
        print(f"\n✅ 财务数据: {len(all_financial_data)} 条记录")
        
        # 成功率统计
        total_companies = len(all_companies)
        companies_with_data = len(all_financial_data[['股票代码']].drop_duplicates())
        success_rate = (companies_with_data / total_companies) * 100 if total_companies > 0 else 0
        print(f"\n📊 数据覆盖率: {companies_with_data}/{total_companies} ({success_rate:.1f}%)")
        
        # 数据类型统计
        if '数据类型' in all_financial_data.columns:
            data_type_counts = all_financial_data['数据类型'].value_counts()
            print(f"\n📈 数据类型分布:")
            for dtype, count in data_type_counts.items():
                type_name = "季度" if dtype == 'Q' else "年度"
                print(f"   - {type_name}数据: {count} 条")
    
    print(f"\n📁 生成文件:")
    print(f"   1. {company_file}")
    if not all_financial_data.empty:
        print(f"   2. {financial_file}")
    
    print(f"\n完成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    
    print("\n💡 提示:")
    if TEST_MODE:
        print("   - 当前为测试模式，仅处理部分股票")
        print("   - 设置 TEST_MODE = False 可获取全量数据")
    else:
        print("   - 全量模式：处理全部美股（可能需要数小时）")
        print("   - 建议首次使用测试模式验证流程")
    print("   - 部分企业财务数据可能获取失败（正常现象）")
    print("   - yfinance 有访问频率限制，请合理设置延迟")
    print("   - 生成的CSV文件可能很大，建议使用数据库存储")
    
    input("\n按回车键退出...")


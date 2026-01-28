"""
美股市场市值和市盈率数据采集 - 全量美股估值数据

策略：
1. 从 Nasdaq 官方 FTP 自动获取全部美股列表
2. 智能过滤：自动排除 ETF、权证、债券等无估值意义的产品
3. 使用 yfinance 获取市值和市盈率
4. 每只股票一行记录，记录获取时间（YYYY-MM-DD格式）

数据来源：
- Nasdaq Trader FTP: ftp://ftp.nasdaqtrader.com
- 包含 NASDAQ、NYSE、NYSE American、NYSE Arca、BATS、IEX 等所有美国交易所
- 官方数据，每日更新，完全免费

过滤规则：
自动排除以下类型：
- ETF（交易所交易基金）
- Warrant/Rights（认股权证）
- Units（股票+权证组合）
- Preferred Stock（优先股）
- Bond/Note（债券）
- Leveraged Products（杠杆产品）

预期结果：
- 原始股票数：8,000-10,000 只
- 过滤后：约 4,000-5,000 只普通股和 ADR
- 成功率：预计 85-95%（市值数据通常更完整）
"""

import pandas as pd
from datetime import datetime
import time
import math
import warnings
warnings.filterwarnings('ignore')

try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False
    print("❌ yfinance未安装，请运行: pip install yfinance")

# ================= 配置区 =================
TEST_MODE = True
TEST_LIMIT = 30  # 测试模式下的数量

# 是否过滤掉 ETF、权证等无估值意义的产品（强烈建议开启）
FILTER_NON_STOCKS = True  # True=只获取普通股, False=获取所有证券

# 请求延迟
REQUEST_DELAY = 0.5

# ADR及特殊ticker别名映射表
ADR_ALIAS = {
    # 如果发现某些股票代码在 yfinance 中查不到，可以在这里添加映射
}


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
        
        initial_count = len(df)
        filtered_count = 0
        
        # 根据配置决定是否过滤
        if FILTER_NON_STOCKS:
            # 过滤掉 ETF（ETF 没有财务报表）
            df = df[df['ETF'] == 'N']
            
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
        
        if FILTER_NON_STOCKS and filtered_count > 0:
            print(f"  ✅ NASDAQ: {len(result)} 只股票（过滤掉 {filtered_count} 只 ETF/权证等）")
        else:
            print(f"  ✅ NASDAQ: {len(result)} 只股票")
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
        
        initial_count = len(df)
        filtered_count = 0
        
        # 根据配置决定是否过滤
        if FILTER_NON_STOCKS:
            # 过滤掉 ETF
            df = df[df['ETF'] == 'N']
            
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
        
        if FILTER_NON_STOCKS and filtered_count > 0:
            print(f"  ✅ NYSE等交易所: {len(result)} 只股票（过滤掉 {filtered_count} 只 ETF/权证等）")
        else:
            print(f"  ✅ NYSE等交易所: {len(result)} 只股票")
        
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
    - 每日更新，包含约 4,000-5,000 只普通股（过滤后）
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
        print("\n❌ 未能获取任何股票数据")
        return pd.DataFrame()
    
    # 合并所有数据
    result = pd.concat(all_stocks, ignore_index=True)
    
    # 去重（基于股票代码）
    result = result.drop_duplicates(subset=['股票代码'], keep='first')
    
    print("\n" + "="*60)
    print(f"✅ 总计: {len(result)} 只美股")
    print("="*60)
    
    # 显示交易所分布统计
    print("\n📊 交易所分布汇总:")
    for exchange, count in result['上市交易所'].value_counts().items():
        print(f"   {exchange}: {count} 只")
    
    # 测试模式截断
    if TEST_MODE:
        print(f"\n🚩 [测试模式] 仅使用前 {TEST_LIMIT} 只股票")
        result = result.head(TEST_LIMIT)
    
    return result


def get_stock_value_data(stock_code, stock_name, company_full_name, exchange, fetch_date):
    """
    获取单只股票的市值和市盈率
    """
    try:
        # 清理股票代码中的不可见字符
        stock_code = ''.join(c for c in str(stock_code) if c.isprintable()).strip()
        
        # 根据交易所调整股票代码格式
        exchange_lower = str(exchange).lower()
        
        if 'hk' in exchange_lower or '港' in str(exchange):
            # 港股：保持 .HK 后缀
            if '.HK' in stock_code.upper():
                code = stock_code
            else:
                code = stock_code.zfill(5) + '.HK'
        elif 'sh' in exchange_lower or '沪' in str(exchange):
            # 上交所：添加 .SS 后缀
            if '.SS' in stock_code.upper():
                code = stock_code
            else:
                code = stock_code + '.SS'
        elif 'sz' in exchange_lower or '深' in str(exchange):
            # 深交所：添加 .SZ 后缀
            if '.SZ' in stock_code.upper():
                code = stock_code
            else:
                code = stock_code + '.SZ'
        elif 'six' in exchange_lower or '瑞士' in str(exchange):
            # 瑞士证券交易所：将 .SIX 替换为 .SW（yfinance 格式）
            if stock_code.upper().endswith('.SIX'):
                code = stock_code[:-4] + '.SW'  # .SIX → .SW
            elif not stock_code.upper().endswith('.SW'):
                code = stock_code + '.SW'
            else:
                code = stock_code
            code = ADR_ALIAS.get(code, code)
        elif 'nyse' in exchange_lower or '纽约' in str(exchange):
            # 纽约证券交易所：去除 .N 后缀（yfinance 不需要）
            if stock_code.upper().endswith('.N'):
                code = stock_code[:-2]
            else:
                code = stock_code
            code = ADR_ALIAS.get(code, code)
        elif 'nasdaq' in exchange_lower or '纳斯达克' in str(exchange):
            # 纳斯达克：去除 .O 后缀
            if stock_code.upper().endswith('.O'):
                code = stock_code[:-2]
            else:
                code = stock_code
            code = ADR_ALIAS.get(code, code)
        else:
            # 其他市场：尝试去除常见后缀
            clean_code = stock_code
            for suffix in ['.O', '.N', '.A', '.K', '.Z']:
                if clean_code.upper().endswith(suffix):
                    clean_code = clean_code[:-2]
                    break
            code = ADR_ALIAS.get(clean_code, clean_code)
        
        # 获取股票信息（添加超时和错误处理）
        ticker = yf.Ticker(code)
        info = ticker.info
        
        # 检查是否获取到有效数据
        if not info or len(info) <= 1:
            # info 为空或只有 symbol 字段，说明股票不存在
            raise ValueError(f"No data available for {code}")
        
        # 提取市值和市盈率
        market_cap = info.get('marketCap', None)
        pe_ratio = info.get('trailingPE', None) or info.get('forwardPE', None)
        
        # 处理市值的异常值
        if market_cap is not None:
            if math.isinf(market_cap) or math.isnan(market_cap):
                market_cap = None
        
        # 处理市盈率的异常值（infinity, -infinity, NaN）
        if pe_ratio is not None:
            # 检查是否为无穷大、无穷小或 NaN
            if math.isinf(pe_ratio) or math.isnan(pe_ratio):
                pe_ratio = None
            # 检查是否为异常的极值（市盈率通常在 -100 到 1000 之间是合理的）
            elif pe_ratio > 10000 or pe_ratio < -1000:
                pe_ratio = None
        
        return {
            '股票代码': stock_code,
            '股票简称': stock_name,
            '企业全称': company_full_name,
            '上市交易所': exchange,
            '获取时间': fetch_date,
            '市值': market_cap,
            '市盈率': pe_ratio,
        }
        
    except Exception as e:
        return {
            '股票代码': stock_code,
            '股票简称': stock_name,
            '企业全称': company_full_name,
            '上市交易所': exchange,
            '获取时间': fetch_date,
            '市值': None,
            '市盈率': None,
        }


def collect_value_data(company_list):
    """批量采集市值和市盈率数据"""
    # 获取当前日期（格式：YYYY-MM-DD）
    fetch_date = datetime.now().strftime('%Y-%m-%d')
    
    print(f"\n开始采集市值和市盈率数据...")
    print(f"共需处理 {len(company_list)} 家企业")
    print(f"数据源: yfinance")
    print(f"获取时间: {fetch_date}")
    print()
    
    all_data = []
    success_count = 0
    fail_count = 0
    
    for idx, row in company_list.iterrows():
        stock_code = row['股票代码']
        stock_name = row['股票简称']
        company_full_name = row.get('企业全称', stock_name)
        exchange = row.get('上市交易所', 'US')
        
        print(f"  [{idx+1}/{len(company_list)}] {stock_name} ({stock_code} @ {exchange})...", end=' ')
        
        result = get_stock_value_data(stock_code, stock_name, company_full_name, exchange, fetch_date)
        
        if result['市值'] is not None or result['市盈率'] is not None:
            success_count += 1
            print(f"✅ 市值: {result['市值']}, PE: {result['市盈率']}")
        else:
            fail_count += 1
            print(f"❌ 失败")
        
        all_data.append(result)
        time.sleep(REQUEST_DELAY)
    
    print(f"\n采集完成: 成功 {success_count} 家, 失败 {fail_count} 家")
    print(f"  成功率: {success_count}/{len(company_list)} = {success_count/len(company_list)*100:.1f}%")
    
    return pd.DataFrame(all_data)


# ==================== 主程序 ====================

if __name__ == "__main__":
    # 检查依赖
    if not YFINANCE_AVAILABLE:
        print("\n❌ 未安装 yfinance 库")
        print("   请运行: pip install yfinance")
        input("\n按回车键退出...")
        exit(1)
    
    print("\n✅ yfinance 依赖已安装")
    
    print("\n" + "="*60)
    print("【美股市场市值数据采集系统】")
    print(f"启动时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    print("\n策略说明:")
    print("  - 股票列表: Nasdaq 官方 FTP 获取全部美股")
    print("  - 数据范围: NASDAQ、NYSE、NYSE American、NYSE Arca、BATS、IEX 等")
    if FILTER_NON_STOCKS:
        print("  - 智能过滤: ✅ 已启用（排除 ETF、权证、债券等）")
        print("  - 预计股票数: 4,000 - 5,000 只（普通股+ADR）")
    else:
        print("  - 智能过滤: ❌ 未启用（包含所有证券类型）")
        print("  - 预计股票数: 8,000 - 10,000 只（包含 ETF 等）")
    print("  - 获取数据: 市值、市盈率")
    print("="*60)
    
    if TEST_MODE:
        print(f"\n🚩 测试模式：前 {TEST_LIMIT} 只股票")
        print("   设置 TEST_MODE = False 启用全量模式")
    
    # ==================== 步骤1: 获取股票名单 ====================
    print("\n" + "="*60)
    print("【步骤 1】从 Nasdaq 官方 FTP 获取股票列表")
    print("="*60)
    
    all_companies = get_all_us_stocks()
    
    if all_companies.empty:
        print("\n❌ 未能获取任何股票数据")
        print("\n建议:")
        print("  1. 检查网络连接")
        print("  2. 确认能访问 ftp://ftp.nasdaqtrader.com")
        print("  3. 稍后重试")
        input("\n按回车键退出...")
        exit(1)
    
    print(f"\n✅ 成功获取 {len(all_companies)} 只股票")
    
    # ==================== 步骤2: 采集市值和市盈率数据 ====================
    print("\n" + "="*60)
    print("【步骤 2】采集市值和市盈率数据")
    print("="*60)
    
    value_data = collect_value_data(all_companies)
    
    if not value_data.empty:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        suffix = "_测试" if TEST_MODE else ""
        fetch_date = value_data['获取时间'].iloc[0] if not value_data.empty else datetime.now().strftime('%Y-%m-%d')
        
        # 导出CSV
        value_file = f"美股市值数据{suffix}_{timestamp}.csv"
        value_data.to_csv(value_file, index=False, encoding='utf-8-sig')
        
        print(f"\n✅ 市值数据已导出: {value_file}")
        print(f"   总计: {len(value_data)} 家企业")
        print(f"   获取时间: {fetch_date}")
        
        # 统计有效数据
        valid_market_cap = value_data['市值'].notna().sum()
        valid_pe = value_data['市盈率'].notna().sum()
        print(f"\n📊 数据统计:")
        print(f"   市值有效: {valid_market_cap}/{len(value_data)} ({valid_market_cap/len(value_data)*100:.1f}%)")
        print(f"   市盈率有效: {valid_pe}/{len(value_data)} ({valid_pe/len(value_data)*100:.1f}%)")
    else:
        print("\n⚠️  未获取到任何数据")
    
    # ==================== 总结 ====================
    print("\n" + "="*60)
    print("【任务完成总结】")
    print("="*60)
    
    if not value_data.empty:
        print(f"✅ 企业数量: {len(value_data)} 家")
        print(f"📁 生成文件: {value_file}")
    
    print(f"\n完成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    
    if not TEST_MODE:
        print("\n💡 提示:")
        print("   - 全量模式预计需要 30-60 分钟（取决于网络速度）")
        print("   - 预计成功率 85-95%（市值数据通常更完整）")
        print("   - 输出文件大小约 1-2 MB（CSV 格式）")
        print("   - 可以定期运行以获取最新市值数据")
    else:
        print("\n💡 提示:")
        print("   - 测试模式已完成，可设置 TEST_MODE = False 启用全量模式")
        print("   - 全量模式将获取 4,000-5,000 只美股的市值数据")
    
    input("\n按回车键退出...")

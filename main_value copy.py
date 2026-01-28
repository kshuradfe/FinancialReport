"""
股票市值和市盈率数据采集

策略：
1. 从 Company_List.xlsx 读取股票列表（包括美股、港股、其他国家）
2. 使用 yfinance 获取市值和市盈率
3. 每只股票只有一行记录
4. 记录获取时间（YYYY-MM-DD格式），方便追踪时点数据

优点：
- 快速获取市值和估值数据
- 每只股票一行，便于查看
- 记录获取时间，便于历史数据对比
- 与财务报表数据分离
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
TEST_MODE = False
TEST_LIMIT = 30  # 测试模式下的数量

# 公司列表文件路径
COMPANY_LIST_FILE = "Company_List.xlsx"

# 请求延迟
REQUEST_DELAY = 0.5

# ADR及特殊ticker别名映射表
ADR_ALIAS = {
    # 如果发现某些股票代码在 yfinance 中查不到，可以在这里添加映射
}


def get_stocks_from_excel():
    """
    从 Company_List.xlsx 读取股票列表
    """
    print(f"\n正在从 {COMPANY_LIST_FILE} 读取股票列表...")
    
    try:
        df = pd.read_excel(COMPANY_LIST_FILE)
        print(f"  ✅ 读取成功: {len(df)} 只股票")
        
        # 检查必需的列
        required_columns = ['code', 'exchange']
        if not all(col in df.columns for col in required_columns):
            print(f"  ❌ 缺少必需列: {required_columns}")
            return pd.DataFrame()
        
        # 显示交易所分布
        print("\n  📊 交易所分布:")
        exchange_counts = df['exchange'].value_counts()
        for exchange, count in exchange_counts.items():
            print(f"     {exchange}: {count} 只")
        
        # 标准化列名
        result = pd.DataFrame()
        result['股票代码'] = df['code'].astype(str)
        result['股票简称'] = df['short'] if 'short' in df.columns else (df['name'] if 'name' in df.columns else df['code'])
        result['企业全称'] = df['name'] if 'name' in df.columns else result['股票简称']
        result['上市交易所'] = df['exchange']
        
        # 测试模式截断
        if TEST_MODE:
            print(f"\n  [测试模式] 仅使用前 {TEST_LIMIT} 只股票")
            result = result.head(TEST_LIMIT)
        
        return result
        
    except FileNotFoundError:
        print(f"  ❌ 文件未找到: {COMPANY_LIST_FILE}")
        return pd.DataFrame()
    except Exception as e:
        print(f"  ❌ 读取失败: {e}")
        return pd.DataFrame()


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
    print("\n" + "="*60)
    print("【股票市值和市盈率数据采集系统】")
    print(f"启动时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    print("\n策略说明:")
    print(f"  - 股票列表: 从 {COMPANY_LIST_FILE} 读取")
    print("  - 数据源: yfinance")
    print("  - 输出: 获取时间、市值、市盈率")
    print(f"  - 获取时间格式: YYYY-MM-DD")
    print("="*60)
    
    # 检查依赖
    if not YFINANCE_AVAILABLE:
        print("\n❌ 未安装 yfinance 库")
        print("   请运行: pip install yfinance")
        input("\n按回车键退出...")
        exit(1)
    
    print("\n✅ yfinance 依赖已安装")
    
    if TEST_MODE:
        print(f"\n🚩 测试模式：{TEST_LIMIT} 家企业")
        print("   设置 TEST_MODE = False 启用全量模式")
    
    # ==================== 步骤1: 获取股票名单 ====================
    print("\n" + "="*60)
    print("【步骤 1】从Excel读取股票名单")
    print("="*60)
    
    all_companies = get_stocks_from_excel()
    
    if all_companies.empty:
        print("\n❌ 未能读取任何股票数据")
        print("\n建议:")
        print(f"  1. 检查文件是否存在: {COMPANY_LIST_FILE}")
        print("  2. 检查文件格式是否正确（需要包含 code 和 exchange 列）")
        input("\n按回车键退出...")
        exit(1)
    
    print(f"\n✅ 成功读取 {len(all_companies)} 只股票")
    
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
        value_file = f"股票市值数据{suffix}_{timestamp}.csv"
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
        print("   - 部分企业数据可能获取失败（正常现象）")
        print("   - 可以重新运行程序获取失败的数据")
    
    input("\n按回车键退出...")

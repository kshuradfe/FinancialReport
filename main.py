import akshare as ak
import pandas as pd
from datetime import datetime
import time
import warnings
warnings.filterwarnings('ignore')

# ================= 配置区 =================
# True: 开启测试模式 (只抓取少量数据快速验证)
# False: 生产模式 (抓取全量数据)
TEST_MODE = True

# 测试模式下每个市场抓取的数量
TEST_LIMIT = 10

# 财务数据抓取时的请求间隔（秒）
REQUEST_DELAY = 1

# 手动导入的企业名单文件（CSV格式，可选）
# 如果API获取失败，可以手动准备CSV文件并设置路径
MANUAL_US_STOCKS_CSV = ""  # 例如: "us_stocks.csv"
MANUAL_HK_STOCKS_CSV = ""  # 例如: "hk_stocks.csv"

# =========================================


def load_stocks_from_csv(csv_file, market_name='US', currency='USD'):
    """
    从CSV文件加载企业名单
    
    CSV格式要求：
    股票代码,股票简称
    BABA,阿里巴巴
    """
    try:
        if not csv_file or not pd.io.common.file_exists(csv_file):
            return pd.DataFrame()
        
        print(f"  正在从文件加载: {csv_file}")
        df = pd.read_csv(csv_file)
        
        # 确保必需列存在
        if '股票代码' not in df.columns or '股票简称' not in df.columns:
            print(f"  ❌ CSV文件格式错误，必须包含'股票代码'和'股票简称'列")
            return pd.DataFrame()
        
        # 补充其他列
        result = pd.DataFrame()
        result['股票代码'] = df['股票代码']
        result['股票简称'] = df['股票简称']
        result['上市交易所'] = df.get('上市交易所', 'NASDAQ/NYSE' if market_name == 'US' else 'HKEX')
        result['上市状态'] = df.get('上市状态', '正常')
        result['上市日期'] = df.get('上市日期', '')
        result['上市板块'] = df.get('上市板块', '')
        result['上市企业全称'] = df.get('上市企业全称', '')
        result['对应大陆企业全称'] = df.get('对应大陆企业全称', '')
        result['最新价'] = df.get('最新价', 0)
        result['市值'] = df.get('市值', '')
        result['币种'] = df.get('币种', currency)
        
        if TEST_MODE:
            result = result.head(TEST_LIMIT)
        
        print(f"  ✅ 从CSV加载成功: {len(result)} 家")
        return result
        
    except Exception as e:
        print(f"  ❌ CSV文件加载失败: {e}")
        return pd.DataFrame()


def get_us_china_concept_stocks():
    """
    需求1: 获取美股中概股企业名单
    包括：股票简称、股票代码、上市状态、上市日期、上市交易所等
    """
    print("\n" + "="*60)
    print("正在获取美股中概股企业名单...")
    print("="*60)
    
    # 尝试多种方式获取美股中概股数据
    max_retries = 3
    
    for attempt in range(max_retries):
        try:
            if attempt > 0:
                print(f"  重试 {attempt}/{max_retries-1}...")
                time.sleep(2)
            
            # 方法1: 尝试获取中概股
            try:
                print("  尝试方法1: 获取中概股板块...")
                df = ak.stock_us_spot_em()  # 获取所有美股
                # 筛选出中概股（通常名称包含中文或特定标识）
                # 由于API限制，这里获取所有美股，后续可手动筛选
                
            except:
                # 方法2: 获取美股知名企业
                print("  尝试方法2: 获取美股知名企业...")
                df = ak.stock_us_famous_spot_em()
            
            if df is not None and not df.empty:
                # 重命名和组织列
                result = pd.DataFrame()
                result['股票代码'] = df['代码']
                result['股票简称'] = df['名称']
                result['上市交易所'] = 'NASDAQ/NYSE'  # 美股主要交易所
                result['上市状态'] = '正常'  # 在榜单中的默认为正常
                result['上市日期'] = ''  # akshare基础接口不提供，可后续补充
                result['上市板块'] = ''  # 需要单独查询
                result['上市企业全称'] = ''  # 需要单独查询
                result['对应大陆企业全称'] = ''  # 需要单独查询或人工维护
                result['最新价'] = df.get('最新价', df.get('价格', 0))
                result['市值'] = df.get('市值', df.get('总市值', ''))
                result['币种'] = 'USD'
                
                if TEST_MODE:
                    print(f"⚠️  [测试模式] 截取前 {TEST_LIMIT} 条数据")
                    result = result.head(TEST_LIMIT)
                
                print(f"✅ 成功获取美股 {len(result)} 家")
                print(f"   提示：可手动筛选中概股企业或使用补充文件标注")
                return result
            
        except Exception as e:
            print(f"  ⚠️  尝试失败: {str(e)[:100]}")
            if attempt == max_retries - 1:
                print(f"❌ 美股数据获取失败（已重试{max_retries}次）")
                print("   建议：")
                print("   1. 检查网络连接")
                print("   2. 稍后再试")
                print("   3. 或手动提供美股中概股名单CSV文件")
    
    return pd.DataFrame()


def get_hk_china_concept_stocks():
    """
    需求1: 获取港股中概股企业名单（港股主板、创业板的中国企业）
    """
    print("\n" + "="*60)
    print("正在获取港股中概股企业名单...")
    print("="*60)
    
    max_retries = 3
    
    for attempt in range(max_retries):
        try:
            if attempt > 0:
                print(f"  重试 {attempt}/{max_retries-1}...")
                time.sleep(3)  # 港股API较慢，等待时间长一点
            
            print("  正在连接港股数据源...")
            # 获取港股实时行情
            df = ak.stock_hk_spot_em()
            
            if df is not None and not df.empty:
                # 重命名和组织列
                result = pd.DataFrame()
                result['股票代码'] = df['代码']
                result['股票简称'] = df['名称']
                result['上市交易所'] = 'HKEX'  # 香港交易所
                result['上市状态'] = '正常'
                result['上市日期'] = ''
                result['上市板块'] = ''  # 主板/创业板需要单独判断
                result['上市企业全称'] = ''
                result['对应大陆企业全称'] = ''
                result['最新价'] = df.get('最新价', 0)
                result['市值'] = df.get('总市值', '')
                result['币种'] = 'HKD'
                
                if TEST_MODE:
                    print(f"⚠️  [测试模式] 截取前 {TEST_LIMIT} 条数据")
                    result = result.head(TEST_LIMIT)
                
                print(f"✅ 成功获取港股 {len(result)} 家")
                return result
            
        except Exception as e:
            error_msg = str(e)
            if 'timeout' in error_msg.lower():
                print(f"  ⚠️  网络超时，正在重试...")
            else:
                print(f"  ⚠️  获取失败: {error_msg[:100]}")
            
            if attempt == max_retries - 1:
                print(f"❌ 港股数据获取失败（已重试{max_retries}次）")
                print("   可能原因：")
                print("   1. 网络连接不稳定")
                print("   2. 数据源服务器繁忙")
                print("   3. 防火墙或代理设置")
                print("   建议：")
                print("   - 检查网络连接")
                print("   - 稍后再试（避开高峰期）")
                print("   - 或手动提供港股名单CSV文件")
    
    return pd.DataFrame()


def get_financial_data_us(stock_code):
    """
    需求2: 获取美股个股的财务数据
    
    返回包含多个季度/年度的财务数据
    """
    try:
        # 获取美股财务报表数据
        # 注意：akshare 对美股财务数据支持有限，可能需要其他数据源
        
        # 尝试获取利润表
        income_df = ak.stock_us_fundamental(symbol=stock_code, indicator="income")
        # 尝试获取资产负债表
        balance_df = ak.stock_us_fundamental(symbol=stock_code, indicator="balance")
        # 尝试获取现金流量表
        cash_df = ak.stock_us_fundamental(symbol=stock_code, indicator="cash_flow")
        
        # 整合数据
        financial_records = []
        
        if not income_df.empty and not balance_df.empty:
            # 按报告期间合并数据
            for idx in range(min(len(income_df), 8)):  # 获取最近8个季度
                record = {
                    '股票代码': stock_code,
                    '币种': 'USD',
                    '报告期间': income_df.iloc[idx].get('date', ''),
                    '总资产': balance_df.iloc[idx].get('totalAssets', None) if idx < len(balance_df) else None,
                    '总负债': balance_df.iloc[idx].get('totalLiabilities', None) if idx < len(balance_df) else None,
                    '净利润': income_df.iloc[idx].get('netIncome', None),
                    '营业总收入': income_df.iloc[idx].get('totalRevenue', None),
                    '营业总成本': income_df.iloc[idx].get('costOfRevenue', None),
                    '研发费用': income_df.iloc[idx].get('researchAndDevelopment', None),
                    '利润总额': income_df.iloc[idx].get('incomeBeforeTax', None),
                    '所得税': income_df.iloc[idx].get('incomeTaxExpense', None),
                }
                
                # 计算衍生指标
                if record['营业总收入'] and record['研发费用']:
                    record['研发投入占比'] = (record['研发费用'] / record['营业总收入']) * 100
                else:
                    record['研发投入占比'] = None
                
                if record['营业总收入'] and record['营业总成本']:
                    record['毛利率'] = ((record['营业总收入'] - record['营业总成本']) / record['营业总收入']) * 100
                else:
                    record['毛利率'] = None
                
                if record['总资产'] and record['营业总收入']:
                    record['总资产周转率'] = record['营业总收入'] / record['总资产']
                else:
                    record['总资产周转率'] = None
                
                financial_records.append(record)
        
        return pd.DataFrame(financial_records)
        
    except Exception as e:
        print(f"  ⚠️  {stock_code} 财务数据获取失败: {e}")
        return pd.DataFrame()


def get_financial_data_hk(stock_code):
    """
    需求2: 获取港股个股的财务数据
    """
    try:
        # 港股代码格式处理（需要5位数字，如 00700）
        if len(stock_code) < 5:
            stock_code = stock_code.zfill(5)
        
        # 尝试获取港股财务数据
        # 注意：akshare 港股财务数据接口可能有限
        
        # 方案1: 尝试东方财富港股财务数据
        try:
            balance_df = ak.stock_hk_finance_balance_em(symbol=stock_code)
            income_df = ak.stock_hk_finance_income_em(symbol=stock_code)
        except:
            # 方案2: 如果失败，返回空数据
            return pd.DataFrame()
        
        financial_records = []
        
        if not income_df.empty and not balance_df.empty:
            # 整合数据
            for idx in range(min(len(income_df), 8)):
                record = {
                    '股票代码': stock_code,
                    '币种': 'HKD',
                    '报告期间': income_df.iloc[idx].get('报告期', ''),
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
                if record['营业总收入'] and record['研发费用']:
                    record['研发投入占比'] = (record['研发费用'] / record['营业总收入']) * 100
                else:
                    record['研发投入占比'] = None
                
                if record['营业总收入'] and record['营业总成本']:
                    record['毛利率'] = ((record['营业总收入'] - record['营业总成本']) / record['营业总收入']) * 100
                else:
                    record['毛利率'] = None
                
                if record['总资产'] and record['营业总收入']:
                    record['总资产周转率'] = record['营业总收入'] / record['总资产']
                else:
                    record['总资产周转率'] = None
                
                financial_records.append(record)
        
        return pd.DataFrame(financial_records)
        
    except Exception as e:
        print(f"  ⚠️  {stock_code} 财务数据获取失败: {e}")
        return pd.DataFrame()


def collect_financial_data(company_list, market_type='US'):
    """
    批量收集财务数据
    
    Args:
        company_list: 包含股票代码的DataFrame
        market_type: 'US' 或 'HK'
    """
    print(f"\n开始收集 {market_type} 市场财务数据...")
    print(f"共需处理 {len(company_list)} 家企业")
    
    all_financial_data = []
    
    for idx, row in company_list.iterrows():
        stock_code = row['股票代码']
        stock_name = row['股票简称']
        
        print(f"  [{idx+1}/{len(company_list)}] 正在获取 {stock_name} ({stock_code}) 的财务数据...")
        
        if market_type == 'US':
            financial_df = get_financial_data_us(stock_code)
        else:
            financial_df = get_financial_data_hk(stock_code)
        
        if not financial_df.empty:
            financial_df['股票简称'] = stock_name
            all_financial_data.append(financial_df)
            print(f"    ✅ 成功获取 {len(financial_df)} 个报告期数据")
        else:
            print(f"    ❌ 未能获取到数据")
        
        # 请求延迟，避免频繁请求
        time.sleep(REQUEST_DELAY)
    
    if all_financial_data:
        result = pd.concat(all_financial_data, ignore_index=True)
        print(f"\n✅ {market_type} 市场财务数据收集完成，共 {len(result)} 条记录")
        return result
    else:
        print(f"\n⚠️  {market_type} 市场未收集到任何财务数据")
        return pd.DataFrame()


# === 主程序 ===
if __name__ == "__main__":
    print("\n" + "="*60)
    print("【中概股企业信息与财务数据采集系统】")
    print(f"启动时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    
    if TEST_MODE:
        print(f"\n🚩 当前为测试模式：每个市场仅抓取前 {TEST_LIMIT} 家企业")
        print(f"   设置 TEST_MODE = False 以启用全量模式\n")
    
    # ==================== 需求1: 获取中概股名单 ====================
    print("\n【步骤 1】获取中概股企业名单")
    
    # 1.1 获取美股中概股
    df_us = get_us_china_concept_stocks()
    
    # 如果API失败，尝试从CSV文件加载
    if df_us.empty and MANUAL_US_STOCKS_CSV:
        print("\n  API获取失败，尝试从CSV文件加载美股数据...")
        df_us = load_stocks_from_csv(MANUAL_US_STOCKS_CSV, market_name='US', currency='USD')
    
    # 1.2 获取港股中概股
    df_hk = get_hk_china_concept_stocks()
    
    # 如果API失败，尝试从CSV文件加载
    if df_hk.empty and MANUAL_HK_STOCKS_CSV:
        print("\n  API获取失败，尝试从CSV文件加载港股数据...")
        df_hk = load_stocks_from_csv(MANUAL_HK_STOCKS_CSV, market_name='HK', currency='HKD')
    
    # 1.3 合并名单
    if not df_us.empty or not df_hk.empty:
        all_companies = pd.concat([df_us, df_hk], ignore_index=True)
        
        # 导出企业名单
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        suffix = "_测试" if TEST_MODE else ""
        company_list_file = f"中概股企业名单{suffix}_{timestamp}.xlsx"
        
        all_companies.to_excel(company_list_file, index=False)
        print(f"\n✅ 企业名单已导出: {company_list_file}")
        print(f"   总计: {len(all_companies)} 家 (美股: {len(df_us)}, 港股: {len(df_hk)})")
    else:
        print("\n" + "="*60)
        print("❌ 未能获取任何企业名单")
        print("="*60)
        print("\n可能的原因：")
        print("  1. 网络连接问题")
        print("  2. API数据源服务器繁忙")
        print("  3. akshare库版本过旧")
        print("\n解决方案：")
        print("  【方案1】检查网络并重试")
        print("    - 确保网络连接正常")
        print("    - 稍后再试（避开高峰期）")
        print("    - 更新akshare: pip install akshare --upgrade")
        print("\n  【方案2】使用CSV文件手动导入")
        print("    步骤1: 编辑CSV模板文件")
        print("      - us_stocks_template.csv (美股)")
        print("      - hk_stocks_template.csv (港股)")
        print("    步骤2: 在main.py中设置文件路径")
        print("      MANUAL_US_STOCKS_CSV = 'us_stocks_template.csv'")
        print("      MANUAL_HK_STOCKS_CSV = 'hk_stocks_template.csv'")
        print("    步骤3: 重新运行程序")
        print("\n  【方案3】使用已有的企业名单")
        print("    如果之前成功生成过企业名单文件，可以：")
        print("    - 直接使用该文件进行后续分析")
        print("    - 或将其重命名为CSV模板文件格式")
        print("="*60)
        exit(1)
    
    # ==================== 需求2: 获取财务数据 ====================
    print("\n" + "="*60)
    print("【步骤 2】获取企业财务数据")
    print("="*60)
    
    # 2.1 收集美股财务数据
    us_financial_data = pd.DataFrame()
    if not df_us.empty:
        us_financial_data = collect_financial_data(df_us, market_type='US')
    
    # 2.2 收集港股财务数据
    hk_financial_data = pd.DataFrame()
    if not df_hk.empty:
        hk_financial_data = collect_financial_data(df_hk, market_type='HK')
    
    # 2.3 合并并导出财务数据
    if not us_financial_data.empty or not hk_financial_data.empty:
        all_financial_data = pd.concat([us_financial_data, hk_financial_data], ignore_index=True)
        
        # 调整列顺序
        columns_order = [
            '股票代码', '股票简称', '币种', '报告期间',
            '总资产', '总负债', '净利润', '营业总收入', '营业总成本',
            '研发费用', '利润总额', '所得税',
            '研发投入占比', '毛利率', '总资产周转率'
        ]
        all_financial_data = all_financial_data[columns_order]
        
        # 导出财务数据
        financial_file = f"中概股财务数据{suffix}_{timestamp}.xlsx"
        
        # 使用 ExcelWriter 创建多个sheet
        with pd.ExcelWriter(financial_file, engine='openpyxl') as writer:
            all_financial_data.to_excel(writer, sheet_name='全部财务数据', index=False)
            
            if not us_financial_data.empty:
                us_financial_data.to_excel(writer, sheet_name='美股财务数据', index=False)
            
            if not hk_financial_data.empty:
                hk_financial_data.to_excel(writer, sheet_name='港股财务数据', index=False)
        
        print(f"\n✅ 财务数据已导出: {financial_file}")
        print(f"   总计: {len(all_financial_data)} 条记录")
    else:
        print("\n⚠️  未能获取任何财务数据")
    
    # ==================== 总结 ====================
    print("\n" + "="*60)
    print("【任务完成总结】")
    print("="*60)
    print(f"✅ 企业名单: {len(all_companies)} 家")
    print(f"   - 美股中概股: {len(df_us)} 家")
    print(f"   - 港股: {len(df_hk)} 家")
    
    if not us_financial_data.empty or not hk_financial_data.empty:
        print(f"✅ 财务数据: {len(all_financial_data)} 条记录")
    else:
        print(f"⚠️  财务数据: 0 条记录")
    
    print(f"\n📁 生成文件:")
    print(f"   1. {company_list_file}")
    if not us_financial_data.empty or not hk_financial_data.empty:
        print(f"   2. {financial_file}")
    
    print(f"\n完成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
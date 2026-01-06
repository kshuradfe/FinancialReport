"""
企业信息补充合并脚本

用途：将手动维护的企业详细信息（上市日期、企业全称等）合并到采集的数据中

使用方法：
1. 编辑 company_info_supplement_example.csv，补充企业信息
2. 运行: python merge_supplement_data.py
3. 选择要处理的企业名单文件
"""

import pandas as pd
import os
from datetime import datetime
import glob


def find_latest_company_list():
    """查找最新的企业名单文件"""
    files = glob.glob("中概股企业名单*.xlsx")
    if not files:
        return None
    # 按修改时间排序
    files.sort(key=os.path.getmtime, reverse=True)
    return files[0]


def merge_supplement_info():
    """合并补充信息到企业名单"""
    
    print("="*60)
    print("企业信息补充合并工具")
    print("="*60)
    
    # 1. 查找最新的企业名单文件
    latest_file = find_latest_company_list()
    
    if not latest_file:
        print("\n❌ 未找到企业名单文件")
        print("   请先运行 main.py 生成企业名单")
        return
    
    print(f"\n找到最新企业名单: {latest_file}")
    
    # 2. 检查补充信息文件
    supplement_file = "company_info_supplement_example.csv"
    
    if not os.path.exists(supplement_file):
        print(f"\n❌ 未找到补充信息文件: {supplement_file}")
        print("   请先创建并编辑此文件")
        return
    
    print(f"找到补充信息文件: {supplement_file}")
    
    # 3. 读取数据
    print("\n正在读取数据...")
    df_company = pd.read_excel(latest_file)
    df_supplement = pd.read_csv(supplement_file)
    
    print(f"  企业名单记录数: {len(df_company)}")
    print(f"  补充信息记录数: {len(df_supplement)}")
    
    # 4. 合并数据（基于股票代码）
    print("\n正在合并数据...")
    
    # 使用左连接，保留所有企业名单中的记录
    df_merged = df_company.merge(
        df_supplement[['股票代码', '上市日期', '上市板块', '上市企业全称', '对应大陆企业全称']],
        on='股票代码',
        how='left',
        suffixes=('', '_补充')
    )
    
    # 用补充信息覆盖原有的空字段
    for col in ['上市日期', '上市板块', '上市企业全称', '对应大陆企业全称']:
        if col + '_补充' in df_merged.columns:
            # 如果原字段为空，用补充字段填充
            df_merged[col] = df_merged[col].fillna(df_merged[col + '_补充'])
            # 删除补充字段
            df_merged.drop(col + '_补充', axis=1, inplace=True)
    
    # 5. 统计合并结果
    matched_count = df_supplement['股票代码'].isin(df_company['股票代码']).sum()
    print(f"\n✅ 合并完成")
    print(f"   成功匹配: {matched_count} 家企业")
    print(f"   未匹配: {len(df_supplement) - matched_count} 家企业")
    
    # 6. 导出合并后的数据
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = f"中概股企业名单_已补充_{timestamp}.xlsx"
    
    df_merged.to_excel(output_file, index=False)
    
    print(f"\n📁 已导出合并后的文件: {output_file}")
    
    # 7. 显示补充了哪些企业的信息
    print("\n已补充信息的企业:")
    supplemented = df_merged[df_merged['股票代码'].isin(df_supplement['股票代码'])]
    
    for idx, row in supplemented.iterrows():
        print(f"  - {row['股票简称']} ({row['股票代码']})")
    
    print("\n" + "="*60)
    print("合并完成！")
    print("="*60)


if __name__ == "__main__":
    merge_supplement_info()


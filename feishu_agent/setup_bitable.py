"""
飞书多维表格初始化脚本
==================
功能：
1. 在飞书创建"直播间线索数据"多维表格
2. 创建"线索明细"数据表
3. 添加字段：日期、品类名、二级团队、三级团队、会员等级、线索数
4. 读取历史Excel（3月/4月/5月），汇总后批量导入

使用方法：
    1. 确保 config_local.py 已配置好 APP_ID 和 APP_SECRET
    2. python setup_bitable.py
    3. 脚本会打印 bitable_app_token 和 table_id，请填入 config_local.py
"""

import sys
import pandas as pd
from datetime import datetime
from typing import List, Dict

# 先尝试加载本地配置（用户真实凭证），fallback到模板配置
try:
    from config_local import APP_ID, APP_SECRET, HISTORY_EXCEL_FILES, EXCEL_SHEET_NAME
except ImportError:
    print("⚠️ 未找到 config_local.py，使用 config.py 模板（需要填入真实凭证）")
    from config import APP_ID, APP_SECRET, HISTORY_EXCEL_FILES, EXCEL_SHEET_NAME

from feishu_client import FeishuClient

# 字段定义
FIELDS = [
    {"name": "日期", "type": 5},
    {"name": "品类名", "type": 1},
    {"name": "二级团队", "type": 3, "property": {"options": [
        {"name": "健康线", "color": 1},
        {"name": "兴趣变美线", "color": 2}
    ]}},
    {"name": "三级团队", "type": 3, "property": {"options": [
        {"name": "直播间购物车", "color": 1},
        {"name": "直播间弹幕", "color": 2}
    ]}},
    {"name": "会员等级", "type": 3, "property": {"options": [
        {"name": "V0 观光客", "color": 1},
        {"name": "V1 普通岛民", "color": 2},
        {"name": "V2 新星岛民", "color": 3},
        {"name": "V3 先驱岛民", "color": 4},
        {"name": "V4 创新岛民", "color": 5},
        {"name": "V5 领航岛民", "color": 6},
        {"name": "V6 至尊岛民", "color": 7},
        {"name": "V7 白银岛主", "color": 8},
        {"name": "V8 白金岛主", "color": 9},
        {"name": "V9 黄金岛主", "color": 10},
        {"name": "V10 黑金岛主", "color": 11}
    ]}},
    {"name": "线索数", "type": 2, "property": {"formatter": "0"}}
]


def read_and_aggregate_excel(files: List[str], sheet_name: str) -> pd.DataFrame:
    """读取多个Excel文件，按天+品类+团队+等级汇总"""
    all_dfs = []
    for f in files:
        print(f"📖 正在读取 {f} ...")
        df = pd.read_excel(f, sheet_name=sheet_name)
        df['例子日期'] = pd.to_datetime(df['例子时间']).dt.date
        all_dfs.append(df)

    df = pd.concat(all_dfs, ignore_index=True)
    print(f"✅ 共读取 {len(df)} 条明细记录")

    # 按维度汇总
    agg = df.groupby([
        '例子日期', '品类名', '二级团队', '三级团队', '会员等级'
    ]).size().reset_index(name='线索数')

    print(f"✅ 汇总后共 {len(agg)} 条记录")
    return agg


def prepare_records(df: pd.DataFrame) -> List[Dict]:
    """把DataFrame转为飞书多维表格记录格式"""
    records = []
    for _, row in df.iterrows():
        date_val = row['例子日期']
        if pd.isna(date_val):
            continue
        if isinstance(date_val, datetime):
            date_str = date_val.strftime("%Y/%m/%d")
        else:
            date_str = pd.to_datetime(date_val).strftime("%Y/%m/%d")

        records.append({
            "日期": int(pd.to_datetime(date_val).timestamp() * 1000),
            "品类名": str(row['品类名']),
            "二级团队": str(row['二级团队']),
            "三级团队": str(row['三级团队']),
            "会员等级": str(row['会员等级']),
            "线索数": int(row['线索数'])
        })
    return records


def main():
    print("=" * 50)
    print("飞书多维表格初始化")
    print("=" * 50)

    if APP_ID == "cli_xxxxxxxxxxxxxxxx" or not APP_SECRET or len(APP_SECRET) < 10:
        print("\n❌ 错误：请先配置 config_local.py，填入真实的 APP_ID 和 APP_SECRET")
        print("   操作步骤：")
        print("   1. cp feishu_agent/config.py feishu_agent/config_local.py")
        print("   2. 编辑 config_local.py，填入你的飞书应用凭证")
        sys.exit(1)

    client = FeishuClient(APP_ID, APP_SECRET)

    # 1. 创建多维表格
    print("\n📦 步骤1：创建多维表格 ...")
    app_token = client.create_bitable("直播间线索数据")
    print(f"✅ 多维表格已创建，app_token: {app_token}")

    # 2. 创建数据表
    print("\n📦 步骤2：创建数据表 ...")
    table_id = client.create_table(app_token, "线索明细", "直播间每日线索汇总数据")
    print(f"✅ 数据表已创建，table_id: {table_id}")

    # 3. 添加字段
    print("\n📦 步骤3：添加字段 ...")
    for field in FIELDS:
        prop = field.get("property")
        try:
            fid = client.create_field(app_token, table_id, field["name"], field["type"], prop)
            print(f"   ✅ {field['name']} ({fid})")
        except Exception as e:
            print(f"   ❌ {field['name']} 创建失败: {e}")
            import json
            print(f"      请求体: {json.dumps({'field_name': field['name'], 'type': field['type'], 'property': prop}, ensure_ascii=False)}")
            raise

    # 4. 读取并汇总Excel
    print("\n📦 步骤4：读取历史Excel并汇总 ...")
    agg_df = read_and_aggregate_excel(HISTORY_EXCEL_FILES, EXCEL_SHEET_NAME)

    # 5. 导入飞书
    print("\n📦 步骤5：导入数据到飞书多维表格 ...")
    records = prepare_records(agg_df)
    print(f"   准备导入 {len(records)} 条记录 ...")
    created_ids = client.batch_create_records(app_token, table_id, records)
    print(f"✅ 成功导入 {len(created_ids)} 条记录")

    # 6. 打印配置
    print("\n" + "=" * 50)
    print("🎉 初始化完成！请把以下信息填入 config_local.py：")
    print("=" * 50)
    print(f"BITABLE_APP_TOKEN = \"{app_token}\"")
    print(f"BITABLE_TABLE_ID  = \"{table_id}\"")
    print(f"\n📎 飞书多维表格链接：https://www.feishu.cn/base/{app_token}")
    print("=" * 50)


if __name__ == "__main__":
    main()

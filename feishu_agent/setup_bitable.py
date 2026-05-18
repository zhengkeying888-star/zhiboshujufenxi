"""
飞书多维表格初始化脚本（明细级，字段与Excel一比一）
==================
功能：
1. 在飞书创建"直播间线索明细"多维表格
2. 创建数据表，字段与 Excel 明细 sheet 完全一致（29个字段）
3. 读取历史Excel（3月/4月/5月），逐条导入为明细记录
4. 打印 app_token / table_id，填入 config_local.py

使用方法：
    1. 确保 config_local.py 已配置好 APP_ID 和 APP_SECRET
    2. python setup_bitable.py
    3. 脚本会打印 bitable_app_token 和 table_id，请填入 config_local.py
"""

import sys
import pandas as pd
from datetime import datetime
from typing import List, Dict

# 先尝试加载本地配置
try:
    from config_local import APP_ID, APP_SECRET, HISTORY_EXCEL_FILES, EXCEL_SHEET_NAME
except ImportError:
    print("⚠️ 未找到 config_local.py，使用 config.py 模板")
    from config import APP_ID, APP_SECRET, HISTORY_EXCEL_FILES, EXCEL_SHEET_NAME

from feishu_client import FeishuClient

# ========== 字段定义（与 Excel 明细一比一） ==========
# type: 1=文本, 2=数字, 3=单选, 5=日期
FIELDS = [
    # 文本字段
    {"name": "统计月", "type": 1},
    {"name": "例子时间", "type": 5},          # 日期时间
    {"name": "一级渠道", "type": 1},
    {"name": "二级渠道", "type": 1},
    {"name": "三级渠道", "type": 1},
    {"name": "一级团队", "type": 1},
    {"name": "二级团队", "type": 1},
    {"name": "三级团队", "type": 1},
    {"name": "品类", "type": 1},
    {"name": "品类名", "type": 1},
    {"name": "老师名", "type": 1},
    # 数字字段
    {"name": "训练营id", "type": 2},
    {"name": "训练营名", "type": 1},
    {"name": "订单id", "type": 2},
    {"name": "用户id", "type": 2},
    {"name": "会员等级", "type": 1},
    {"name": "渠道参", "type": 1},
    {"name": "渠道名", "type": 1},
    {"name": "付费类型", "type": 1},
    {"name": "sku_id", "type": 2},
    {"name": "sku名称", "type": 1},
    # 日期字段
    {"name": "开营时间", "type": 5},
    {"name": "结营时间", "type": 5},
    {"name": "首单时间", "type": 5},
    # 数字字段
    {"name": "投手id", "type": 2},
    {"name": "投手名称", "type": 1},
    {"name": "投手部门", "type": 1},
    {"name": "例子价格", "type": 2},
    {"name": "首单流水", "type": 2},
    # 新增：区分直播策略类型
    {"name": "是否新量直播间策略", "type": 3, "property": {"options": [{"name": "是", "color": 0}, {"name": "否", "color": 1}]}},  # 单选：是/否
]

# Excel → 飞书字段名映射（大部分相同，只处理特殊情况）
EXCEL_TO_FEISHU = {
    "例子时间": "例子时间",
    "开营时间": "开营时间",
    "结营时间": "结营时间",
    "首单时间": "首单时间",
}


def read_excel_files(files: List[str], sheet_name: str) -> pd.DataFrame:
    """读取多个Excel文件，合并为明细DataFrame"""
    all_dfs = []
    for f in files:
        print(f"📖 正在读取 {f} ...")
        df = pd.read_excel(f, sheet_name=sheet_name)
        all_dfs.append(df)

    df = pd.concat(all_dfs, ignore_index=True)
    print(f"✅ 共读取 {len(df)} 条明细记录")
    return df


def _to_timestamp_ms(val) -> int:
    """把各种日期格式转为飞书日期字段需要的毫秒时间戳"""
    if pd.isna(val):
        return None
    if isinstance(val, (int, float)):
        # 已经是时间戳或Excel序列号
        dt = pd.to_datetime(val, unit="s" if val < 1e10 else "D", errors="coerce")
        if pd.isna(dt):
            return None
        return int(dt.timestamp() * 1000)
    # 字符串或其他
    dt = pd.to_datetime(val, errors="coerce")
    if pd.isna(dt):
        return None
    return int(dt.timestamp() * 1000)


def _safe_int(val) -> int:
    """安全转整数"""
    if pd.isna(val):
        return 0
    try:
        return int(float(val))
    except (ValueError, TypeError):
        return 0


def _safe_str(val) -> str:
    """安全转字符串"""
    if pd.isna(val):
        return ""
    return str(val)


def prepare_records(df: pd.DataFrame) -> List[Dict]:
    """把DataFrame转为飞书多维表格记录格式（逐条明细）"""
    records = []
    for _, row in df.iterrows():
        record = {}

        # 文本字段
        record["统计月"] = _safe_str(row.get("统计月"))
        record["一级渠道"] = _safe_str(row.get("一级渠道"))
        record["二级渠道"] = _safe_str(row.get("二级渠道"))
        record["三级渠道"] = _safe_str(row.get("三级渠道"))
        record["一级团队"] = _safe_str(row.get("一级团队"))
        record["二级团队"] = _safe_str(row.get("二级团队"))
        record["三级团队"] = _safe_str(row.get("三级团队"))
        record["品类"] = _safe_str(row.get("品类"))
        record["品类名"] = _safe_str(row.get("品类名"))
        record["老师名"] = _safe_str(row.get("老师名"))
        record["训练营名"] = _safe_str(row.get("训练营名"))
        record["会员等级"] = _safe_str(row.get("会员等级"))
        record["渠道参"] = _safe_str(row.get("渠道参"))
        record["渠道名"] = _safe_str(row.get("渠道名"))
        record["付费类型"] = _safe_str(row.get("付费类型"))
        record["sku名称"] = _safe_str(row.get("sku名称"))
        record["投手名称"] = _safe_str(row.get("投手名称"))
        record["投手部门"] = _safe_str(row.get("投手部门"))

        # 数字字段
        record["训练营id"] = _safe_int(row.get("训练营id"))
        record["订单id"] = _safe_int(row.get("订单id"))
        record["用户id"] = _safe_int(row.get("用户id"))
        record["sku_id"] = _safe_int(row.get("sku_id"))
        record["投手id"] = _safe_int(row.get("投手id"))
        record["例子价格"] = _safe_int(row.get("例子价格"))
        record["首单流水"] = _safe_int(row.get("首单流水"))

        # 日期字段（飞书日期字段需要毫秒时间戳）
        ts = _to_timestamp_ms(row.get("例子时间"))
        if ts:
            record["例子时间"] = ts
        ts = _to_timestamp_ms(row.get("开营时间"))
        if ts:
            record["开营时间"] = ts
        ts = _to_timestamp_ms(row.get("结营时间"))
        if ts:
            record["结营时间"] = ts
        ts = _to_timestamp_ms(row.get("首单时间"))
        if ts:
            record["首单时间"] = ts

        records.append(record)
    return records


def main():
    print("=" * 50)
    print("飞书多维表格初始化（明细级，字段与Excel一比一）")
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
    app_token = client.create_bitable("直播间线索明细")
    print(f"✅ 多维表格已创建，app_token: {app_token}")

    # 2. 创建数据表
    print("\n📦 步骤2：创建数据表 ...")
    table_id = client.create_table(app_token, "线索明细", "直播间线索逐条明细，字段与Excel一比一")
    print(f"✅ 数据表已创建，table_id: {table_id}")

    # 3. 添加字段
    print("\n📦 步骤3：添加字段（共{}个）...".format(len(FIELDS)))
    for field in FIELDS:
        prop = field.get("property")
        try:
            fid = client.create_field(app_token, table_id, field["name"], field["type"], prop)
            print(f"   ✅ {field['name']} ({fid})")
        except Exception as e:
            print(f"   ❌ {field['name']} 创建失败: {e}")
            raise

    # 4. 读取Excel明细
    print("\n📦 步骤4：读取历史Excel明细 ...")
    df = read_excel_files(HISTORY_EXCEL_FILES, EXCEL_SHEET_NAME)

    # 5. 导入飞书
    print("\n📦 步骤5：导入数据到飞书多维表格 ...")
    records = prepare_records(df)
    print(f"   准备导入 {len(records)} 条明细记录 ...")
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

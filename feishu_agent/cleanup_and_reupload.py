"""
清理错误数据并重新上传5月18日完整数据（含策略字段）
"""
import sys
import os
import pandas as pd
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config_local import APP_ID, APP_SECRET, BITABLE_APP_TOKEN, BITABLE_TABLE_ID
from feishu_client import FeishuClient


def _to_ts(val):
    if pd.isna(val):
        return None
    if isinstance(val, pd.Timestamp):
        return int(val.timestamp() * 1000)
    if isinstance(val, datetime):
        return int(val.timestamp() * 1000)
    return None


def _to_int(val):
    if pd.isna(val):
        return 0
    try:
        return int(float(val))
    except (ValueError, TypeError):
        return 0


def _to_float(val):
    if pd.isna(val):
        return 0
    try:
        return float(val)
    except (ValueError, TypeError):
        return 0


def _to_str(val):
    if pd.isna(val):
        return ""
    return str(val).strip()


def main():
    client = FeishuClient(APP_ID, APP_SECRET)

    # 1. 查询所有记录，找出5月19日和5月18日策略为空的记录
    print("📥 查询 Bitable 记录 ...")
    records = client.query_records(BITABLE_APP_TOKEN, BITABLE_TABLE_ID)

    may19_ids = []
    may18_ids = []
    for rec in records:
        fields = rec.get("fields", {})
        ts = fields.get("例子时间") or fields.get("日期")
        if not isinstance(ts, (int, float)):
            continue
        dt = datetime.fromtimestamp(ts / 1000)
        rec_id = rec.get("record_id")
        if dt.month == 5 and dt.day == 19:
            may19_ids.append(rec_id)
        elif dt.month == 5 and dt.day == 18:
            # 删除所有5月18日记录（重新上传完整数据）
            may18_ids.append(rec_id)

    print(f"   发现 5月19日 错误记录: {len(may19_ids)} 条")
    print(f"   发现 5月18日 记录: {len(may18_ids)} 条")

    # 2. 删除错误记录
    total_delete = may19_ids + may18_ids
    if total_delete:
        print(f"\n🗑️ 删除 {len(total_delete)} 条记录 ...")
        client.delete_records(BITABLE_APP_TOKEN, BITABLE_TABLE_ID, total_delete)
        print(f"   ✅ 删除完成")
    else:
        print("   ℹ️ 无需要删除的记录")

    # 3. 读取 Excel 并上传5月18日完整数据
    script_dir = os.path.dirname(os.path.abspath(__file__))
    excel_path = os.path.join(script_dir, "../直播间5月19日数据分析.xlsx")

    print(f"\n📥 读取 Excel: {excel_path}")
    df = pd.read_excel(excel_path, sheet_name="明细")
    df["例子时间"] = pd.to_datetime(df["例子时间"], errors="coerce")

    # 只保留 5月18日
    may18 = df[(df["例子时间"].dt.month == 5) & (df["例子时间"].dt.day == 18)].copy()
    print(f"✅ 5月18日记录: {len(may18)} 条")

    if len(may18) == 0:
        print("⚠️ 无 5月18日 数据，退出")
        return

    records_to_create = []
    for _, row in may18.iterrows():
        fields = {
            "统计月": _to_str(row.get("统计月", "")),
            "例子时间": _to_ts(row.get("例子时间")),
            "一级渠道": _to_str(row.get("一级渠道", "")),
            "二级渠道": _to_str(row.get("二级渠道", "")),
            "三级渠道": _to_str(row.get("三级渠道", "")),
            "一级团队": _to_str(row.get("一级团队", "")),
            "二级团队": _to_str(row.get("二级团队", "")),
            "三级团队": _to_str(row.get("三级团队", "")),
            "品类": _to_str(row.get("品类", "")),
            "品类名": _to_str(row.get("品类名", "")),
            "老师名": _to_str(row.get("老师名", "")),
            "训练营id": _to_int(row.get("训练营id", 0)),
            "训练营名": _to_str(row.get("训练营名", "")),
            "订单id": _to_int(row.get("订单id", 0)),
            "用户id": _to_int(row.get("用户id", 0)),
            "会员等级": _to_str(row.get("会员等级", "")),
            "渠道参": _to_str(row.get("渠道参", "")),
            "渠道名": _to_str(row.get("渠道名", "")),
            "付费类型": _to_str(row.get("付费类型", "")),
            "sku_id": _to_int(row.get("sku_id", 0)),
            "sku名称": _to_str(row.get("sku名称", "")),
            "开营时间": _to_ts(row.get("开营时间")),
            "结营时间": _to_ts(row.get("结营时间")),
            "首单时间": _to_ts(row.get("首单时间")),
            "投手id": _to_int(row.get("投手id", 0)),
            "投手名称": _to_str(row.get("投手名称", "")),
            "投手部门": _to_str(row.get("投手部门", "")),
            "例子价格": _to_float(row.get("例子价格", 0)),
            "首单流水": _to_float(row.get("首单流水", 0)),
            "是否新量直播间策略": _to_str(row.get("是否新量策略", "")),
        }
        # 过滤掉 None 值（Bitable 创建时不传空字段更稳定）
        fields = {k: v for k, v in fields.items() if v is not None and v != ""}
        records_to_create.append(fields)

    print(f"\n📤 上传 {len(records_to_create)} 条记录到 Bitable ...")
    record_ids = client.batch_create_records(BITABLE_APP_TOKEN, BITABLE_TABLE_ID, records_to_create)
    print(f"✅ 上传完成: {len(record_ids)} 条记录")


if __name__ == "__main__":
    main()

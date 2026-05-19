"""
上传 5月18日 数据到 Bitable（追加模式）
数据源: ../直播间5月19日数据分析.xlsx
"""
import sys
import os
import pandas as pd
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config_local import APP_ID, APP_SECRET, BITABLE_APP_TOKEN, BITABLE_TABLE_ID
from feishu_client import FeishuClient


def _to_ts(val):
    """转为毫秒时间戳（本地时间）"""
    if pd.isna(val):
        return None
    if isinstance(val, pd.Timestamp):
        # 必须用 to_pydatetime() 再取 timestamp()，否则 naive pd.Timestamp
        # 会被当成 UTC，导致 +8h 时区漂移（晚 8 小时的记录变成次日）
        dt = val.to_pydatetime()
        return int(dt.timestamp() * 1000)
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
    script_dir = os.path.dirname(os.path.abspath(__file__))
    excel_path = os.path.join(script_dir, "../直播间5月19日数据分析.xlsx")

    print(f"📥 读取 Excel: {excel_path}")
    df = pd.read_excel(excel_path, sheet_name="明细")
    df["例子时间"] = pd.to_datetime(df["例子时间"], errors="coerce")

    # 只保留 5月18日
    may18 = df[(df["例子时间"].dt.month == 5) & (df["例子时间"].dt.day == 18)].copy()
    print(f"✅ 5月18日记录: {len(may18)} 条")

    if len(may18) == 0:
        print("⚠️ 无 5月18日 数据，退出")
        return

    records = []
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
        }
        # 过滤掉 None 值（Bitable 创建时不传空字段更稳定）
        fields = {k: v for k, v in fields.items() if v is not None and v != ""}
        records.append(fields)

    print(f"\n📤 上传到 Bitable ...")
    client = FeishuClient(APP_ID, APP_SECRET)
    record_ids = client.batch_create_records(BITABLE_APP_TOKEN, BITABLE_TABLE_ID, records)
    print(f"✅ 上传完成: {len(record_ids)} 条记录")


if __name__ == "__main__":
    main()

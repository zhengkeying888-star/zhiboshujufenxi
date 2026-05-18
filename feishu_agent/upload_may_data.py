"""
上传 5月2日-17日 线索数据到 Bitable
步骤：
1. 读取 Bitable 所有记录，筛选 3月 record_id 并删除（释放空间）
2. 从 Excel 读取 5月2日-17日数据
3. 格式化成 Bitable 字段格式
4. 分批上传到 Bitable
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pandas as pd
from datetime import datetime
from feishu_client import FeishuClient
from config_local import APP_ID, APP_SECRET, BITABLE_APP_TOKEN, BITABLE_TABLE_ID

client = FeishuClient(APP_ID, APP_SECRET)


def dt_to_ms(dt):
    """datetime / NaT -> 毫秒时间戳或 None"""
    if pd.isna(dt):
        return None
    if isinstance(dt, pd.Timestamp):
        dt = dt.to_pydatetime()
    if isinstance(dt, datetime):
        return int(dt.timestamp() * 1000)
    return None


def clean_val(v):
    """NaN / NaT -> None"""
    if pd.isna(v):
        return None
    if isinstance(v, (int, float)):
        return v
    return str(v)


def main():
    print("=" * 50)
    print("上传 5月2日-17日 线索数据到 Bitable")
    print("=" * 50)

    # Step 1: 读取 Bitable，筛选 3月记录并删除
    print("\n1. 读取 Bitable 记录并筛选 3月数据...")
    records = client.query_records(BITABLE_APP_TOKEN, BITABLE_TABLE_ID)
    print(f"   Bitable 现有记录: {len(records)} 条")

    march_ids = []
    for rec in records:
        fields = rec.get("fields", {})
        ts = fields.get("例子时间")
        if isinstance(ts, (int, float)):
            dt = datetime.fromtimestamp(ts / 1000)
            if dt.month == 3:
                march_ids.append(rec["record_id"])

    print(f"   3月记录数: {len(march_ids)} 条")

    if march_ids:
        print(f"   开始删除 3月记录...")
        batch_size = 500
        for i in range(0, len(march_ids), batch_size):
            batch = march_ids[i:i + batch_size]
            try:
                client.delete_records(BITABLE_APP_TOKEN, BITABLE_TABLE_ID, batch)
                print(f"      已删除 {len(batch)} 条")
            except Exception as e:
                print(f"      删除失败: {e}")
        print(f"   ✅ 3月记录删除完成")

    # Step 2: 读取 Excel 中 5月2日-17日数据
    print("\n2. 读取 Excel 数据...")
    excel_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "直播间4.1-5.17all.xlsx")
    df = pd.read_excel(excel_path, sheet_name="明细")
    df["例子时间"] = pd.to_datetime(df["例子时间"])

    may_df = df[(df["例子时间"].dt.month == 5) & (df["例子时间"].dt.day >= 2)].copy()
    print(f"   Excel 中 5月2日-17日记录: {len(may_df)} 条")

    if len(may_df) == 0:
        print("❌ 无数据需要上传")
        return

    # Step 3: 格式化成 Bitable 字段格式
    print("\n3. 格式化数据...")
    field_records = []
    for _, row in may_df.iterrows():
        fields = {
            "统计月": clean_val(row.get("统计月")),
            "例子时间": dt_to_ms(row.get("例子时间")),
            "一级渠道": clean_val(row.get("一级渠道")),
            "二级渠道": clean_val(row.get("二级渠道")),
            "三级渠道": clean_val(row.get("三级渠道")),
            "一级团队": clean_val(row.get("一级团队")),
            "二级团队": clean_val(row.get("二级团队")),
            "三级团队": clean_val(row.get("三级团队")),
            "品类": clean_val(row.get("品类")),
            "品类名": clean_val(row.get("品类名")),
            "老师名": clean_val(row.get("老师名")),
            "训练营id": clean_val(row.get("训练营id")),
            "训练营名": clean_val(row.get("训练营名")),
            "订单id": clean_val(row.get("订单id")),
            "用户id": clean_val(row.get("用户id")),
            "会员等级": clean_val(row.get("会员等级")),
            "渠道参": clean_val(row.get("渠道参")),
            "渠道名": clean_val(row.get("渠道名")),
            "付费类型": clean_val(row.get("付费类型")),
            "sku_id": clean_val(row.get("sku_id")),
            "sku名称": clean_val(row.get("sku名称")),
            "开营时间": dt_to_ms(row.get("开营时间")),
            "结营时间": dt_to_ms(row.get("结营时间")),
            "首单时间": dt_to_ms(row.get("首单时间")),
            "投手id": clean_val(row.get("投手id")),
            "投手名称": clean_val(row.get("投手名称")),
            "投手部门": clean_val(row.get("投手部门")),
            "例子价格": clean_val(row.get("例子价格")),
            "首单流水": clean_val(row.get("首单流水")),
            "线索数": 1,
        }
        # 过滤掉 None 值
        fields = {k: v for k, v in fields.items() if v is not None}
        field_records.append({"fields": fields})

    # Step 4: 分批上传
    print(f"\n4. 开始上传 {len(field_records)} 条记录到 Bitable...")
    batch_size = 500
    success = 0
    failed = 0
    for i in range(0, len(field_records), batch_size):
        batch = field_records[i:i + batch_size]
        try:
            payload = {"records": batch}
            client._request(
                "POST",
                f"/bitable/v1/apps/{BITABLE_APP_TOKEN}/tables/{BITABLE_TABLE_ID}/records/batch_create",
                json=payload,
            )
            success += len(batch)
            print(f"   ✅ 已上传 {success}/{len(field_records)} 条")
        except Exception as e:
            failed += len(batch)
            print(f"   ❌ 上传失败 ({len(batch)} 条): {e}")

    print(f"\n{'=' * 50}")
    print(f"上传完成: 成功 {success} 条, 失败 {failed} 条")
    print(f"{'=' * 50}")


if __name__ == "__main__":
    main()

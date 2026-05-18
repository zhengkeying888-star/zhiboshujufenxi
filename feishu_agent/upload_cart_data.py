"""
清空 Bitable 并重新上传 4月+5月 购物车数据（不含弹幕）
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
    if pd.isna(dt):
        return None
    if isinstance(dt, pd.Timestamp):
        dt = dt.to_pydatetime()
    if isinstance(dt, datetime):
        return int(dt.timestamp() * 1000)
    return None


def clean_val(v):
    if pd.isna(v):
        return None
    if isinstance(v, (int, float)):
        return v
    return str(v)


def main():
    print("=" * 50)
    print("清空 Bitable 并上传 4月+5月 购物车数据")
    print("=" * 50)

    # Step 1: 清空 Bitable
    print("\n1. 清空 Bitable...")
    records = client.query_records(BITABLE_APP_TOKEN, BITABLE_TABLE_ID)
    print(f"   现有记录: {len(records)} 条")

    if records:
        ids = [r["record_id"] for r in records]
        batch_size = 500
        for i in range(0, len(ids), batch_size):
            batch = ids[i:i + batch_size]
            client.delete_records(BITABLE_APP_TOKEN, BITABLE_TABLE_ID, batch)
            print(f"      已删除 {len(batch)} 条")
        print("   ✅ Bitable 已清空")

    # Step 2: 读取 Excel 购物车数据
    print("\n2. 读取 Excel 购物车数据...")
    excel_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "直播间4.1-5.17all.xlsx")
    df = pd.read_excel(excel_path, sheet_name="明细")
    df["例子时间"] = pd.to_datetime(df["例子时间"])

    # 只保留 4月+5月 购物车
    cart_df = df[
        (df["例子时间"].dt.month.isin([4, 5])) &
        (df["三级团队"] == "直播间购物车")
    ].copy()
    print(f"   4月+5月 购物车记录: {len(cart_df)} 条")

    # Step 3: 格式化并上传
    print("\n3. 上传数据...")
    field_records = []
    for _, row in cart_df.iterrows():
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
            "是否新量直播间策略": clean_val(row.get("是否新量直播间策略")),
        }
        fields = {k: v for k, v in fields.items() if v is not None}
        field_records.append({"fields": fields})

    batch_size = 500
    success = 0
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
            print(f"   ❌ 上传失败 ({len(batch)} 条): {e}")

    print(f"\n{'=' * 50}")
    print(f"完成: 成功上传 {success} 条购物车记录")
    print(f"{'=' * 50}")


if __name__ == "__main__":
    main()

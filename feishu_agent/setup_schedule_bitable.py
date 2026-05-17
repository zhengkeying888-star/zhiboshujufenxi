"""
飞书排期明细多维表格初始化脚本
==================
功能：
1. 在飞书创建"直播排期明细"多维表格
2. 字段对齐《排期表标准模板规范-v1.0》的一维化表示
3. 打印 app_token / table_id，填入 config_local.py

使用方法：
    1. 确保 config_local.py 已配置好 APP_ID 和 APP_SECRET
    2. python setup_schedule_bitable.py
    3. 脚本会打印 bitable_app_token 和 table_id，请填入 config_local.py
"""

import sys

# 加载本地配置
try:
    from config_local import APP_ID, APP_SECRET
except ImportError:
    print("⚠️ 未找到 config_local.py，使用 config.py 模板")
    from config import APP_ID, APP_SECRET

from feishu_client import FeishuClient

# ========== 字段定义（排期明细一维化） ==========
# type: 1=文本, 2=数字, 3=单选, 5=日期
SCHEDULE_FIELDS = [
    # 日期字段
    {"name": "日期", "type": 5},
    # 文本字段
    {"name": "月份", "type": 1},        # 如"4月"、"5月"，方便按月汇总筛选
    {"name": "品类", "type": 1},        # 标准品类名（见规范附录）
    {"name": "直播名", "type": 1},      # 运营自定义名称
    {"name": "标记", "type": 1},        # 数字人/录播/不回捞/需剪辑，逗号分隔
    {"name": "时间", "type": 1},        # 如 7:00-9:00 或 19:00
    {"name": "文案负责人", "type": 1},
    {"name": "所属周次", "type": 1},    # 如 "5.18-5.24"
    # 单选字段
    {
        "name": "时段",
        "type": 3,
        "property": {
            "options": [
                {"name": "晨练", "color": 0},
                {"name": "晚间", "color": 1},
                {"name": "伪直播", "color": 2},
            ]
        }
    },
    {
        "name": "线级",
        "type": 3,
        "property": {
            "options": [
                {"name": "健康线", "color": 0},
                {"name": "变美线", "color": 1},
                {"name": "兴趣线", "color": 2},
            ]
        }
    },
    # 数字字段
    {"name": "曝光量级", "type": 2},
    {"name": "预估线索数", "type": 2},   # 可选，手动填写或后续关联计算
]


def main():
    print("=" * 50)
    print("飞书排期明细多维表格初始化")
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
    app_token = client.create_bitable("直播排期明细")
    print(f"✅ 多维表格已创建，app_token: {app_token}")

    # 2. 创建数据表
    print("\n📦 步骤2：创建数据表 ...")
    table_id = client.create_table(app_token, "排期明细", "每场直播一条记录，字段对齐排期规范")
    print(f"✅ 数据表已创建，table_id: {table_id}")

    # 3. 添加字段
    print(f"\n📦 步骤3：添加字段（共{len(SCHEDULE_FIELDS)}个）...")
    for field in SCHEDULE_FIELDS:
        prop = field.get("property")
        try:
            fid = client.create_field(app_token, table_id, field["name"], field["type"], prop)
            print(f"   ✅ {field['name']} ({fid})")
        except Exception as e:
            print(f"   ❌ {field['name']} 创建失败: {e}")
            raise

    # 4. 打印配置
    print("\n" + "=" * 50)
    print("🎉 初始化完成！请把以下信息填入 config_local.py：")
    print("=" * 50)
    print(f'SCHEDULE_APP_TOKEN = "{app_token}"')
    print(f'SCHEDULE_TABLE_ID  = "{table_id}"')
    print(f"\n📎 飞书多维表格链接：https://www.feishu.cn/base/{app_token}")
    print("\n💡 使用建议：")
    print("   1. 在多维表中逐条录入未来排期（每行一场直播）")
    print("   2. 或从 Excel 排期表解析后批量导入")
    print("   3. 运行 generate_data.py 时会自动读取排期数据生成 schedule_correlation")
    print("=" * 50)


if __name__ == "__main__":
    main()

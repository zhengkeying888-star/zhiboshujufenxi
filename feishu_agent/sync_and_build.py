"""
数据同步 + 看板生成脚本
==================
功能：
1. 从飞书多维表格读取最新数据
2. 转换为 dashboard_data.json 格式
3. 生成 dashboard.html 看板

使用方法：
    python sync_and_build.py

自动化触发（GitHub Actions / 定时任务）：
    cd feishu_agent && python sync_and_build.py
"""

import json
import sys
from collections import defaultdict
from datetime import datetime

# 加载配置
try:
    from config_local import APP_ID, APP_SECRET, BITABLE_APP_TOKEN, BITABLE_TABLE_ID, DASHBOARD_OUTPUT, DASHBOARD_DATA_JSON
except ImportError:
    print("⚠️ 未找到 config_local.py，使用 config.py 模板")
    from config import APP_ID, APP_SECRET, BITABLE_APP_TOKEN, BITABLE_TABLE_ID, DASHBOARD_OUTPUT, DASHBOARD_DATA_JSON

from feishu_client import FeishuClient


def fetch_data_from_feishu(client: FeishuClient, app_token: str, table_id: str) -> dict:
    """从飞书多维表格读取数据，转换为看板所需格式"""
    print("📡 正在从飞书多维表格读取数据 ...")
    records = client.query_records(app_token, table_id)
    print(f"✅ 读取到 {len(records)} 条记录")

    # 解析记录
    data_by_date = defaultdict(lambda: defaultdict(int))
    team_by_date = defaultdict(lambda: defaultdict(int))
    level_by_month = defaultdict(lambda: defaultdict(int))
    cat_data = defaultdict(lambda: {"3月": 0, "4月": 0, "5月": 0, "team": ""})

    for rec in records:
        fields = rec.get("fields", {})

        # 日期：飞书返回的是毫秒时间戳
        date_ts = fields.get("日期")
        if isinstance(date_ts, (int, float)):
            dt = datetime.fromtimestamp(date_ts / 1000)
        else:
            dt = datetime.strptime(str(date_ts), "%Y/%m/%d")

        month_key = f"{dt.month}月"
        day = dt.day
        date_str = dt.strftime("%Y-%m-%d")

        cat = fields.get("品类名", "未知")
        team = fields.get("二级团队", "未知")
        channel = fields.get("三级团队", "未知")
        level = fields.get("会员等级", "未知")
        count = fields.get("线索数", 1)
        if isinstance(count, str):
            count = int(count)

        # 按渠道分开统计
        if channel == "直播间购物车":
            data_by_date["cart"][(month_key, day)] += count
            team_by_date["cart"][(month_key, team)] += count
            cat_data[cat][month_key] += count
            cat_data[cat]["team"] = team
            level_by_month["cart"][(month_key, level)] += count
        elif channel == "直播间弹幕":
            data_by_date["dm"][(month_key, day)] += count
            team_by_date["dm"][(month_key, team)] += count
            level_by_month["dm"][(month_key, level)] += count

    # 转换为输出格式
    months = ["3月", "4月", "5月"]

    # 1. total_stats
    total_stats = {}
    for m in months:
        total_stats[m] = {
            "购物车": sum(v for (mk, d), v in data_by_date["cart"].items() if mk == m),
            "弹幕": sum(v for (mk, d), v in data_by_date["dm"].items() if mk == m),
        }

    # 2. daily_cart / daily_dm
    daily_cart = {}
    daily_dm = {}
    for m in months:
        daily_cart[m] = {str(d): data_by_date["cart"].get((m, d), 0) for d in range(1, 32)}
        daily_dm[m] = {str(d): data_by_date["dm"].get((m, d), 0) for d in range(1, 32)}

    # 3. team_compare (1-15号同期)
    team_compare = {m: {"健康线": 0, "兴趣变美线": 0} for m in months}
    for rec in records:
        fields = rec.get("fields", {})
        date_ts = fields.get("日期")
        if isinstance(date_ts, (int, float)):
            dt = datetime.fromtimestamp(date_ts / 1000)
        else:
            dt = datetime.strptime(str(date_ts), "%Y/%m/%d")
        month_key = f"{dt.month}月"
        day = dt.day
        team = fields.get("二级团队", "")
        channel = fields.get("三级团队", "")
        count = fields.get("线索数", 1)
        if isinstance(count, str):
            count = int(count)
        if channel == "直播间购物车" and day <= 15 and month_key in team_compare:
            team_compare[month_key][team] = team_compare[month_key].get(team, 0) + count

    # 4. cat_data
    cat_list = []
    for cat, vals in cat_data.items():
        c3, c4, c5 = vals["3月"], vals["4月"], vals["5月"]
        if c4 > 0 and c5 == 0:
            status = "消失"
            change = -100
        elif c4 > 0:
            change = round((c5 - c4) / c4 * 100, 1)
            if change <= -70:
                status = "暴跌"
            elif change <= -30:
                status = "下滑"
            else:
                status = "扛住"
        elif c4 == 0 and c5 > 0:
            status = "新增"
            change = 999
        else:
            status = "无数据"
            change = 0

        cat_list.append({
            "品类": cat,
            "二级团队": vals["team"],
            "3月": c3,
            "4月": c4,
            "5月": c5,
            "环比": change,
            "状态": status,
        })
    cat_list.sort(key=lambda x: x["4月"], reverse=True)

    # 5. level_data
    all_levels = set()
    level_data = {}
    for m in months:
        level_data[m] = {}
        for (mk, lvl), v in level_by_month["cart"].items():
            if mk == m:
                level_data[m][lvl] = level_data[m].get(lvl, 0) + v
                all_levels.add(lvl)

    # 6. findings
    findings = []
    for c in cat_list:
        if c["状态"] == "消失":
            findings.append({"severity": "high", "text": f"{c['品类']} 4月{c['4月']}条→5月直接消失（未排期）"})
        elif c["状态"] == "暴跌":
            findings.append({"severity": "high", "text": f"{c['品类']} 4月{c['4月']}条→5月{c['5月']}条（跌幅{c['环比']}%）"})

    health_3 = team_compare["3月"].get("健康线", 0)
    health_4 = team_compare["4月"].get("健康线", 0)
    health_5 = team_compare["5月"].get("健康线", 0)
    interest_4 = team_compare["4月"].get("兴趣变美线", 0)
    interest_5 = team_compare["5月"].get("兴趣变美线", 0)

    if health_4 > 0:
        h_change = round((health_5 - health_4) / health_4 * 100, 1)
        findings.append({
            "severity": "medium",
            "text": f"健康线同期波动剧烈：4月较3月+{round((health_4 - health_3) / health_3 * 100, 0):.0f}%，5月较4月{h_change}%"
        })
    if interest_4 > 0:
        i_change = round((interest_5 - interest_4) / interest_4 * 100, 1)
        findings.append({
            "severity": "low",
            "text": f"兴趣变美线相对稳定：5月较4月{i_change}%"
        })

    return {
        "total_stats": total_stats,
        "daily_cart": daily_cart,
        "daily_dm": daily_dm,
        "team_compare": team_compare,
        "cat_data": cat_list,
        "level_data": level_data,
        "all_levels": sorted(list(all_levels)),
        "findings": findings,
    }


def generate_dashboard_html(data: dict, output_path: str) -> None:
    """
    基于已有 generate_dashboard.py 的逻辑，直接复用生成 HTML。
    为了避免代码重复，这里直接调用 ../generate_dashboard.py 生成的 dashboard.html 逻辑，
    但由于 generate_dashboard.py 是独立的脚本，我们这里只生成 dashboard_data.json，
    然后调用已有的 generate_dashboard.py 重新生成 HTML。
    """
    # 先生成 dashboard_data.json
    import os
    json_path = os.path.join(os.path.dirname(output_path), "dashboard_data.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"✅ 已生成 {json_path}")

    # 然后调用已有的 generate_dashboard.py
    generate_script = os.path.join(os.path.dirname(__file__), "..", "generate_dashboard.py")
    if os.path.exists(generate_script):
        print(f"🔄 正在调用 {generate_script} 生成看板 ...")
        import subprocess
        result = subprocess.run([sys.executable, generate_script], capture_output=True, text=True, cwd=os.path.dirname(generate_script))
        if result.returncode == 0:
            print(f"✅ 看板已生成: {output_path}")
        else:
            print(f"❌ 生成看板失败: {result.stderr}")
            sys.exit(1)
    else:
        print(f"⚠️ 未找到 {generate_script}，请确保它在项目根目录")


def main():
    print("=" * 50)
    print("数据同步 + 看板生成")
    print("=" * 50)

    if not BITABLE_APP_TOKEN or not BITABLE_TABLE_ID:
        print("\n❌ 错误：请先运行 setup_bitable.py 创建多维表格，并把 token 填入 config_local.py")
        sys.exit(1)

    client = FeishuClient(APP_ID, APP_SECRET)

    # 1. 从飞书读取数据
    data = fetch_data_from_feishu(client, BITABLE_APP_TOKEN, BITABLE_TABLE_ID)

    # 2. 生成看板
    generate_dashboard_html(data, DASHBOARD_OUTPUT)

    print("\n" + "=" * 50)
    print("🎉 完成！看板已更新")
    print(f"📎 数据文件: {DASHBOARD_DATA_JSON}")
    print(f"📎 看板文件: {DASHBOARD_OUTPUT}")
    print("=" * 50)


if __name__ == "__main__":
    main()

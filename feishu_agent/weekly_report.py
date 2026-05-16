"""
周报自动生成脚本
==================
功能：
1. 从飞书多维表格读取最近7天数据
2. 自动生成周报文本
3. 写入飞书文档

使用方法：
    python weekly_report.py

自动化触发：
    建议每周一早上运行（GitHub Actions cron: "0 9 * * 1"）
"""

import json
import sys
from datetime import datetime, timedelta
from collections import defaultdict

# 加载配置
try:
    from config_local import APP_ID, APP_SECRET, BITABLE_APP_TOKEN, BITABLE_TABLE_ID, WEEKLY_DOC_ID
except ImportError:
    from config import APP_ID, APP_SECRET, BITABLE_APP_TOKEN, BITABLE_TABLE_ID, WEEKLY_DOC_ID

from feishu_client import FeishuClient


def fetch_recent_data(client: FeishuClient, app_token: str, table_id: str, days: int = 14):
    """读取最近 N 天的数据"""
    # 飞书查询条件：日期 >= (今天 - days)
    cutoff = int((datetime.now() - timedelta(days=days)).timestamp() * 1000)
    # 简单方式：先读全部，再过滤
    records = client.query_records(app_token, table_id)

    recent = []
    for rec in records:
        fields = rec.get("fields", {})
        date_ts = fields.get("日期")
        if isinstance(date_ts, (int, float)):
            dt = datetime.fromtimestamp(date_ts / 1000)
        else:
            continue
        recent.append({
            "date": dt,
            "cat": fields.get("品类名", "未知"),
            "team": fields.get("二级团队", "未知"),
            "channel": fields.get("三级团队", "未知"),
            "level": fields.get("会员等级", "未知"),
            "count": int(fields.get("线索数", 1)) if not isinstance(fields.get("线索数"), str) else int(fields.get("线索数", 1)),
        })
    return recent


def generate_weekly_report(records: list) -> str:
    """生成周报 Markdown 文本"""
    today = datetime.now()
    this_week_start = today - timedelta(days=today.weekday())
    last_week_start = this_week_start - timedelta(days=7)

    # 分区统计
    this_week_cart = 0
    this_week_dm = 0
    last_week_cart = 0
    last_week_dm = 0

    cat_this = defaultdict(int)
    cat_last = defaultdict(int)
    team_this = defaultdict(int)
    team_last = defaultdict(int)

    for r in records:
        d = r["date"]
        cnt = r["count"]
        is_cart = r["channel"] == "直播间购物车"

        # 本周 (本周一 到 今天)
        if this_week_start <= d <= today:
            if is_cart:
                this_week_cart += cnt
            else:
                this_week_dm += cnt
            cat_this[r["cat"]] += cnt
            team_this[r["team"]] += cnt

        # 上周
        elif last_week_start <= d < this_week_start:
            if is_cart:
                last_week_cart += cnt
            else:
                last_week_dm += cnt
            cat_last[r["cat"]] += cnt
            team_last[r["team"]] += cnt

    # 环比计算
    def pct(a, b):
        if b == 0:
            return "N/A"
        return f"{round((a-b)/b*100, 1):+.1f}%"

    cart_change = pct(this_week_cart, last_week_cart)
    dm_change = pct(this_week_dm, last_week_dm)

    # 品类变化 TOP
    all_cats = set(cat_this.keys()) | set(cat_last.keys())
    cat_changes = []
    for c in all_cats:
        t = cat_this.get(c, 0)
        l = cat_last.get(c, 0)
        if l > 0 or t > 0:
            cat_changes.append((c, t, l, pct(t, l)))
    cat_changes.sort(key=lambda x: abs(float(x[3].replace("%", "").replace("+", ""))) if x[3] != "N/A" else 0, reverse=True)

    # 组装周报
    report = f"""# 直播间线索周报

> 统计周期：{last_week_start.strftime("%Y-%m-%d")} ~ {today.strftime("%Y-%m-%d")}
> 生成时间：{today.strftime("%Y-%m-%d %H:%M")}
> ⚠️ 本报告由自动化脚本生成，根因分析和行动计划需人工补充

---

## 一、核心指标概览

| 指标 | 上周 | 本周 | 环比 |
|------|------|------|------|
| 购物车线索 | {last_week_cart:,} | {this_week_cart:,} | {cart_change} |
| 弹幕线索 | {last_week_dm:,} | {this_week_dm:,} | {dm_change} |

## 二、品类变化 TOP

| 品类 | 上周 | 本周 | 环比 | 状态 |
|------|------|------|------|------|
"""

    for c, t, l, p in cat_changes[:10]:
        status = ""
        if l > 0 and t == 0:
            status = "🔴 消失"
        elif l > 0 and p != "N/A" and float(p.replace("%", "").replace("+", "")) <= -50:
            status = "🟠 暴跌"
        elif l > 0 and p != "N/A" and float(p.replace("%", "").replace("+", "")) <= -20:
            status = "🟡 下滑"
        elif p != "N/A" and float(p.replace("%", "").replace("+", "")) >= 0:
            status = "🟢 增长"
        else:
            status = "➖ 波动"
        report += f"| {c} | {l:,} | {t:,} | {p} | {status} |\n"

    report += f"""
## 三、二级团队对比

| 团队 | 上周 | 本周 | 环比 |
|------|------|------|------|
"""
    for team in ["健康线", "兴趣变美线"]:
        t = team_this.get(team, 0)
        l = team_last.get(team, 0)
        report += f"| {team} | {l:,} | {t:,} | {pct(t, l)} |\n"

    report += """
## 四、根因分析（待补充）

- [ ] 排期变化：哪些品类本周未排期/加场？
- [ ] 话术/引导：直播间引导是否有调整？
- [ ] 投流/宣发：私域宣发力度是否有变化？
- [ ] 外部因素：节假日、竞品活动、平台规则等？

> 💡 请在此区域补充本周线索波动的业务根因

## 五、Action Plan（待补充）

- [ ] 下周排期调整：
- [ ] 话术优化：
- [ ] 投流策略：
- [ ] 其他行动：

> 💡 请在此区域补充下周具体行动计划和负责人

---

*本报告由直播间线索归因智能体自动生成*
"""
    return report


def write_to_feishu_doc(client: FeishuClient, document_id: str, content: str) -> None:
    """把周报内容写入飞书文档"""
    # 获取文档块
    blocks = client.get_doc_blocks(document_id)
    if not blocks:
        raise RuntimeError("无法获取文档块")
    root_block_id = blocks[0]["block_id"]

    # 把 Markdown 转换为飞书 Docx 块结构（简化版：直接写纯文本块）
    # 由于飞书 Docx API 的块结构比较复杂，这里先用纯文本方式写入
    lines = content.split("\n")
    doc_blocks = []
    for line in lines:
        if line.startswith("# "):
            doc_blocks.append({
                "block_type": 1,
                "heading1": {"elements": [{"text_run": {"content": line[2:]}}]}
            })
        elif line.startswith("## "):
            doc_blocks.append({
                "block_type": 2,
                "heading2": {"elements": [{"text_run": {"content": line[3:]}}]}
            })
        elif line.startswith("> "):
            doc_blocks.append({
                "block_type": 4,
                "quote": {"elements": [{"text_run": {"content": line[2:]}}]}
            })
        elif line.startswith("---"):
            doc_blocks.append({"block_type": 15, "divider": {}})
        elif line.strip() == "":
            continue
        else:
            doc_blocks.append({
                "block_type": 3,
                "text": {"elements": [{"text_run": {"content": line}}]}
            })

    # 写入文档（追加到根块）
    client.append_doc_blocks(document_id, root_block_id, doc_blocks)
    print(f"✅ 周报已写入飞书文档: https://www.feishu.cn/docx/{document_id}")


def main():
    print("=" * 50)
    print("周报自动生成")
    print("=" * 50)

    if not BITABLE_APP_TOKEN or not BITABLE_TABLE_ID:
        print("\n❌ 错误：BITABLE_APP_TOKEN 和 BITABLE_TABLE_ID 未配置")
        sys.exit(1)

    client = FeishuClient(APP_ID, APP_SECRET)

    # 1. 读取最近14天数据
    print("\n📡 读取最近14天数据 ...")
    records = fetch_recent_data(client, BITABLE_APP_TOKEN, BITABLE_TABLE_ID, days=14)
    print(f"✅ 读取到 {len(records)} 条记录")

    # 2. 生成周报
    print("\n📝 生成周报 ...")
    report = generate_weekly_report(records)

    # 3. 写入飞书文档
    if not WEEKLY_DOC_ID:
        print("\n📦 WEEKLY_DOC_ID 未配置，创建新文档 ...")
        doc_id = client.create_doc("直播间线索周报")
        print(f"✅ 已创建新文档，document_id: {doc_id}")
        print(f"   请把 {doc_id} 填入 config_local.py 的 WEEKLY_DOC_ID")
    else:
        doc_id = WEEKLY_DOC_ID

    write_to_feishu_doc(client, doc_id, report)

    # 4. 保存本地备份
    local_path = f"weekly_report_{datetime.now().strftime('%Y%m%d')}.md"
    with open(local_path, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"✅ 本地备份: {local_path}")

    print("\n" + "=" * 50)
    print("🎉 周报生成完成！")
    print("=" * 50)


if __name__ == "__main__":
    main()

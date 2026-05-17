"""
月报自动生成脚本
==================
功能：
1. 从 dashboard_data.json 读取月度统计数据
2. 自动生成结构化月报文本 + 可视化图表
3. 写入飞书文档并插入图表

使用方法：
    python monthly_report.py
"""

import json
import sys
import os
import subprocess
from datetime import datetime, timedelta
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from config_local import APP_ID, APP_SECRET, WEEKLY_DOC_ID
except ImportError:
    from config import APP_ID, APP_SECRET, WEEKLY_DOC_ID

from feishu_client import FeishuClient


def load_dashboard_data():
    """加载看板数据"""
    json_path = os.path.join(os.path.dirname(__file__), "..", "dashboard_data.json")
    if os.path.exists(json_path):
        with open(json_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def progress_bar(pct, width=20):
    filled = int(pct / 100 * width)
    empty = width - filled
    bar = "█" * filled + "░" * empty
    return f"[{bar}] {pct:.1f}%"


def status_dot(color):
    colors = {"green": "🟢", "yellow": "🟡", "orange": "🟠", "red": "🔴", "gray": "⚪"}
    return colors.get(color, "⚪")


def generate_monthly_report(data: dict) -> str:
    """生成月报 Markdown 文本"""
    today = datetime.now()
    current_month = f"{today.month}月"
    prev_month = f"{today.month - 1}月" if today.month > 1 else "12月"

    total = data.get("total_stats", {})
    cat_data = data.get("cat_data", [])
    team = data.get("team_compare", {})
    target = data.get("target_tracking", {})
    ca = data.get("core_answer", {})
    pareto = data.get("pareto", {})
    high_value = data.get("high_value_cats", [])
    schedule_corr = data.get("schedule_correlation", {})

    # 本月 vs 上月
    curr_cart = total.get(current_month, {}).get("购物车", 0)
    curr_dm = total.get(current_month, {}).get("弹幕", 0)
    prev_cart = total.get(prev_month, {}).get("购物车", 0)
    prev_dm = total.get(prev_month, {}).get("弹幕", 0)

    def pct(a, b):
        if b == 0:
            return "N/A"
        return f"{round((a - b) / b * 100, 1):+.1f}%"

    cart_change = pct(curr_cart, prev_cart)
    dm_change = pct(curr_dm, prev_dm)

    # 品类排序
    sorted_cats = sorted(cat_data, key=lambda x: x.get(current_month, 0), reverse=True)
    top_cats = sorted_cats[:10]

    # 暴跌 / 增长
    crashed = [c for c in cat_data if c.get("状态") in ["暴跌", "消失"]]
    crashed.sort(key=lambda x: x.get("环比", 0))
    grown = [c for c in cat_data if c.get("环比", 0) > 20]
    grown.sort(key=lambda x: x.get("环比", 0), reverse=True)

    # 高价值
    disappeared = [c for c in high_value if c.get("状态") == "消失"]
    crashed_hv = [c for c in high_value if c.get("状态") == "暴跌"]

    # 线级
    curr_team = team.get(current_month, {})
    prev_team = team.get(prev_month, {})

    # 排期
    not_scheduled = schedule_corr.get("not_scheduled", [])

    report = f"""# 📊 直播间线索月报

> 统计周期：{current_month}1日 ~ {today.strftime("%Y-%m-%d")}
> 生成时间：{today.strftime("%Y-%m-%d %H:%M")}
> ⚠️ 本报告由自动化脚本生成，根因分析和行动计划需人工补充

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## 一、核心指标概览

### 1.1 月度环比

| 指标 | {prev_month} | {current_month} | 环比 |
|------|-------------|----------------|------|
| 🛒 购物车线索 | {prev_cart:,} | {curr_cart:,} | {cart_change} |
| 💬 弹幕线索 | {prev_dm:,} | {curr_dm:,} | {dm_change} |
| 合计 | {prev_cart + prev_dm:,} | {curr_cart + curr_dm:,} | {pct(curr_cart + curr_dm, prev_cart + prev_dm)} |

### 1.2 目标追踪

{progress_bar(target.get("达成率", 0))}

| 指标 | 数值 |
|------|------|
| {current_month}目标 | {target.get(f"{current_month}购物车目标", 'N/A')} 条 |
| 当前进度 | {target.get(f"{current_month}当前(1-15)", 0):,} 条 |
| 达成率 | {target.get('达成率', 0)}% |
| 预估流水 | ¥{target.get('预估流水(按LTV95)', 0):,.0f} |

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## 二、品类排名 TOP10

| 排名 | 品类 | {prev_month} | {current_month} | 环比 | 状态 |
|------|------|------------|----------------|------|------|
"""
    for i, c in enumerate(top_cats, 1):
        s = c.get("状态", "")
        icon = "🔴" if s == "消失" else "🟠" if s == "暴跌" else "🟡" if s == "下滑" else "🟢" if s == "增长" else "⚪"
        report += f"| {i} | {c['品类']} | {c.get(prev_month, 0):,} | {c.get(current_month, 0):,} | {c.get('环比', 0)}% | {icon} {s} |\n"

    report += f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## 三、核心归因结论

**{status_dot('red') if ca.get('total_loss', 0) > 500 else status_dot('yellow')} {current_month}较{prev_month}同期购物车线索跌 {ca.get('total_loss', 0):,} 条**

- 暴跌品类贡献 {ca.get('crashed_pct', 0)}% 跌幅
- 消失品类贡献 {ca.get('disappeared_pct', 0)}% 跌幅
- TOP5 集中度：{prev_month} {pareto.get(prev_month, {}).get('集中度', 0)}% → {current_month} {pareto.get(current_month, {}).get('集中度', 0)}%

### 暴跌品类明细

| 品类 | {prev_month}线索 | {current_month}线索 | 跌幅 | LTV |
|------|---------------|-------------------|------|-----|
"""
    for c in ca.get("crashed_cats_detail", [])[:5]:
        report += f"| {c['品类']} | {c.get(prev_month, 0):,} | {c.get(current_month, 0):,} | {c.get('环比', 0)}% | ¥{c.get('LTV', 0)} |\n"

    report += f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## 四、线级分布

| 线级 | {prev_month} | {current_month} | 变化 |
|------|------------|----------------|------|
"""
    for t_name in ["健康线", "兴趣变美线"]:
        p = prev_team.get(t_name, 0)
        c = curr_team.get(t_name, 0)
        report += f"| {t_name} | {p:,} | {c:,} | {pct(c, p)} |\n"

    report += f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## 五、高价值品类监控

### 5.1 高LTV高线索品类（线索≥50 & LTV≥80）

| 品类 | 4月线索 | 4月LTV | 5月状态 | 5月线索 |
|------|---------|--------|---------|---------|
"""
    for c in high_value[:8]:
        s = c.get("状态", "")
        icon = "🔴" if s == "消失" else "🟠" if s == "暴跌" else "🟢" if s == "扛住" else "⚪"
        report += f"| {c['品类']} | {c.get('4月(1-15)', 0):,} | ¥{c.get('4月LTV', 0)} | {icon} {s} | {c.get('5月(1-15)', 0):,} |\n"

    report += f"""
### 5.2 需复播品类（4月线索≥20但5月未排期）

"""
    if not_scheduled:
        for c in not_scheduled[:8]:
            report += f"- 🔴 **{c['品类']}**：4月{c['4月线索']}条 → 5月未排期\n"
    else:
        report += "- ✅ 暂无高线索品类未排期\n"

    report += f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## 六、下月策略建议（智能推荐）

### 6.1 排期策略

"""
    if disappeared:
        report += "**必播清单（高LTV消失品类）：**\n"
        for c in disappeared[:5]:
            report += f"- [ ] **{c['品类']}**（4月{c.get('4月(1-15)', 0)}条，LTV¥{c.get('4月LTV', 0)}）→ 建议复播\n"
        report += "\n"

    if crashed_hv:
        report += "**加码清单（高LTV暴跌品类）：**\n"
        for c in crashed_hv[:5]:
            report += f"- [ ] **{c['品类']}**（4月{c.get('4月(1-15)', 0)}条→5月{c.get('5月(1-15)', 0)}条，LTV¥{c.get('4月LTV', 0)}）→ 建议增加场次\n"
        report += "\n"

    report += f"""### 6.2 流量与转化策略

- [ ] **缺口追回**：评估是否可通过加场/加大宣发追回线索缺口
- [ ] **高价值用户召回**：V7-V10占比下降，建议针对老岛主群体单独触发MA工作流
- [ ] **话术复盘**：调取4月高转化场次录像，复用到低效场次

### 6.3 监控指标

- [ ] 每日购物车线索是否维持在目标水平
- [ ] 高价值用户（V7-V10）占比是否回升
- [ ] 复播品类的线索转化率是否恢复正常

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## 七、根因分析（待补充）

- [ ] 排期变化：哪些品类本月未排期/加场？
- [ ] 话术/引导：直播间引导是否有调整？
- [ ] 投流/宣发：私域宣发力度是否有变化？
- [ ] 外部因素：节假日、竞品活动、平台规则等？

> 💡 请在此区域补充本月线索波动的业务根因

## 八、Action Plan（待补充）

- [ ] 下月排期调整：
- [ ] 话术优化：
- [ ] 投流策略：
- [ ] 其他行动：

> 💡 请在此区域补充下月具体行动计划和负责人

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

*本报告由直播间线索归因智能体自动生成*
"""
    return report


def _build_and_screenshot(title, subtitle, body_html, chart_js, project_name):
    """使用 chart skill 生成图表并截图"""
    sys.path.insert(0, "/Users/zhengkeying/.claude/skills/chart/scripts")
    from build_chart import build_chart_custom, save_chart, screenshot_chart

    base_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output", "monthly-charts")
    os.makedirs(base_dir, exist_ok=True)
    project_dir = os.path.join(base_dir, project_name)
    os.makedirs(project_dir, exist_ok=True)

    html = build_chart_custom(title=title, subtitle=subtitle, body_html=body_html, chart_js=chart_js)
    save_chart(html, project_dir=project_dir)
    png_path = screenshot_chart(project_dir, filename="screenshot.png", width=1280, height=600)
    return png_path


def generate_monthly_charts(data):
    """生成月报可视化图表，返回 [(标题, 图片路径), ...]"""
    chart_images = []
    total = data.get("total_stats", {})
    cat_data = data.get("cat_data", [])
    team = data.get("team_compare", {})
    ca = data.get("core_answer", {})

    months = ["3月", "4月", "5月"]
    cart_vals = [total.get(m, {}).get("购物车", 0) for m in months]
    dm_vals = [total.get(m, {}).get("弹幕", 0) for m in months]

    # 图表1: 月度总线索趋势
    body_html = '<div id="chart1" style="width:100%;height:420px;"></div>'
    chart_js = f'''
    window.CHART_INSTANCES = [];
    var chart = echarts.init(document.getElementById('chart1'));
    chart.setOption({{
        backgroundColor: '#1a1d27',
        tooltip: {{ trigger: 'axis', axisPointer: {{ type: 'shadow' }} }},
        legend: {{ data: ['购物车', '弹幕'], textStyle: {{ color: '#e1e4ea' }} }},
        grid: {{ left: '3%', right: '4%', bottom: '3%', containLabel: true }},
        xAxis: {{ type: 'category', data: {json.dumps(months)}, axisLabel: {{ color: '#9aa0b4' }} }},
        yAxis: {{ type: 'value', axisLabel: {{ color: '#9aa0b4' }}, splitLine: {{ lineStyle: {{ color: '#2d3148' }} }} }},
        series: [
            {{ name: '购物车', type: 'bar', data: {cart_vals}, itemStyle: {{ color: '#5470c6' }} }},
            {{ name: '弹幕', type: 'bar', data: {dm_vals}, itemStyle: {{ color: '#91cc75' }} }}
        ]
    }});
    CHART_INSTANCES.push(chart);
    '''
    png_path = _build_and_screenshot("月度线索趋势", "3月-5月购物车与弹幕线索量", body_html, chart_js, "monthly-trend")
    if png_path:
        chart_images.append(("月度线索趋势（3-5月）", png_path))

    # 图表2: TOP10 品类排名
    sorted_cats = sorted(cat_data, key=lambda x: x.get("5月", 0), reverse=True)
    top10 = sorted_cats[:10]
    if top10:
        cats = [c["品类"] for c in top10]
        vals_may = [c.get("5月", 0) for c in top10]
        vals_apr = [c.get("4月", 0) for c in top10]

        body_html = '<div id="chart2" style="width:100%;height:480px;"></div>'
        chart_js = f'''
        window.CHART_INSTANCES = [];
        var chart = echarts.init(document.getElementById('chart2'));
        chart.setOption({{
            backgroundColor: '#1a1d27',
            tooltip: {{ trigger: 'axis', axisPointer: {{ type: 'shadow' }} }},
            legend: {{ data: ['4月', '5月'], textStyle: {{ color: '#e1e4ea' }} }},
            grid: {{ left: '3%', right: '4%', bottom: '3%', containLabel: true }},
            xAxis: {{ type: 'value', axisLabel: {{ color: '#9aa0b4' }}, splitLine: {{ lineStyle: {{ color: '#2d3148' }} }} }},
            yAxis: {{ type: 'category', data: {json.dumps(list(reversed(cats)))}, axisLabel: {{ color: '#e1e4ea' }} }},
            series: [
                {{ name: '4月', type: 'bar', data: {list(reversed(vals_apr))}, itemStyle: {{ color: '#5470c6' }} }},
                {{ name: '5月', type: 'bar', data: {list(reversed(vals_may))}, itemStyle: {{ color: '#ee6666' }} }}
            ]
        }});
        CHART_INSTANCES.push(chart);
        '''
        png_path = _build_and_screenshot("品类排名 TOP10", "5月线索量最高的品类", body_html, chart_js, "top-cats")
        if png_path:
            chart_images.append(("品类排名 TOP10（5月）", png_path))

    # 图表3: 线级分布变化
    lines = ["健康线", "兴趣变美线"]
    vals_3 = [team.get("3月", {}).get(l, 0) for l in lines]
    vals_4 = [team.get("4月", {}).get(l, 0) for l in lines]
    vals_5 = [team.get("5月", {}).get(l, 0) for l in lines]

    body_html = '<div id="chart3" style="width:100%;height:420px;"></div>'
    chart_js = f'''
    window.CHART_INSTANCES = [];
    var chart = echarts.init(document.getElementById('chart3'));
    chart.setOption({{
        backgroundColor: '#1a1d27',
        tooltip: {{ trigger: 'axis', axisPointer: {{ type: 'shadow' }} }},
        legend: {{ data: ['3月', '4月', '5月'], textStyle: {{ color: '#e1e4ea' }} }},
        grid: {{ left: '3%', right: '4%', bottom: '3%', containLabel: true }},
        xAxis: {{ type: 'category', data: {json.dumps(lines)}, axisLabel: {{ color: '#9aa0b4' }} }},
        yAxis: {{ type: 'value', axisLabel: {{ color: '#9aa0b4' }}, splitLine: {{ lineStyle: {{ color: '#2d3148' }} }} }},
        series: [
            {{ name: '3月', type: 'bar', data: {vals_3}, itemStyle: {{ color: '#5470c6' }} }},
            {{ name: '4月', type: 'bar', data: {vals_4}, itemStyle: {{ color: '#91cc75' }} }},
            {{ name: '5月', type: 'bar', data: {vals_5}, itemStyle: {{ color: '#ee6666' }} }}
        ]
    }});
    CHART_INSTANCES.push(chart);
    '''
    png_path = _build_and_screenshot("线级分布变化", "3月-5月各线级线索量", body_html, chart_js, "line-level")
    if png_path:
        chart_images.append(("线级分布变化（3-5月）", png_path))

    return chart_images


def write_to_feishu_doc(client: FeishuClient, document_id: str, content: str) -> None:
    """把月报内容写入飞书文档（分批，每批最多50个块）"""
    blocks = client.get_doc_blocks(document_id)
    if not blocks:
        raise RuntimeError("无法获取文档块")
    root_block_id = blocks[0]["block_id"]

    lines = content.split("\n")
    doc_blocks = []
    for line in lines:
        if line.startswith("# "):
            doc_blocks.append({
                "block_type": 3,
                "heading1": {"elements": [{"text_run": {"content": line[2:]}}]}
            })
        elif line.startswith("## "):
            doc_blocks.append({
                "block_type": 4,
                "heading2": {"elements": [{"text_run": {"content": line[3:]}}]}
            })
        elif line.startswith("### "):
            doc_blocks.append({
                "block_type": 5,
                "heading3": {"elements": [{"text_run": {"content": line[4:]}}]}
            })
        elif line.startswith("> "):
            doc_blocks.append({
                "block_type": 15,
                "quote": {"elements": [{"text_run": {"content": line[2:]}}]}
            })
        elif line.strip() == "":
            continue
        elif line.startswith("---") or line.startswith("━━"):
            doc_blocks.append({
                "block_type": 2,
                "text": {"elements": [{"text_run": {"content": "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"}}]}
            })
        else:
            doc_blocks.append({
                "block_type": 2,
                "text": {"elements": [{"text_run": {"content": line}}]}
            })

    batch_size = 50
    for i in range(0, len(doc_blocks), batch_size):
        batch = doc_blocks[i:i + batch_size]
        client.append_doc_blocks(document_id, root_block_id, batch)
        print(f"   已写入块 {i+1}-{min(i+batch_size, len(doc_blocks))} / {len(doc_blocks)}")

    print(f"✅ 月报已写入飞书文档: https://www.feishu.cn/docx/{document_id}")


def main():
    print("=" * 50)
    print("月报自动生成")
    print("=" * 50)

    client = FeishuClient(APP_ID, APP_SECRET)

    # 1. 加载看板数据
    print("\n📊 加载深度归因分析数据 ...")
    data = load_dashboard_data()
    if data:
        print("✅ 已加载 dashboard_data.json")
    else:
        print("❌ 未找到 dashboard_data.json")
        sys.exit(1)

    # 2. 生成月报
    print("\n📝 生成月报 ...")
    report = generate_monthly_report(data)

    # 3. 生成可视化图表
    print("\n📈 生成可视化图表 ...")
    chart_images = generate_monthly_charts(data)
    print(f"✅ 生成 {len(chart_images)} 张图表")

    # 4. 写入飞书文档
    if not WEEKLY_DOC_ID:
        print("\n📦 WEEKLY_DOC_ID 未配置，创建新文档 ...")
        doc_id = client.create_doc("直播间线索月报")
        print(f"✅ 已创建新文档，document_id: {doc_id}")
        print(f"   请把 {doc_id} 填入 config_local.py 的 WEEKLY_DOC_ID")
    else:
        doc_id = WEEKLY_DOC_ID

    write_to_feishu_doc(client, doc_id, report)

    # 5. 插入图表到文档末尾
    if chart_images:
        print("\n📎 插入图表到飞书文档 ...")
        for caption, path in chart_images:
            if not path or not os.path.exists(path):
                print(f"   ⚠️ 跳过缺失的图表: {caption}")
                continue
            try:
                rel_path = os.path.relpath(path, os.path.dirname(os.path.abspath(__file__)))
                subprocess.run(
                    [
                        "lark-cli", "docs", "+media-insert",
                        "--as", "bot",
                        "--doc", doc_id,
                        "--file", rel_path,
                        "--caption", caption,
                        "--align", "center"
                    ],
                    capture_output=True, text=True, check=True
                )
                print(f"   ✅ 已插入: {caption}")
            except subprocess.CalledProcessError as e:
                print(f"   ❌ 插入失败 {caption}: {e.stderr or e.stdout}")

    # 6. 保存本地备份
    local_path = f"monthly_report_{datetime.now().strftime('%Y%m%d')}.md"
    with open(local_path, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"✅ 本地备份: {local_path}")

    if chart_images:
        print(f"✅ 图表保存位置:")
        for caption, path in chart_images:
            print(f"   {caption}: {path}")

    print("\n" + "=" * 50)
    print("🎉 月报生成完成！")
    print("=" * 50)


if __name__ == "__main__":
    main()

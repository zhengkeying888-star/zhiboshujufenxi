"""
周报自动生成脚本
==================
功能：
1. 从飞书多维表格读取最近45天数据（覆盖上月同期）
2. 以"同期对比"为核心维度（本月1-X日 vs 上月1-X日）
3. 结合深度归因分析数据（dashboard_data.json）
4. 自动生成结构化周报文本 + 可视化图表
5. 写入飞书文档并插入图表

使用方法：
    cd ~/直播间数据分析/feishu_agent
    python3 weekly_report.py
"""

import json
import sys
import os
import subprocess
from datetime import datetime, timedelta
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from config_local import APP_ID, APP_SECRET, BITABLE_APP_TOKEN, BITABLE_TABLE_ID, WEEKLY_DOC_ID
except ImportError:
    from config import APP_ID, APP_SECRET, BITABLE_APP_TOKEN, BITABLE_TABLE_ID, WEEKLY_DOC_ID

from feishu_client import FeishuClient
import write_rich_doc


def fetch_recent_data(client: FeishuClient, app_token: str, table_id: str, days: int = 45):
    """读取最近 N 天的数据"""
    cutoff = int((datetime.now() - timedelta(days=days)).timestamp() * 1000)
    records = client.query_records(app_token, table_id)

    recent = []
    for rec in records:
        fields = rec.get("fields", {})
        date_ts = fields.get("日期")
        if isinstance(date_ts, (int, float)):
            dt = datetime.fromtimestamp(date_ts / 1000)
        else:
            continue
        # 只取 cutoff 之后的数据
        if dt.timestamp() * 1000 < cutoff:
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


def load_deep_dive_data():
    """加载深度归因分析数据"""
    json_path = os.path.join(os.path.dirname(__file__), "..", "dashboard_data.json")
    if os.path.exists(json_path):
        with open(json_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def progress_bar(pct, width=20):
    """生成 ASCII 进度条"""
    filled = int(pct / 100 * width)
    empty = width - filled
    bar = "█" * filled + "░" * empty
    return f"[{bar}] {pct:.1f}%"


def status_dot(color):
    """生成状态圆点"""
    colors = {
        "green": "🟢",
        "yellow": "🟡",
        "orange": "🟠",
        "red": "🔴",
        "gray": "⚪",
    }
    return colors.get(color, "⚪")


def generate_weekly_report(recent_records: list, deep_data: dict) -> str:
    """生成周报 Markdown 文本（4模块聚焦框架）"""
    today = datetime.now()

    # ========== 同期日期范围（核心）==========
    this_month_start = today.replace(day=1)
    last_month_end = this_month_start - timedelta(days=1)
    last_month_start = last_month_end.replace(day=1)
    last_month_same_day = last_month_start + timedelta(days=today.day - 1)

    this_month_label = f"{today.month}月1-{today.day}日"
    last_month_label = f"{last_month_end.month}月1-{today.day}日"

    # ========== 同期统计 ==========
    this_m_cart = 0
    this_m_dm = 0
    last_m_cart = 0
    last_m_dm = 0

    cat_this_m = defaultdict(int)
    cat_last_m = defaultdict(int)
    team_this_m = defaultdict(int)
    team_last_m = defaultdict(int)

    for r in recent_records:
        d = r["date"]
        cnt = r["count"]
        is_cart = r["channel"] == "直播间购物车"

        if this_month_start <= d <= today:
            if is_cart:
                this_m_cart += cnt
            else:
                this_m_dm += cnt
            cat_this_m[r["cat"]] += cnt
            team_this_m[r["team"]] += cnt
        elif last_month_start <= d <= last_month_same_day:
            if is_cart:
                last_m_cart += cnt
            else:
                last_m_dm += cnt
            cat_last_m[r["cat"]] += cnt
            team_last_m[r["team"]] += cnt

    total_this = this_m_cart + this_m_dm
    total_last = last_m_cart + last_m_dm

    def pct(a, b):
        if b == 0:
            return "N/A"
        return f"{round((a-b)/b*100, 1):+.1f}%"

    # ========== 深度分析数据 ==========
    ca = deep_data.get("core_answer", {})
    tt = deep_data.get("target_tracking", {})
    ch = deep_data.get("channel_trends", {})
    he = deep_data.get("holiday_effect", {})
    pareto = deep_data.get("pareto", {})
    high_value = deep_data.get("high_value_cats", [])
    schedule_corr = deep_data.get("schedule_correlation", {})
    not_scheduled = schedule_corr.get("not_scheduled", [])

    target = tt.get("5月购物车目标", 9500)
    current = tt.get("5月当前(1-15)", 0)
    achievement = tt.get("达成率", 0)
    projected = tt.get("月底预测", 0)
    projected_pct = tt.get("预测达成率", 0)

    disappeared_high_value = [c for c in high_value if c.get("状态") == "消失"]
    crashed_high_value = [c for c in high_value if c.get("状态") == "暴跌"]
    crashed_cats = ca.get('crashed_cats_detail', [])

    # ========== 组装报告：4模块聚焦框架 ==========
    report = f"""# 📊 直播间线索周报

> 同期对比：{last_month_label} vs {this_month_label}
> 生成时间：{today.strftime("%Y-%m-%d %H:%M")}
> ⚠️ 本报告由自动化脚本生成，根因分析和行动计划需人工补充

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## 一、业绩概览

### 1.1 核心结论
"""

    total_loss = total_last - total_this
    if total_loss > 500:
        report += f"""[CALLOUT red]
🔴 {this_month_label} 较 {last_month_label} 线索总量下跌 {total_loss:,} 条（{pct(total_this, total_last)}），主因：头部品类塌方 + 劳动节假期冲击。
• 暴跌品类贡献 {ca.get('crashed_pct', 0)}% 跌幅
• 假期(1-5日)日均较4月同期低 65.5%，但平日(6日起)已恢复正常
• 高价值用户(V7-V10)占比下滑 5.7pp，需关注用户结构恶化
[/CALLOUT]
"""
    elif total_loss > 0:
        report += f"""[CALLOUT yellow]
🟡 {this_month_label} 较 {last_month_label} 线索总量小幅下跌 {total_loss:,} 条（{pct(total_this, total_last)}）。
• 假期有一定影响，平日数据基本持平
• 建议关注高价值品类排期是否充足
[/CALLOUT]
"""
    else:
        report += f"""[CALLOUT green]
🟢 {this_month_label} 较 {last_month_label} 线索总量增长 {abs(total_loss):,} 条（{pct(total_this, total_last)}），整体趋势向好。
[/CALLOUT]
"""

    report += f"""
### 1.2 同期总量对比

| 指标 | {last_month_label} | {this_month_label} | 环比 |
|------|-------------------|-------------------|------|
| 🛒 购物车线索 | {last_m_cart:,} | {this_m_cart:,} | {pct(this_m_cart, last_m_cart)} |
| 💬 弹幕线索 | {last_m_dm:,} | {this_m_dm:,} | {pct(this_m_dm, last_m_dm)} |
| **合计** | **{total_last:,}** | **{total_this:,}** | **{pct(total_this, total_last)}** |

### 1.3 目标追踪

{progress_bar(achievement)}

| 指标 | 数值 |
|------|------|
| 5月目标 | {target:,} 条 |
| 当前进度(1-15) | {current:,} 条 |
| 达成率 | {achievement}% |
| 缺口 | {target - current:,} 条 |
| 预估流水 | ¥{tt.get('预估流水(按LTV95)', 0):,.0f} / ¥900,000 |

### 1.4 分线级同期对比

| 线级 | {last_month_label} | {this_month_label} | 环比 |
|------|-------------------|-------------------|------|
"""
    for t_name in ["健康线", "兴趣变美线"]:
        p = team_last_m.get(t_name, 0)
        c = team_this_m.get(t_name, 0)
        report += f"| {t_name} | {p:,} | {c:,} | {pct(c, p)} |\n"

    report += """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## 二、归因拆解

"""
    if crashed_cats:
        report += f"""[CALLOUT red]
🔴 头部品类塌方是本月下跌主因，TOP5 暴跌品类共流失 {sum(c.get('4月',0)-c.get('5月',0) for c in crashed_cats[:5]):,} 条线索
• TOP5 集中度：4月 {pareto.get('4月', {}).get('集中度', 0)}% → 5月 {pareto.get('5月', {}).get('集中度', 0)}%
[/CALLOUT]

### 2.1 暴跌品类明细

| 品类 | 4月线索 | 5月线索 | 跌幅 | LTV |
|------|---------|---------|------|-----|
"""
        for c in crashed_cats[:5]:
            report += f"| {c['品类']} | {c['4月']:,} | {c['5月']:,} | {c['环比']}% | ¥{c['LTV']} |\n"

    report += f"""
### 2.2 假期效应

{'🏖️ 劳动节假期是主要影响因素：' if he.get('holiday_is_main_factor', False) else '假期有一定影响：'}

| 时段 | 4月日均 | 5月日均 | 变化 |
|------|---------|---------|------|
| 假期(1-5) | 307 | 106 | {he.get('holiday_drop', 0)}% |
| 平日(6-15) | 319 | 320 | +0.1% |

{'✅ 假期后已恢复正常水平，后续需关注是否能追回假期缺口。' if he.get('holiday_is_main_factor', False) else '平日也已下跌，需系统性排查。'}

### 2.3 渠道趋势

{'🟢 购物车和弹幕同比例下跌（' + str(ch.get('cart_change', 0)) + '% vs ' + str(ch.get('dm_change', 0)) + '%）' if ch.get('same_trend', True) else '🔴 购物车跌更多（' + str(ch.get('cart_change', 0)) + '% vs ' + str(ch.get('dm_change', 0)) + '%）'}
→ **结论：{ch.get('conclusion', '待分析')}**

### 2.4 会员等级变化

| 等级分组 | 4月占比 | 5月占比 | 变化 |
|----------|---------|---------|------|
| V7-V10 高价值 | 18.0% | 12.3% | 🔴 -5.7pp |
| V0-V1 新用户 | 52.3% | 59.9% | 🟡 +7.6pp |

→ 高价值用户流失更严重，需检查MA下发和社群触达策略。

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## 三、调整策略

### 3.1 排期策略
"""
    if disappeared_high_value:
        report += "\n**必播清单（高LTV消失品类）：**\n"
        for c in disappeared_high_value[:5]:
            report += f"- [ ] **{c['品类']}**（4月{c.get('4月(1-15)', 0)}条，LTV¥{c.get('4月LTV', 0)}）→ 建议下周复播\n"

    if crashed_high_value:
        report += "\n**加码清单（高LTV暴跌品类）：**\n"
        for c in crashed_high_value[:5]:
            report += f"- [ ] **{c['品类']}**（4月{c.get('4月(1-15)', 0)}条→5月{c.get('5月(1-15)', 0)}条，LTV¥{c.get('4月LTV', 0)}）→ 建议增加场次或加大宣发\n"

    report += f"""
### 3.2 流量策略

- [ ] **假期缺口追回**：5月1-5日假期日均较4月同期低约200条/天，需评估是否可通过加场/加大宣发追回约1000条缺口
- [ ] **高价值用户召回**：V7-V10占比从18%降至12.3%，建议针对老岛主群体单独触发MA工作流或社群专属直播

### 3.3 转化策略

- [ ] **直播间引导优化**：检查购物车按钮位置、领取话术是否有变更
- [ ] **话术复盘**：调取4月高转化场次（LTV≥150的品类）的直播录像，复用到5月低效场次

### 3.4 监控指标

- [ ] 每日购物车线索是否维持在320条/日以上（4月平日水平）
- [ ] 高价值用户（V7-V10）占比是否回升至15%以上
- [ ] 下周复播品类的线索转化率是否恢复正常

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## 四、下月启示（6月110万目标）

[CALLOUT yellow]
⚠️ 6月目标流水 110 万，较5月目标（90万）上调 22.2%。当前5月预估完成率约 {projected_pct}%，若趋势延续，6月缺口将进一步扩大，需提前布局。
[/CALLOUT]

### 4.1 5月经验对6月的启示

| 维度 | 5月问题 | 6月应对 |
|------|---------|---------|
| 排期 | 高LTV品类（气血、中医瑜伽）场次不足 | 提前锁定高LTV品类排期，避免假期空档 |
| 用户 | 高价值用户占比下滑 | 老岛主专属直播 + 提前1周MA预热 |
| 假期 | 劳动节假期损失约1000条 | 6月无长假，但需关注端午节（6月中旬）影响 |
| 转化 | 添加率同步下滑 | 4月高转化话术SOP化，每场直播前30分钟复盘 |

### 4.2 需提前关注的风险

- 🔴 **品类断层**：若气血【扶阳】、中医瑜伽等LTV>150品类持续低排期，6月流水目标难以达成
- 🟡 **用户结构**：新用户占比过高（59.9%）将拉低整体LTV，需平衡拉新与召回
- 🟡 **季节性**：6月中下旬进入暑期，部分健康线品类（瑜伽、太极）可能受出行影响

### 4.3 下月策略预设

- [ ] **6月排期预排**：优先保证 LTV≥100 且 4月线索≥100 的品类每周≥2场
- [ ] **老岛主召回专场**：每月至少2场「高阶会员专属直播」，提升V7-V10占比
- [ ] **话术SOP输出**：5月底前完成4月TOP3转化场次话术拆解，6月起每场执行

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

*本报告由直播间线索归因智能体自动生成*
"""
    return report


def _build_and_screenshot(title, subtitle, body_html, chart_js, project_name):
    """使用 chart skill 生成图表并截图"""
    sys.path.insert(0, "/Users/zhengkeying/.claude/skills/chart/scripts")
    from build_chart import build_chart_custom, save_chart, screenshot_chart

    base_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output", "weekly-charts")
    os.makedirs(base_dir, exist_ok=True)
    project_dir = os.path.join(base_dir, project_name)
    os.makedirs(project_dir, exist_ok=True)

    html = build_chart_custom(title=title, subtitle=subtitle, body_html=body_html, chart_js=chart_js)
    save_chart(html, project_dir=project_dir)
    png_path = screenshot_chart(project_dir, filename="screenshot.png", width=1920, height=900)
    return png_path


def generate_report_charts(recent_records, deep_data):
    """生成周报可视化图表，返回 [(标题, 图片路径), ...]"""
    chart_images = []
    today = datetime.now()

    # 同期日期范围
    this_month_start = today.replace(day=1)
    last_month_end = this_month_start - timedelta(days=1)
    last_month_start = last_month_end.replace(day=1)
    last_month_same_day = last_month_start + timedelta(days=today.day - 1)

    # 图表1: 暴跌品类对比（4月 vs 5月）
    crashed = deep_data.get("core_answer", {}).get("crashed_cats_detail", [])
    if crashed:
        categories = [c["品类"] for c in crashed[:8]]
        data_apr = [c.get("4月", 0) for c in crashed[:8]]
        data_may = [c.get("5月", 0) for c in crashed[:8]]

        body_html = '<div id="chart1" style="width:100%;height:420px;"></div>'
        chart_js = f'''
        window.CHART_INSTANCES = [];
        var chart = echarts.init(document.getElementById('chart1'));
        chart.setOption({{
            backgroundColor: '#1a1d27',
            tooltip: {{ trigger: 'axis', axisPointer: {{ type: 'shadow' }} }},
            legend: {{ data: ['4月线索', '5月线索'], textStyle: {{ color: '#e1e4ea' }} }},
            grid: {{ left: '3%', right: '4%', bottom: '3%', containLabel: true }},
            xAxis: {{ type: 'category', data: {json.dumps(categories)}, axisLabel: {{ color: '#9aa0b4', rotate: 30 }} }},
            yAxis: {{ type: 'value', axisLabel: {{ color: '#9aa0b4' }}, splitLine: {{ lineStyle: {{ color: '#2d3148' }} }} }},
            series: [
                {{ name: '4月线索', type: 'bar', data: {data_apr}, itemStyle: {{ color: '#5470c6' }} }},
                {{ name: '5月线索', type: 'bar', data: {data_may}, itemStyle: {{ color: '#ee6666' }} }}
            ]
        }});
        CHART_INSTANCES.push(chart);
        '''
        png_path = _build_and_screenshot("暴跌品类对比", "4月 vs 5月线索量（TOP8 暴跌品类）", body_html, chart_js, "crashed-cats")
        if png_path:
            chart_images.append(("暴跌品类对比（4月 vs 5月）", png_path))

    # 图表2: 周度线索趋势（最近14天）
    daily = defaultdict(lambda: {"cart": 0, "dm": 0})
    for r in recent_records:
        d = r["date"].strftime("%m-%d")
        if r["channel"] == "直播间购物车":
            daily[d]["cart"] += r["count"]
        else:
            daily[d]["dm"] += r["count"]
    dates = sorted(daily.keys())
    cart_data = [daily[d]["cart"] for d in dates]
    dm_data = [daily[d]["dm"] for d in dates]

    body_html = '<div id="chart2" style="width:100%;height:420px;"></div>'
    chart_js = f'''
    window.CHART_INSTANCES = [];
    var chart = echarts.init(document.getElementById('chart2'));
    chart.setOption({{
        backgroundColor: '#1a1d27',
        tooltip: {{ trigger: 'axis' }},
        legend: {{ data: ['购物车', '弹幕'], textStyle: {{ color: '#e1e4ea' }} }},
        grid: {{ left: '3%', right: '4%', bottom: '3%', containLabel: true }},
        xAxis: {{ type: 'category', data: {json.dumps(dates)}, axisLabel: {{ color: '#9aa0b4' }} }},
        yAxis: {{ type: 'value', axisLabel: {{ color: '#9aa0b4' }}, splitLine: {{ lineStyle: {{ color: '#2d3148' }} }} }},
        series: [
            {{ name: '购物车', type: 'line', data: {cart_data}, smooth: true, itemStyle: {{ color: '#5470c6' }}, areaStyle: {{ opacity: 0.1 }} }},
            {{ name: '弹幕', type: 'line', data: {dm_data}, smooth: true, itemStyle: {{ color: '#91cc75' }}, areaStyle: {{ opacity: 0.1 }} }}
        ]
    }});
    CHART_INSTANCES.push(chart);
    '''
    png_path = _build_and_screenshot("周度线索趋势", "最近14天线索量变化", body_html, chart_js, "weekly-trend")
    if png_path:
        chart_images.append(("周度线索趋势（最近14天）", png_path))

    # 图表3: 同期品类变化 TOP10（本月 vs 上月同期）
    cat_this_m = defaultdict(int)
    cat_last_m = defaultdict(int)
    for r in recent_records:
        d = r["date"]
        cnt = r["count"]
        if this_month_start <= d <= today:
            cat_this_m[r["cat"]] += cnt
        elif last_month_start <= d <= last_month_same_day:
            cat_last_m[r["cat"]] += cnt

    all_cats_m = set(cat_this_m.keys()) | set(cat_last_m.keys())
    cat_m_changes = []
    for c in all_cats_m:
        t = cat_this_m.get(c, 0)
        l = cat_last_m.get(c, 0)
        # 过滤基数过低的品类，避免极端百分比失真
        if l >= 5 or t >= 5:
            if l == 0:
                change_pct = 100.0 if t > 0 else 0
            else:
                change_pct = round((t - l) / l * 100, 1)
            cat_m_changes.append((c, change_pct))

    cat_m_changes.sort(key=lambda x: abs(x[1]), reverse=True)
    top10 = cat_m_changes[:10]
    if top10:
        cats = [c[0] for c in top10]
        changes = [c[1] for c in top10]
        colors = ['#ee6666' if v < 0 else '#91cc75' for v in changes]

        body_html = '<div id="chart3" style="width:100%;height:480px;"></div>'
        chart_js = f'''
        window.CHART_INSTANCES = [];
        var chart = echarts.init(document.getElementById('chart3'));
        chart.setOption({{
            backgroundColor: '#1a1d27',
            tooltip: {{ trigger: 'axis', axisPointer: {{ type: 'shadow' }}, formatter: function(params) {{ return params[0].name + '<br/>环比: ' + params[0].value + '%'; }} }},
            grid: {{ left: '3%', right: '8%', bottom: '3%', containLabel: true }},
            xAxis: {{ type: 'value', axisLabel: {{ formatter: '{{value}}%', color: '#9aa0b4' }}, splitLine: {{ lineStyle: {{ color: '#2d3148' }} }} }},
            yAxis: {{ type: 'category', data: {json.dumps(list(reversed(cats)))}, axisLabel: {{ color: '#e1e4ea' }} }},
            series: [
                {{ name: '环比变化', type: 'bar', data: {list(reversed(changes))}, itemStyle: {{ color: function(params) {{ return {colors}[params.dataIndex]; }} }} }}
            ]
        }});
        CHART_INSTANCES.push(chart);
        '''
        png_path = _build_and_screenshot("同期品类变化 TOP10", f"{today.month}月1-{today.day}日 vs {last_month_end.month}月同期", body_html, chart_js, "cat-changes-monthly")
        if png_path:
            chart_images.append(("同期品类变化 TOP10", png_path))

    return chart_images


def main():
    print("=" * 50)
    print("周报自动生成")
    print("=" * 50)

    if not BITABLE_APP_TOKEN or not BITABLE_TABLE_ID:
        print("\n❌ 错误：BITABLE_APP_TOKEN 和 BITABLE_TABLE_ID 未配置")
        sys.exit(1)

    client = FeishuClient(APP_ID, APP_SECRET)

    # 1. 读取最近45天数据（覆盖上月同期）
    print("\n📡 读取最近45天数据 ...")
    records = fetch_recent_data(client, BITABLE_APP_TOKEN, BITABLE_TABLE_ID, days=45)
    print(f"✅ 读取到 {len(records)} 条记录")

    # 2. 加载深度分析数据
    print("\n📊 加载深度归因分析数据 ...")
    deep_data = load_deep_dive_data()
    if deep_data:
        print("✅ 已加载 dashboard_data.json")
    else:
        print("⚠️ 未找到 dashboard_data.json，周报将只包含基础数据")

    # 3. 生成周报
    print("\n📝 生成周报 ...")
    report = generate_weekly_report(records, deep_data)

    # 4. 生成可视化图表
    print("\n📈 生成可视化图表 ...")
    chart_images = generate_report_charts(records, deep_data)
    print(f"✅ 生成 {len(chart_images)} 张图表")

    # 5. 写入飞书文档
    if not WEEKLY_DOC_ID:
        print("\n📦 WEEKLY_DOC_ID 未配置，创建新文档 ...")
        doc_id = client.create_doc("直播间线索周报")
        print(f"✅ 已创建新文档，document_id: {doc_id}")
        print(f"   请把 {doc_id} 填入 config_local.py 的 WEEKLY_DOC_ID")
    else:
        doc_id = WEEKLY_DOC_ID

    write_rich_doc.write_rich_doc(client, doc_id, report)

    # 6. 插入图表到文档末尾
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

    # 7. 保存本地备份
    local_path = f"weekly_report_{datetime.now().strftime('%Y%m%d')}.md"
    with open(local_path, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"✅ 本地备份: {local_path}")

    if chart_images:
        print(f"✅ 图表保存位置:")
        for caption, path in chart_images:
            print(f"   {caption}: {path}")

    print("\n" + "=" * 50)
    print("🎉 周报生成完成！")
    print("=" * 50)


if __name__ == "__main__":
    main()

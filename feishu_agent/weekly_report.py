"""
周报自动生成脚本（XML 版本 — 线索数口径）
==================
使用 lark-doc skill 的 XML 格式写入飞书文档。
核心指标：线索数（条），预估流水 = 线索数 × LTV。

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
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from config_local import APP_ID, APP_SECRET, BITABLE_APP_TOKEN, BITABLE_TABLE_ID, WEEKLY_DOC_ID, HISTORY_EXCEL_FILES, EXCEL_SHEET_NAME
except ImportError:
    from config import APP_ID, APP_SECRET, BITABLE_APP_TOKEN, BITABLE_TABLE_ID, WEEKLY_DOC_ID, HISTORY_EXCEL_FILES, EXCEL_SHEET_NAME

from feishu_client import FeishuClient


def fetch_from_excel(days: int = 45):
    """直接从 Excel 读取最近 N 天的数据（绕过 Bitable 20000 条限制）"""
    import pandas as pd
    cutoff = datetime.now() - timedelta(days=days)
    script_dir = os.path.dirname(os.path.abspath(__file__))

    all_dfs = []
    for f in HISTORY_EXCEL_FILES:
        path = os.path.join(script_dir, f)
        if not os.path.exists(path):
            print(f"   ⚠️ 跳过不存在的文件: {path}")
            continue
        df = pd.read_excel(path, sheet_name=EXCEL_SHEET_NAME)
        df['例子时间'] = pd.to_datetime(df['例子时间'], errors='coerce')
        df = df[df['例子时间'] >= cutoff]
        all_dfs.append(df)
        print(f"   ✅ {os.path.basename(path)}: {len(df)} 条")

    if not all_dfs:
        return []

    df = pd.concat(all_dfs, ignore_index=True)
    print(f"✅ Excel 合计读取 {len(df)} 条记录")

    recent = []
    for _, row in df.iterrows():
        dt = row['例子时间']
        if pd.isna(dt):
            continue

        revenue = row.get('首单流水')
        if pd.isna(revenue):
            revenue = 0
        try:
            revenue = float(revenue)
        except (ValueError, TypeError):
            revenue = 0

        strategy = str(row.get("是否新量直播间策略", "")).strip()

        recent.append({
            "date": dt,
            "cat": str(row.get("品类名", "未知")),
            "team": str(row.get("二级团队", "未知")),
            "channel": str(row.get("三级团队", "未知")),
            "level": str(row.get("会员等级", "未知")),
            "clue_count": 1,
            "revenue": revenue,
            "strategy": strategy,
            "stat_month": str(row.get("统计月", "")),
            "teacher": str(row.get("老师名", "")),
            "shooter": str(row.get("投手名称", "")),
        })
    return recent


def fetch_recent_data(client: FeishuClient, app_token: str, table_id: str, days: int = 45):
    """读取最近 N 天的数据（完整字段，线索数口径）"""
    cutoff = int((datetime.now() - timedelta(days=days)).timestamp() * 1000)
    records = client.query_records(app_token, table_id)

    recent = []
    for rec in records:
        fields = rec.get("fields", {})

        # 时间字段：优先"例子时间"，fallback"日期"（兼容旧数据）
        date_ts = fields.get("例子时间") or fields.get("日期")
        if isinstance(date_ts, (int, float)):
            dt = datetime.fromtimestamp(date_ts / 1000)
        else:
            continue

        if dt.timestamp() * 1000 < cutoff:
            continue

        # 首单流水（用于 LTV 计算）
        revenue = fields.get("首单流水")
        if revenue is None or revenue == "":
            revenue = 0
        try:
            revenue = float(revenue)
        except (ValueError, TypeError):
            revenue = 0

        # 是否新量直播间策略（单选字段可能返回 dict）
        strategy = fields.get("是否新量直播间策略", "")
        if isinstance(strategy, dict):
            strategy = strategy.get("text", "")
        elif not isinstance(strategy, str):
            strategy = str(strategy)

        recent.append({
            "date": dt,
            "cat": fields.get("品类名", "未知"),
            "team": fields.get("二级团队", "未知"),
            "channel": fields.get("三级团队", "未知") or fields.get("三级渠道", "未知"),
            "level": fields.get("会员等级", "未知"),
            "clue_count": 1,
            "revenue": revenue,
            "strategy": strategy.strip(),
            "stat_month": fields.get("统计月", ""),
            "teacher": fields.get("老师名", ""),
            "shooter": fields.get("投手名称", ""),
        })
    return recent


def load_deep_dive_data():
    """加载深度归因分析数据"""
    json_path = os.path.join(os.path.dirname(__file__), "..", "dashboard_data.json")
    if os.path.exists(json_path):
        with open(json_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def _escape_xml(text) -> str:
    if text is None:
        return ""
    return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _pct(a, b):
    if b == 0:
        return "N/A"
    return f"{round((a - b) / b * 100, 1):+.1f}%"


def _fmt_count(val: float) -> str:
    """格式化数量（整数）"""
    return f"{int(val):,}"


def _fmt_money(val: float) -> str:
    """格式化金额（万元）"""
    if val >= 10000:
        return f"{val/10000:.1f}万"
    return f"{val:,.0f}"


def _sum_by_period(records, month_start, month_end, strategy_filter=None):
    """按时间段和策略过滤求和（线索数）"""
    cart = 0
    dm = 0
    cat_map = defaultdict(int)
    team_map = defaultdict(int)
    for r in records:
        d = r["date"]
        if not (month_start <= d <= month_end):
            continue
        if strategy_filter is not None and r["strategy"] != strategy_filter:
            continue
        is_cart = r["channel"] == "直播间购物车"
        if is_cart:
            cart += r["clue_count"]
        else:
            dm += r["clue_count"]
        cat_map[r["cat"]] += r["clue_count"]
        team_map[r["team"]] += r["clue_count"]
    return cart, dm, cat_map, team_map


def _calc_ltv(records):
    """从上月数据动态计算 LTV（总流水 / 总线索数）"""
    today = datetime.now()
    last_month_end = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0) - timedelta(days=1)
    last_month_start = last_month_end.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    total_clues = 0
    total_revenue = 0.0
    for r in records:
        if last_month_start <= r["date"] <= last_month_end:
            total_clues += r["clue_count"]
            total_revenue += r["revenue"]

    if total_clues == 0:
        return 95.0  # fallback
    return round(total_revenue / total_clues, 1)


def _generate_backlink_xml() -> str:
    """生成品类后链路分析 XML（正式品/孵化品分表 + 漏斗趋势 + 恶化预警）"""
    try:
        import pandas as pd
    except ImportError:
        return "<!-- 后链路分析：缺少 pandas，跳过 -->"

    # 路径
    base_dir = Path(__file__).parent.parent
    backlink_file = base_dir / "私域导量进度后链路.xlsx"
    backlink_file_new = base_dir / "私域导流后链路补充.xlsx"
    cat_file = base_dir / "【重要】品类归属.xlsx"

    if not cat_file.exists():
        return "<!-- 后链路分析：源文件不存在，跳过 -->"

    # 1. 读取品类归属
    cat_map = pd.read_excel(cat_file, sheet_name="Sheet1")
    cat_attr = {}
    for _, row in cat_map.iterrows():
        cat_attr[str(row["品类"]).strip()] = {
            "线级": str(row["品类属性"]).strip(),
            "类型": str(row["品类情况"]).strip(),
        }
    alias_map = {
        "唱歌【燃老师】": "唱歌",
        "太极：李在峰": "太极",
        "气血【扶阳】": "气血调理",
        "短视频-李扬": "短视频",
        "茶道-戎新宇": "茶道",
        "道家睡眠": "睡眠调理",
        "瑜伽：杨淇": "瑜伽",
    }

    def get_type(name: str) -> str:
        if name in cat_attr:
            return cat_attr[name]["类型"]
        if name in alias_map and alias_map[name] in cat_attr:
            return cat_attr[alias_map[name]]["类型"]
        if name == "中医瑜伽-陈浙南":
            return "正式品"
        return "未分类"

    # 2. 读取后链路数据（优先日度补充文件，fallback 月度汇总）
    if backlink_file_new.exists():
        df_daily = pd.read_excel(backlink_file_new, sheet_name="私域导量进度")
        df_daily["例子时间"] = pd.to_datetime(df_daily["例子时间"])
        df_daily["统计月"] = df_daily["例子时间"].dt.strftime("%Y-%m")
        # 按月汇总
        agg = df_daily.groupby(["统计月", "品类名"]).agg({
            "线索数": "sum",
            "好友数": "sum",
            "进群数": "sum",
            "先导课到课数": "sum",
            "首课到课数": "sum",
            "首课完课数": "sum",
            "首单流水": "sum",
            "直播转化率": "mean",
            "社群转化率": "mean",
        }).reset_index()
        agg["好友率"] = agg["好友数"] / agg["线索数"]
        agg["进群率"] = agg["进群数"] / agg["线索数"]
        agg["先导课到课率"] = agg["先导课到课数"] / agg["线索数"]
        agg["首课到课率"] = agg["首课到课数"] / agg["线索数"]
        agg["首课完课率"] = agg["首课完课数"] / agg["线索数"]
        agg["综合转化率"] = agg["直播转化率"] + agg["社群转化率"]
        agg["LTV"] = agg["首单流水"] / agg["线索数"]
        df = agg
    elif backlink_file.exists():
        df = pd.read_excel(backlink_file, sheet_name="私域导量进度")
    else:
        return "<!-- 后链路分析：源文件不存在，跳过 -->"

    df["类型"] = df["品类名"].apply(get_type)

    # 3. 按月均值漏斗
    funnel_rows = []
    for m in ["2026-03", "2026-04", "2026-05"]:
        sub = df[(df["统计月"] == m) & (df["类型"] == "正式品")]
        if len(sub) == 0:
            continue
        funnel_rows.append({
            "月份": m.replace("2026-", "") + "月",
            "好友率": f"{sub['好友率'].mean() * 100:.1f}%",
            "进群率": f"{sub['进群率'].mean() * 100:.1f}%",
            "先导课到课率": f"{sub['先导课到课率'].mean() * 100:.1f}%",
            "首课到课率": f"{sub['首课到课率'].mean() * 100:.1f}%",
            "首课完课率": f"{sub['首课完课率'].mean() * 100:.1f}%",
            "综合转化率": f"{sub['综合转化率'].mean() * 100:.2f}%",
        })

    funnel_table = ""
    if funnel_rows:
        funnel_table = """<table>
  <thead>
    <tr>
      <th background-color="light-gray">月份</th>
      <th background-color="light-gray">好友率</th>
      <th background-color="light-gray">进群率</th>
      <th background-color="light-gray">先导课到课率</th>
      <th background-color="light-gray">首课到课率</th>
      <th background-color="light-gray">首课完课率</th>
      <th background-color="light-gray">综合转化率</th>
    </tr>
  </thead>
  <tbody>"""
        for r in funnel_rows:
            funnel_table += f"""
    <tr>
      <td>{r['月份']}</td>
      <td>{r['好友率']}</td>
      <td>{r['进群率']}</td>
      <td>{r['先导课到课率']}</td>
      <td>{r['首课到课率']}</td>
      <td>{r['首课完课率']}</td>
      <td><b>{r['综合转化率']}</b></td>
    </tr>"""
        funnel_table += "\n  </tbody>\n</table>"

    # 4. 环比计算（5月 vs 4月）——过程指标口径
    proc_cols = ["好友率", "进群率", "先导课到课率", "首课到课率", "首课完课率", "综合转化率"]
    results = []
    for cat in sorted(df["品类名"].unique()):
        apr = df[(df["品类名"] == cat) & (df["统计月"] == "2026-04")]
        may = df[(df["品类名"] == cat) & (df["统计月"] == "2026-05")]
        if len(apr) == 0 or len(may) == 0:
            continue
        apr = apr.iloc[0]
        may = may.iloc[0]
        cat_type = get_type(cat)

        row = {
            "品类": cat,
            "类型": cat_type,
            "4月线索": int(apr["线索数"]),
            "5月线索": int(may["线索数"]),
        }
        for col in proc_cols:
            a_val = apr.get(col, 0) if pd.notna(apr.get(col)) else 0
            m_val = may.get(col, 0) if pd.notna(may.get(col)) else 0
            row[f"4月{col}"] = round(a_val * 100, 1)
            row[f"5月{col}"] = round(m_val * 100, 1)
            row[f"{col}环比"] = round((m_val - a_val) / a_val * 100, 1) if a_val > 0 else 0
        results.append(row)

    result_df = pd.DataFrame(results)

    def _build_table(sub_df, title):
        if len(sub_df) == 0:
            return ""
        rows = sub_df.sort_values("5月线索", ascending=False)
        html = f"<h2>{title}</h2>\n<table>\n  <thead>\n    <tr>"
        html += "\n      <th background-color=\"light-gray\">品类</th>"
        html += "\n      <th background-color=\"light-gray\">4月线索</th>"
        html += "\n      <th background-color=\"light-gray\">5月线索</th>"
        html += "\n      <th background-color=\"light-gray\">好友率环比</th>"
        html += "\n      <th background-color=\"light-gray\">进群率环比</th>"
        html += "\n      <th background-color=\"light-gray\">到课率环比</th>"
        html += "\n      <th background-color=\"light-gray\">完课率环比</th>"
        html += "\n      <th background-color=\"light-gray\">转化率环比</th>"
        html += "\n    </tr>\n  </thead>\n  <tbody>"
        for _, r in rows.iterrows():
            def _color(v):
                return "text-error" if v < -10 else ("text-tertiary" if v < 0 else "text-secondary")
            html += f"""\n    <tr>
      <td>{_escape_xml(r['品类'])}</td>
      <td>{r['4月线索']}</td>
      <td>{r['5月线索']}</td>
      <td class=\"{_color(r['好友率环比'])}\">{r['好友率环比']:+.1f}%</td>
      <td class=\"{_color(r['进群率环比'])}\">{r['进群率环比']:+.1f}%</td>
      <td class=\"{_color(r['先导课到课率环比'])}\">{r['先导课到课率环比']:+.1f}%</td>
      <td class=\"{_color(r['首课完课率环比'])}\">{r['首课完课率环比']:+.1f}%</td>
      <td class=\"{_color(r['综合转化率环比'])}\">{r['综合转化率环比']:+.1f}%</td>
    </tr>"""
        html += "\n  </tbody>\n</table>"
        return html

    formal_html = _build_table(result_df[result_df["类型"] == "正式品"], "正式品后链路（5月 vs 4月）")
    incub_html = _build_table(result_df[result_df["类型"] == "孵化品"], "孵化品后链路（5月 vs 4月）")

    # 5. 过程指标恶化预警 callout
    warnings = []
    formal = result_df[result_df["类型"] == "正式品"]
    for _, r in formal.iterrows():
        if r["5月线索"] < 30:
            continue
        # 进群率大幅恶化
        if r["进群率环比"] < -15:
            warnings.append(f"{_escape_xml(r['品类'])}：进群率 {r['4月进群率']:.1f}%→{r['5月进群率']:.1f}%（{r['进群率环比']:+.1f}pp），线索{r['5月线索']}条")
        # 完课率大幅恶化
        if r["首课完课率环比"] < -15:
            warnings.append(f"{_escape_xml(r['品类'])}：完课率 {r['4月首课完课率']:.1f}%→{r['5月首课完课率']:.1f}%（{r['首课完课率环比']:+.1f}pp），线索{r['5月线索']}条")
        # 到课率大幅恶化
        if r["先导课到课率环比"] < -15:
            warnings.append(f"{_escape_xml(r['品类'])}：到课率 {r['4月先导课到课率']:.1f}%→{r['5月先导课到课率']:.1f}%（{r['先导课到课率环比']:+.1f}pp），线索{r['5月线索']}条")

    warning_xml = ""
    if warnings:
        warning_xml = """<callout emoji="🔴" background-color="light-red" border-color="red">
  <p><b>过程指标恶化预警（5月 vs 4月）</b></p>
  <ul>"""
        for w in warnings[:6]:
            warning_xml += f"\n    <li>{w}</li>"
        warning_xml += "\n  </ul>\n</callout>"

    # 关键发现：哪层漏最多
    if len(funnel_rows) >= 3:
        # 计算 4月→5月 各层变化
        f4 = next((r for r in funnel_rows if r["月份"] == "04月"), None)
        f5 = next((r for r in funnel_rows if r["月份"] == "05月"), None)
        if f4 and f5:
            layers = [
                ("好友率", float(f4["好友率"].rstrip("%")), float(f5["好友率"].rstrip("%"))),
                ("进群率", float(f4["进群率"].rstrip("%")), float(f5["进群率"].rstrip("%"))),
                ("到课率", float(f4["先导课到课率"].rstrip("%")), float(f5["先导课到课率"].rstrip("%"))),
                ("完课率", float(f4["首课完课率"].rstrip("%")), float(f5["首课完课率"].rstrip("%"))),
            ]
            drops = [(name, f4v - f5v) for name, f4v, f5v in layers if f4v - f5v > 1]
            drops.sort(key=lambda x: x[1], reverse=True)
            if drops:
                top_drop = drops[0]
                key_findings = f"5月正式品<strong>{top_drop[0]}</strong>较4月下降 {top_drop[1]:.1f}pp，是漏斗中恶化最严重的环节；"
                if len(drops) > 1:
                    key_findings += f"其次为{drops[1][0]}（下降{drops[1][1]:.1f}pp）。"
                else:
                    key_findings += "其他环节相对稳定。"
            else:
                key_findings = "5月正式品各过程指标与4月相比整体稳定，无明显恶化。"
        else:
            key_findings = "5月正式品综合转化率较4月下降，需关注进群后运营与课程交付环节。"
    else:
        key_findings = "5月正式品综合转化率较4月下降，需关注进群后运营与课程交付环节。"

    return f"""<h1>五、品类后链路分析</h1>

{warning_xml}

<h2>正式品漏斗趋势</h2>
{funnel_table}

<p><b>关键发现：</b>{key_findings}首单流水因结算周期尚未完全体现，当前重点监控过程指标。</p>

{formal_html}

{incub_html}

<hr/>
"""


def generate_weekly_report_xml(recent_records: list, deep_data: dict) -> list:
    """生成周报 XML，返回 [(章节标识, xml_content), ...]"""
    today = datetime.now()

    # 同期日期范围（重置时间分量，避免当天小时过滤掉月初记录）
    this_month_start = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    last_month_end = this_month_start - timedelta(days=1)
    last_month_start = last_month_end.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    last_month_same_day = (last_month_start + timedelta(days=today.day - 1)).replace(hour=23, minute=59, second=59, microsecond=999999)

    this_month_label = f"{today.month}月1-{today.day}日"
    last_month_label = f"{last_month_end.month}月1-{today.day}日"

    # 全部（购物车口径）
    this_cart, this_dm, cat_this, team_this = _sum_by_period(recent_records, this_month_start, today)
    last_cart, last_dm, cat_last, team_last = _sum_by_period(recent_records, last_month_start, last_month_same_day)

    # 新量（是）
    this_cart_y, this_dm_y, cat_this_y, team_this_y = _sum_by_period(recent_records, this_month_start, today, "是")
    last_cart_y, last_dm_y, cat_last_y, team_last_y = _sum_by_period(recent_records, last_month_start, last_month_same_day, "是")

    # 非新量（否）
    this_cart_n, this_dm_n, cat_this_n, team_this_n = _sum_by_period(recent_records, this_month_start, today, "否")
    last_cart_n, last_dm_n, cat_last_n, team_last_n = _sum_by_period(recent_records, last_month_start, last_month_same_day, "否")

    # 动态 LTV
    ltv = _calc_ltv(recent_records)
    est_revenue_this = this_cart * ltv
    est_revenue_last = last_cart * ltv

    # 深度分析数据
    ca = deep_data.get("core_answer", {})
    tt = deep_data.get("target_tracking", {})
    ch = deep_data.get("channel_trends", {})
    he = deep_data.get("holiday_effect", {})
    ml = deep_data.get("member_levels", {})
    high_value = deep_data.get("high_value_cats", [])
    crashed_cats = ca.get('crashed_cats_detail', [])
    schedule_corr = deep_data.get("schedule_correlation", {})

    # 目标追踪（当前预测LTV=76.74 口径，与业务系统对齐）
    revenue_target = 900000
    ltv_forecast = 76.74
    target_clues = round(revenue_target / ltv_forecast)  # ≈ 9278
    current_clues = this_cart
    achievement = round(current_clues / target_clues * 100, 1) if target_clues > 0 else 0
    daily_avg = round(current_clues / today.day, 1) if today.day > 0 else 0
    projected_clues = round(daily_avg * 31, 1)
    projected_pct = round(projected_clues / target_clues * 100, 1) if target_clues > 0 else 0
    est_revenue = round(current_clues * ltv_forecast, 0)
    est_revenue_this = this_cart * ltv_forecast

    disappeared_high_value = [c for c in high_value if c.get("状态") == "消失"]
    crashed_high_value = [c for c in high_value if c.get("状态") == "暴跌"]

    # 策略占比
    cart_stats_strategy = deep_data.get("cart_stats_by_strategy", {})
    apr_y_pct = cart_stats_strategy.get("4月", {}).get("是占比", 0)
    may_y_pct = cart_stats_strategy.get("5月", {}).get("是占比", 0)

    # 会员等级数据（动态）
    ml_prev = ml.get(last_month_label.split("月")[0] + "月", {})
    ml_curr = ml.get(str(today.month) + "月", {})
    prev_high = ml_prev.get("pct", {}).get("V7-V10 高价值", 0)
    curr_high = ml_curr.get("pct", {}).get("V7-V10 高价值", 0)
    prev_new = ml_prev.get("pct", {}).get("V0-V1 新用户", 0)
    curr_new = ml_curr.get("pct", {}).get("V0-V1 新用户", 0)
    high_drop_pp = round(curr_high - prev_high, 1) if prev_high else 0
    new_rise_pp = round(curr_new - prev_new, 1) if prev_new else 0

    # 假期数据
    holiday_drop = he.get("holiday_drop", 0)
    normal_drop = he.get("normal_drop", 0)
    holiday_is_main = he.get("holiday_is_main_factor", False)
    he_counts = he.get("counts", {})
    prev_holiday_key = [k for k in he_counts if "假期" in k and last_month_label.split("月")[0] + "月" in k]
    curr_holiday_key = [k for k in he_counts if "假期" in k and str(today.month) + "月" in k]
    prev_holiday_cnt = he_counts.get(prev_holiday_key[0], 0) if prev_holiday_key else 0
    curr_holiday_cnt = he_counts.get(curr_holiday_key[0], 0) if curr_holiday_key else 0

    # 归因计算
    cart_loss = last_cart - this_cart
    crashed_loss = sum(c.get('4月', 0) - c.get('5月', 0) for c in crashed_cats[:3]) if crashed_cats else 0
    crashed_pct = ca.get('crashed_pct', 0)

    # 头部信息
    header_xml = f"""<title>直播间线索周报</title>
<callout emoji="ℹ️" background-color="light-blue" border-color="blue">
  <p>同期对比：{_escape_xml(last_month_label)} vs {_escape_xml(this_month_label)} | 生成时间：{_escape_xml(today.strftime('%Y-%m-%d %H:%M'))} | 口径：线索数（条） | 上月LTV≈¥{ltv}</p>
</callout>"""

    # Part 1: 总体指标
    if cart_loss > 500:
        callout_color, callout_emoji = "red", "🔴"
        callout_text = f"{this_month_label} 较 {last_month_label} 购物车线索下跌 {_fmt_count(cart_loss)} 条（{_pct(this_cart, last_cart)}），主因：头部品类塌方 + 假期冲击。"
    elif cart_loss > 0:
        callout_color, callout_emoji = "yellow", "🟡"
        callout_text = f"{this_month_label} 较 {last_month_label} 购物车线索小幅下跌 {_fmt_count(cart_loss)} 条（{_pct(this_cart, last_cart)}）。"
    else:
        callout_color, callout_emoji = "green", "🟢"
        callout_text = f"{this_month_label} 较 {last_month_label} 购物车线索增长 {_fmt_count(abs(cart_loss))} 条（{_pct(this_cart, last_cart)}），整体趋势向好。"

    part1 = f"""<h1>一、总体指标</h1>
<callout emoji="{callout_emoji}" background-color="light-{callout_color}" border-color="{callout_color}">
  <p>{_escape_xml(callout_text)}</p>
</callout>

<grid>
  <column width-ratio="0.25">
    <p><b>🛒 购物车线索</b></p>
    <p><span text-color="red">{_fmt_count(this_cart)}</span></p>
    <p>环比 <span text-color="red">{_pct(this_cart, last_cart)}</span></p>
  </column>
  <column width-ratio="0.25">
    <p><b>🆕 新量策略</b></p>
    <p><span text-color="red">{_fmt_count(this_cart_y)}</span></p>
    <p>占比 {round(this_cart_y / this_cart * 100, 1) if this_cart else 0}%（4月 {apr_y_pct}%）</p>
  </column>
  <column width-ratio="0.25">
    <p><b>📉 非新量策略</b></p>
    <p>{_fmt_count(this_cart_n)}</p>
    <p>环比 {_pct(this_cart_n, last_cart_n)}</p>
  </column>
  <column width-ratio="0.25">
    <p><b>💰 预估流水</b></p>
    <p><span text-color="red">{_fmt_money(est_revenue_this)}</span></p>
    <p>按LTV¥{ltv_forecast}估算</p>
  </column>
</grid>"""

    # Part 2: 目标进度-总
    part2 = f"""<h1>二、目标进度-总</h1>

<grid>
  <column width-ratio="0.25">
    <p><b>🎯 5月线索目标</b></p>
    <p>{_fmt_count(target_clues)}</p>
    <p>按LTV¥{ltv_forecast}反推</p>
  </column>
  <column width-ratio="0.25">
    <p><b>📍 当前进度</b></p>
    <p><span text-color="red">{_fmt_count(current_clues)} ({achievement}%)</span></p>
  </column>
  <column width-ratio="0.25">
    <p><b>🔮 月底预测</b></p>
    <p>{_fmt_count(int(projected_clues))} ({projected_pct}%)</p>
  </column>
  <column width-ratio="0.25">
    <p><b>💰 预估流水</b></p>
    <p><span text-color="red">{_fmt_money(est_revenue)}</span></p>
    <p>目标 {_fmt_money(revenue_target)}</p>
  </column>
</grid>

<h2>分线级同期对比</h2>
<table>
  <thead>
    <tr>
      <th background-color="light-gray">线级</th>
      <th background-color="light-gray">{_escape_xml(last_month_label)}</th>
      <th background-color="light-gray">{_escape_xml(this_month_label)}</th>
      <th background-color="light-gray">环比</th>
    </tr>
  </thead>
  <tbody>
"""
    for t_name in ["健康线", "兴趣变美线"]:
        p = team_last.get(t_name, 0)
        c = team_this.get(t_name, 0)
        part2 += f'    <tr><td>{_escape_xml(t_name)}</td><td>{_fmt_count(p)}</td><td>{_fmt_count(c)}</td><td><span text-color="red">{_pct(c, p)}</span></td></tr>\n'
    part2 += """  </tbody>
</table>"""

    # Part 3: 构成拆分（正常排期+新用户策略，同期环比）
    cat_by_strategy = deep_data.get("cat_data_by_strategy", [])
    strategy_cat_rows_list = []
    for c in cat_by_strategy[:30]:
        if c.get("4月", 0) == 0 and c.get("5月", 0) == 0:
            continue
        strategy_label = "新量-是" if c.get("策略") == "是" else "非新量-否"
        strategy_cat_rows_list.append(
            f'    <tr><td>{_escape_xml(c["品类"])}</td><td>{_escape_xml(strategy_label)}</td>'
            f'<td>{_fmt_count(c.get("4月", 0))}</td><td>{_fmt_count(c.get("5月", 0))}</td>'
            f'<td><span text-color="red">{_pct(c.get("5月", 0), c.get("4月", 0))}</span></td>'
            f'<td>{_escape_xml(c.get("状态", ""))}</td></tr>'
        )
    strategy_cat_rows = "\n".join(strategy_cat_rows_list)

    part3 = f"""<h1>三、构成拆分（正常排期+新用户策略，同期环比）</h1>

<table>
  <thead>
    <tr>
      <th background-color="light-gray">策略</th>
      <th background-color="light-gray">4月线索</th>
      <th background-color="light-gray">4月占比</th>
      <th background-color="light-gray">5月线索</th>
      <th background-color="light-gray">5月占比</th>
      <th background-color="light-gray">环比</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td>新量策略（是）</td>
      <td>{_fmt_count(cart_stats_strategy.get('4月', {}).get('是', 0))}</td>
      <td>{cart_stats_strategy.get('4月', {}).get('是占比', 0)}%</td>
      <td>{_fmt_count(cart_stats_strategy.get('5月', {}).get('是', 0))}</td>
      <td>{cart_stats_strategy.get('5月', {}).get('是占比', 0)}%</td>
      <td><span text-color="red">{_pct(cart_stats_strategy.get('5月', {}).get('是', 0), cart_stats_strategy.get('4月', {}).get('是', 0))}</span></td>
    </tr>
    <tr>
      <td>非新量策略（否）</td>
      <td>{_fmt_count(cart_stats_strategy.get('4月', {}).get('否', 0))}</td>
      <td>{100 - cart_stats_strategy.get('4月', {}).get('是占比', 0)}%</td>
      <td>{_fmt_count(cart_stats_strategy.get('5月', {}).get('否', 0))}</td>
      <td>{100 - cart_stats_strategy.get('5月', {}).get('是占比', 0)}%</td>
      <td><span text-color="red">{_pct(cart_stats_strategy.get('5月', {}).get('否', 0), cart_stats_strategy.get('4月', {}).get('否', 0))}</span></td>
    </tr>
  </tbody>
</table>"""

    # Part 4: 目标差距分析 归因123
    _holiday_impact_cnt = prev_holiday_cnt - curr_holiday_cnt

    part4 = f"""<h1>四、目标差距分析 归因123</h1>

<callout emoji="📉" background-color="light-red" border-color="red">
  <p><b>总跌幅 {_fmt_count(cart_loss)} 条（{_pct(this_cart, last_cart)}）</b>，三大归因拆解如下：</p>
</callout>

<h2>归因1：假期冲击</h2>
<callout emoji="🏖️" background-color="light-yellow" border-color="yellow">
  <p>劳动节假期（1-5日）购物车线索从 {prev_holiday_cnt:,} 条跌至 {curr_holiday_cnt:,} 条，跌幅 <b>{holiday_drop}%</b>，直接影响约 {_fmt_count(_holiday_impact_cnt)} 条线索。</p>
</callout>

<h2>归因2：头部品类塌方</h2>
<callout emoji="🔴" background-color="light-red" border-color="red">
  <p>TOP3 暴跌品类（一杰瑜伽、气血、中医瑜伽）共流失 {_fmt_count(crashed_loss)} 条线索，贡献总跌幅的 <b>{crashed_pct}%</b>。</p>
</callout>

<h2>归因3：高价值用户流失</h2>
<callout emoji="👥" background-color="light-yellow" border-color="yellow">
  <p>V7-V10 高价值用户占比从 {prev_high}% 降至 {curr_high}%（跌 {abs(high_drop_pp):.1f}pp），新用户占比从 {prev_new}% 升至 {curr_new}%（升 {new_rise_pp:.1f}pp），用户结构恶化拉低整体LTV。</p>
</callout>"""

    # Part 5: 品类后链路分析
    part5 = _generate_backlink_xml()

    # Part 6: 下一步迭代策略（精简版：3个核心 checkbox + 下月启示）
    part6 = f"""<h1>六、下一步迭代策略</h1>

<h2>核心行动</h2>
<checkbox done="false">追回假期缺口：评估加场/加大宣发追回约{_fmt_count(int(target_clues * 0.1))}条线索</checkbox>
<checkbox done="false">高价值用户召回：V7-V10占比降至{curr_high}%，建议老岛主专属直播或社群专属场次</checkbox>
<checkbox done="false">头部品类复播：气血、中医瑜伽等LTV&gt;150品类尽快恢复排期</checkbox>

<h2>下月启示（6月110万目标）</h2>
<callout emoji="⚠️" background-color="light-yellow" border-color="yellow">
  <p>6月目标流水 110 万，较5月（90万）上调 22.2%。当前线索预估完成率 {projected_pct}%，若趋势延续缺口将进一步扩大。</p>
</callout>
<ul>
  <li><span text-color="red">🔴 品类断层：</span>气血、中医瑜伽等LTV&gt;150品类若持续低排期，6月流水目标难以达成</li>
  <li><span text-color="yellow">🟡 用户结构：</span>新用户占比过高（{curr_new}%）将拉低整体LTV，需平衡拉新与召回</li>
  <li><span text-color="yellow">🟡 季节性：</span>6月中下旬暑期，健康线品类可能受出行影响</li>
</ul>

<hr/>
<p><em>本报告由直播间线索归因智能体自动生成 | 口径：线索数（条） | 预估流水按预测LTV¥{ltv_forecast}计算</em></p>"""

    return [
        ("header", header_xml),
        ("一、总体指标", part1),
        ("二、目标进度-总", part2),
        ("三、构成拆分", part3),
        ("四、目标差距分析 归因123", part4),
        ("五、品类后链路分析", part5),
        ("六、下一步迭代策略", part6),
    ]


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

    this_month_start = today.replace(day=1)
    last_month_end = this_month_start - timedelta(days=1)
    last_month_start = last_month_end.replace(day=1)
    last_month_same_day = last_month_start + timedelta(days=today.day - 1)

    # ---------- 图表1: 策略构成饼图（4月 vs 5月） ----------
    cart_stats = deep_data.get("cart_stats_by_strategy", {})
    apr_y = cart_stats.get("4月", {}).get("是", 0)
    apr_n = cart_stats.get("4月", {}).get("否", 0)
    may_y = cart_stats.get("5月", {}).get("是", 0)
    may_n = cart_stats.get("5月", {}).get("否", 0)

    if (apr_y + apr_n) > 0 and (may_y + may_n) > 0:
        body_html = '<div style="display:flex;justify-content:space-between;"><div id="pie1" style="width:48%;height:420px;"></div><div id="pie2" style="width:48%;height:420px;"></div></div>'
        chart_js = f'''
        window.CHART_INSTANCES = [];
        var pie1 = echarts.init(document.getElementById('pie1'));
        pie1.setOption({{
            backgroundColor: '#1a1d27',
            title: {{ text: '4月策略构成', left: 'center', textStyle: {{ color: '#e1e4ea' }} }},
            tooltip: {{ trigger: 'item', formatter: '{{b}}: {{c}}条 ({{d}}%)' }},
            series: [{{
                type: 'pie', radius: ['40%', '70%'], center: ['50%', '55%'],
                label: {{ show: true, formatter: '{{b}}\\n{{d}}%', color: '#e1e4ea' }},
                data: [
                    {{ value: {apr_y}, name: '新量策略', itemStyle: {{ color: '#5470c6' }} }},
                    {{ value: {apr_n}, name: '非新量策略', itemStyle: {{ color: '#91cc75' }} }}
                ]
            }}]
        }});
        CHART_INSTANCES.push(pie1);
        var pie2 = echarts.init(document.getElementById('pie2'));
        pie2.setOption({{
            backgroundColor: '#1a1d27',
            title: {{ text: '5月策略构成', left: 'center', textStyle: {{ color: '#e1e4ea' }} }},
            tooltip: {{ trigger: 'item', formatter: '{{b}}: {{c}}条 ({{d}}%)' }},
            series: [{{
                type: 'pie', radius: ['40%', '70%'], center: ['50%', '55%'],
                label: {{ show: true, formatter: '{{b}}\\n{{d}}%', color: '#e1e4ea' }},
                data: [
                    {{ value: {may_y}, name: '新量策略', itemStyle: {{ color: '#5470c6' }} }},
                    {{ value: {may_n}, name: '非新量策略', itemStyle: {{ color: '#91cc75' }} }}
                ]
            }}]
        }});
        CHART_INSTANCES.push(pie2);
        '''
        png_path = _build_and_screenshot("策略构成对比", "4月 vs 5月新量策略占比", body_html, chart_js, "strategy-composition")
        if png_path:
            chart_images.append(("策略构成对比（4月 vs 5月）", png_path))

    # ---------- 图表2: 目标达成仪表盘 ----------
    tt = deep_data.get("target_tracking", {})
    target_clues = tt.get("购物车线索目标", 11728)
    current_clues = tt.get("5月当前(1-15)", 0)
    achievement = round(current_clues / target_clues * 100, 1) if target_clues > 0 else 0
    body_html = '<div id="gauge1" style="width:100%;height:420px;"></div>'
    chart_js = f'''
    window.CHART_INSTANCES = [];
    var gauge = echarts.init(document.getElementById('gauge1'));
    gauge.setOption({{
        backgroundColor: '#1a1d27',
        series: [{{
            type: 'gauge', startAngle: 180, endAngle: 0, min: 0, max: 100,
            splitNumber: 10,
            axisLine: {{ lineStyle: {{ width: 30, color: [[{achievement/100}, '#5470c6'], [1, '#2d3148']] }} }},
            pointer: {{ itemStyle: {{ color: 'auto' }} }},
            axisTick: {{ show: false }}, splitLine: {{ length: 30, lineStyle: {{ color: 'auto', width: 2 }} }},
            axisLabel: {{ color: '#9aa0b4', distance: 40, formatter: '{{value}}%' }},
            title: {{ offsetCenter: [0, '-20%'], fontSize: 20, color: '#e1e4ea' }},
            detail: {{ fontSize: 50, offsetCenter: [0, '0%'], valueAnimation: true, formatter: '{{value}}%', color: 'auto' }},
            data: [{{ value: {achievement}, name: '5月目标达成率' }}]
        }}]
    }});
    CHART_INSTANCES.push(gauge);
    '''
    png_path = _build_and_screenshot("目标达成仪表盘", f"5月购物车线索目标 {target_clues} 条", body_html, chart_js, "target-gauge")
    if png_path:
        chart_images.append(("目标达成仪表盘", png_path))

    # ---------- 图表3: 暴跌品类对比（4月 vs 5月） ----------
    crashed = deep_data.get("core_answer", {}).get("crashed_cats_detail", [])
    if crashed:
        categories = [c["品类"] for c in crashed[:8]]
        data_apr = [c.get("4月", 0) for c in crashed[:8]]
        data_may = [c.get("5月", 0) for c in crashed[:8]]

        body_html = '<div id="chart3" style="width:100%;height:420px;"></div>'
        chart_js = f'''
        window.CHART_INSTANCES = [];
        var chart = echarts.init(document.getElementById('chart3'));
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
        png_path = _build_and_screenshot("暴跌品类对比", "4月 vs 5月线索数（TOP8 暴跌品类）", body_html, chart_js, "crashed-cats")
        if png_path:
            chart_images.append(("暴跌品类对比（4月 vs 5月）", png_path))

    # ---------- 图表4: 假期冲击图 ----------
    he = deep_data.get("holiday_effect", {})
    he_counts = he.get("counts", {})
    prev_h_keys = [k for k in he_counts if "假期" in k]
    prev_n_keys = [k for k in he_counts if "平日" in k]
    if len(prev_h_keys) >= 2 and len(prev_n_keys) >= 2:
        vals = [he_counts.get(prev_h_keys[0], 0), he_counts.get(prev_h_keys[1], 0),
                he_counts.get(prev_n_keys[0], 0), he_counts.get(prev_n_keys[1], 0)]
        labels = ['4月假期', '5月假期', '4月平日', '5月平日']
        colors_bar = ['#5470c6', '#ee6666', '#5470c6', '#91cc75']
        body_html = '<div id="chart4" style="width:100%;height:420px;"></div>'
        chart_js = f'''
        window.CHART_INSTANCES = [];
        var chart = echarts.init(document.getElementById('chart4'));
        chart.setOption({{
            backgroundColor: '#1a1d27',
            tooltip: {{ trigger: 'axis', axisPointer: {{ type: 'shadow' }} }},
            grid: {{ left: '3%', right: '4%', bottom: '3%', containLabel: true }},
            xAxis: {{ type: 'category', data: {json.dumps(labels)}, axisLabel: {{ color: '#9aa0b4' }} }},
            yAxis: {{ type: 'value', axisLabel: {{ color: '#9aa0b4' }}, splitLine: {{ lineStyle: {{ color: '#2d3148' }} }} }},
            series: [{{
                type: 'bar', data: {vals},
                itemStyle: {{ color: function(params) {{ return {colors_bar}[params.dataIndex]; }} }},
                label: {{ show: true, position: 'top', color: '#e1e4ea', formatter: '{{c}}' }}
            }}]
        }});
        CHART_INSTANCES.push(chart);
        '''
        png_path = _build_and_screenshot("假期冲击对比", "4月 vs 5月 假期/平日线索数", body_html, chart_js, "holiday-impact")
        if png_path:
            chart_images.append(("假期冲击对比", png_path))

    # ---------- 图表5: 会员等级变化（堆叠柱状图） ----------
    ml = deep_data.get("member_levels", {})
    months_ml = sorted(ml.keys())
    if len(months_ml) >= 2:
        groups = ["V0-V1 新用户", "V2-V6 普通会员", "V7-V10 高价值"]
        group_colors = {"V0-V1 新用户": "#91cc75", "V2-V6 普通会员": "#fac858", "V7-V10 高价值": "#5470c6"}
        series_data = []
        for g in groups:
            data = [ml.get(m, {}).get("pct", {}).get(g, 0) for m in months_ml[-3:]]
            series_data.append(f"{{ name: '{g}', type: 'bar', stack: 'total', data: {data}, itemStyle: {{ color: '{group_colors[g]}' }} }}")
        body_html = '<div id="chart5" style="width:100%;height:420px;"></div>'
        chart_js = f'''
        window.CHART_INSTANCES = [];
        var chart = echarts.init(document.getElementById('chart5'));
        chart.setOption({{
            backgroundColor: '#1a1d27',
            tooltip: {{ trigger: 'axis', axisPointer: {{ type: 'shadow' }}, formatter: function(params) {{ var s = params[0].name + "<br/>"; for(var i=0;i<params.length;i++){{ s += params[i].marker + params[i].seriesName + ": " + params[i].value + "%<br/>"; }} return s; }} }},
            legend: {{ data: {json.dumps(groups)}, textStyle: {{ color: '#e1e4ea' }} }},
            grid: {{ left: '3%', right: '4%', bottom: '3%', containLabel: true }},
            xAxis: {{ type: 'category', data: {json.dumps(months_ml[-3:])}, axisLabel: {{ color: '#9aa0b4' }} }},
            yAxis: {{ type: 'value', axisLabel: {{ formatter: '{{value}}%', color: '#9aa0b4' }}, splitLine: {{ lineStyle: {{ color: '#2d3148' }} }} }},
            series: [{','.join(series_data)}]
        }});
        CHART_INSTANCES.push(chart);
        '''
        png_path = _build_and_screenshot("会员等级结构变化", "近3个月用户等级占比", body_html, chart_js, "member-level-change")
        if png_path:
            chart_images.append(("会员等级结构变化", png_path))

    # ---------- 图表6: 同期品类变化 TOP10 ----------
    cat_this_m = defaultdict(int)
    cat_last_m = defaultdict(int)
    for r in recent_records:
        d = r["date"]
        if this_month_start <= d <= today:
            cat_this_m[r["cat"]] += r["clue_count"]
        elif last_month_start <= d <= last_month_same_day:
            cat_last_m[r["cat"]] += r["clue_count"]

    all_cats_m = set(cat_this_m.keys()) | set(cat_last_m.keys())
    cat_m_changes = []
    for c in all_cats_m:
        t = cat_this_m.get(c, 0)
        l = cat_last_m.get(c, 0)
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

        body_html = '<div id="chart6" style="width:100%;height:480px;"></div>'
        chart_js = f'''
        window.CHART_INSTANCES = [];
        var chart = echarts.init(document.getElementById('chart6'));
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


def _lark_update(doc_id: str, command: str, content: str):
    """调用 lark-cli docs +update"""
    cmd = [
        "lark-cli", "docs", "+update",
        "--api-version", "v2",
        "--as", "bot",
        "--doc", doc_id,
        "--command", command,
        "--content", content,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        err = result.stderr or result.stdout
        raise RuntimeError(f"lark-cli docs +update 失败: {err}")
    return result


def _set_doc_permission(doc_id: str, doc_type: str = "docx"):
    """设置飞书文档权限为组织内可读（docx/wiki 自动适配）"""
    import json
    body = {
        "security_entity": "anyone_can_view",
        "comment_entity": "anyone_can_view",
    }
    if doc_type == "docx":
        body["link_share_entity"] = "tenant_readable"
        body["external_access"] = False
        body["share_entity"] = "anyone"
    elif doc_type == "wiki":
        # wiki 不支持 link_share_entity 的 anyone 选项，仅设置安全属性
        body["link_share_entity"] = "tenant_readable"
    else:
        return

    cmd = [
        "lark-cli", "drive", "permission.public", "patch",
        "--params", json.dumps({"token": doc_id, "type": doc_type}),
        "--data", json.dumps(body),
        "--as", "bot",
        "--yes",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"   ⚠️ 权限设置失败: {result.stderr or result.stdout}")
    else:
        print(f"   ✅ 文档权限已设置为组织内可读")


def _insert_image(doc_id: str, caption: str, path: str):
    if not path or not os.path.exists(path):
        print(f"   ⚠️ 跳过缺失的图表: {caption}")
        return
    try:
        rel_path = os.path.relpath(path, os.getcwd())
        subprocess.run(
            [
                "lark-cli", "docs", "+media-insert",
                "--as", "bot",
                "--doc", doc_id,
                "--file", rel_path,
                "--caption", caption,
                "--align", "center",
            ],
            capture_output=True, text=True, check=True,
        )
        print(f"   ✅ 已插入: {caption}")
    except subprocess.CalledProcessError as e:
        print(f"   ❌ 插入失败 {caption}: {e.stderr or e.stdout}")


def main():
    print("=" * 50)
    print("周报自动生成（XML 版本 — 线索数口径）")
    print("=" * 50)

    if APP_ID == "cli_xxxxxxxxxxxxxxxx" or not APP_SECRET or len(APP_SECRET) < 10:
        print("\n❌ 错误：请先配置 config_local.py，填入真实的 APP_ID 和 APP_SECRET")
        sys.exit(1)

    client = FeishuClient(APP_ID, APP_SECRET)

    # Bitable-first：优先从多维表格读取，失败 fallback Excel
    records = []
    if BITABLE_APP_TOKEN and BITABLE_TABLE_ID:
        print("\n📡 Bitable-first：从多维表格读取最近45天数据 ...")
        try:
            records = fetch_recent_data(client, BITABLE_APP_TOKEN, BITABLE_TABLE_ID, days=45)
            if records:
                print(f"✅ Bitable 读取成功：{len(records)} 条")
            else:
                print("   ⚠️ Bitable 返回空数据")
        except Exception as e:
            print(f"   ⚠️ Bitable 读取失败: {e}")
    else:
        print("   ℹ️ 未配置 Bitable，跳过")

    if not records:
        print("\n📡 Fallback 到 Excel ...")
        records = fetch_from_excel(days=45)
        print(f"✅ Excel 读取到 {len(records)} 条记录")

    if not records:
        print("❌ 错误：Bitable 和 Excel 均未读取到数据")
        sys.exit(1)

    # 检查数据完整性
    has_clue = sum(1 for r in records if r["clue_count"] > 0)
    has_revenue = sum(1 for r in records if r["revenue"] > 0)
    has_strategy = sum(1 for r in records if r["strategy"] in ("是", "否"))
    print(f"   有效线索记录: {has_clue} 条")
    print(f"   有首单流水数据: {has_revenue} 条")
    print(f"   有策略标记数据: {has_strategy} 条")

    # 计算并显示 LTV
    ltv = _calc_ltv(records)
    print(f"   动态 LTV（上月）: ¥{ltv}")
    if has_revenue == 0:
        print("   ⚠️ 警告：首单流水字段为空，LTV 使用默认值 ¥95")

    print("\n📊 加载深度归因分析数据 ...")
    deep_data = load_deep_dive_data()
    if deep_data:
        print("✅ 已加载 dashboard_data.json")
    else:
        print("⚠️ 未找到 dashboard_data.json，周报将只包含基础数据")

    print("\n📝 生成周报 XML ...")
    xml_parts = generate_weekly_report_xml(records, deep_data)

    print("\n📈 生成可视化图表 ...")
    chart_images = generate_report_charts(records, deep_data)
    print(f"✅ 生成 {len(chart_images)} 张图表")
    chart_map = {caption: path for caption, path in chart_images}

    if not WEEKLY_DOC_ID:
        print("\n📦 WEEKLY_DOC_ID 未配置，创建新文档 ...")
        doc_id = client.create_doc("直播间线索周报")
        print(f"✅ 已创建新文档，document_id: {doc_id}")
        print(f"   请把 {doc_id} 填入 config_local.py 的 WEEKLY_DOC_ID")
    else:
        doc_id = WEEKLY_DOC_ID

    print("\n📝 写入飞书文档 ...")

    # 1. overwrite 写入标题 + 头部 + 第一部分（总体指标）
    header_content = xml_parts[0][1] + xml_parts[1][1]
    _lark_update(doc_id, "overwrite", header_content)
    print("   ✅ 标题 + 一、总体指标")

    # 2. append 第二部分（目标进度-总）+ 插入目标仪表盘
    _lark_update(doc_id, "append", xml_parts[2][1])
    print("   ✅ 二、目标进度-总")
    gauge_path = chart_map.get("目标达成仪表盘")
    if gauge_path:
        print("\n📎 插入图表: 目标达成仪表盘")
        _insert_image(doc_id, "目标达成仪表盘", gauge_path)

    # 3. append 第三部分（构成拆分）+ 插入策略构成饼图
    _lark_update(doc_id, "append", xml_parts[3][1])
    print("   ✅ 三、构成拆分")
    strategy_path = chart_map.get("策略构成对比（4月 vs 5月）")
    if strategy_path:
        print("\n📎 插入图表: 策略构成对比")
        _insert_image(doc_id, "策略构成对比（4月 vs 5月）", strategy_path)

    # 4. append 第四部分（目标差距分析 归因123）+ 插入归因图表
    _lark_update(doc_id, "append", xml_parts[4][1])
    print("   ✅ 四、目标差距分析 归因123")

    holiday_path = chart_map.get("假期冲击对比")
    if holiday_path:
        print("\n📎 插入图表: 假期冲击对比")
        _insert_image(doc_id, "假期冲击对比", holiday_path)

    crashed_path = chart_map.get("暴跌品类对比（4月 vs 5月）")
    if crashed_path:
        print("\n📎 插入图表: 暴跌品类对比")
        _insert_image(doc_id, "暴跌品类对比（4月 vs 5月）", crashed_path)

    member_path = chart_map.get("会员等级结构变化")
    if member_path:
        print("\n📎 插入图表: 会员等级结构变化")
        _insert_image(doc_id, "会员等级结构变化", member_path)

    cat_change_path = chart_map.get("同期品类变化 TOP10")
    if cat_change_path:
        print("\n📎 插入图表: 同期品类变化 TOP10")
        _insert_image(doc_id, "同期品类变化 TOP10", cat_change_path)

    # 5. append 第五部分（品类后链路分析）
    _lark_update(doc_id, "append", xml_parts[5][1])
    print("   ✅ 五、品类后链路分析")

    # 6. append 第六部分（下一步迭代策略）
    _lark_update(doc_id, "append", xml_parts[6][1])
    print("   ✅ 六、下一步迭代策略")

    # 保存本地备份
    local_path = f"weekly_report_{datetime.now().strftime('%Y%m%d')}.xml"
    full_xml = "\n".join([p[1] for p in xml_parts])
    with open(local_path, "w", encoding="utf-8") as f:
        f.write(full_xml)
    print(f"✅ 本地备份: {local_path}")

    # 自动设置文档权限（组织内可读）
    print("\n🔓 设置文档权限 ...")
    try:
        from config_local import WEEKLY_DOC_TYPE
    except ImportError:
        WEEKLY_DOC_TYPE = "docx"
    _set_doc_permission(doc_id, WEEKLY_DOC_TYPE)

    if chart_images:
        print(f"✅ 图表保存位置:")
        for caption, path in chart_images:
            print(f"   {caption}: {path}")

    print("\n" + "=" * 50)
    print("🎉 周报生成完成！")
    print("=" * 50)


if __name__ == "__main__":
    main()

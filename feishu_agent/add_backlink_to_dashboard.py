"""
在看板 dashboard.html 中插入后链路分析板块
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pandas as pd
from pathlib import Path
from datetime import datetime

base_dir = Path(__file__).parent.parent
backlink_file = base_dir / "私域导流后链路补充.xlsx"
cat_file = base_dir / "【重要】品类归属.xlsx"
dashboard_file = base_dir / "dashboard.html"

if not backlink_file.exists() or not cat_file.exists():
    print("后链路数据文件不存在，跳过")
    sys.exit(0)

# 读取品类归属
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

# 读取后链路数据
df_daily = pd.read_excel(backlink_file, sheet_name="私域导量进度")
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
agg["类型"] = agg["品类名"].apply(get_type)

# 正式品漏斗趋势
funnel_rows = []
for m in ["2026-03", "2026-04", "2026-05"]:
    sub = agg[(agg["统计月"] == m) & (agg["类型"] == "正式品")]
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

funnel_html = ""
if funnel_rows:
    rows = ""
    for r in funnel_rows:
        rows += f"""
            <tr class="border-b border-outline-variant">
                <td class="py-2 px-3 text-body-standard font-body-standard">{r['月份']}</td>
                <td class="py-2 px-3 text-body-standard font-body-standard text-right">{r['好友率']}</td>
                <td class="py-2 px-3 text-body-standard font-body-standard text-right">{r['进群率']}</td>
                <td class="py-2 px-3 text-body-standard font-body-standard text-right">{r['先导课到课率']}</td>
                <td class="py-2 px-3 text-body-standard font-body-standard text-right">{r['首课到课率']}</td>
                <td class="py-2 px-3 text-body-standard font-body-standard text-right">{r['首课完课率']}</td>
                <td class="py-2 px-3 text-body-standard font-body-standard text-right font-bold">{r['综合转化率']}</td>
            </tr>"""
    funnel_html = f"""
    <div class="overflow-x-auto">
        <table class="w-full text-left">
            <thead>
                <tr class="border-b-2 border-outline-variant">
                    <th class="py-2 px-3 text-subtext font-subtext">月份</th>
                    <th class="py-2 px-3 text-subtext font-subtext text-right">好友率</th>
                    <th class="py-2 px-3 text-subtext font-subtext text-right">进群率</th>
                    <th class="py-2 px-3 text-subtext font-subtext text-right">先导课到课率</th>
                    <th class="py-2 px-3 text-subtext font-subtext text-right">首课到课率</th>
                    <th class="py-2 px-3 text-subtext font-subtext text-right">首课完课率</th>
                    <th class="py-2 px-3 text-subtext font-subtext text-right">综合转化率</th>
                </tr>
            </thead>
            <tbody>{rows}
            </tbody>
        </table>
    </div>"""

# 品类后链路环比表（过程指标口径）
proc_cols = ["好友率", "进群率", "先导课到课率", "首课到课率", "首课完课率", "综合转化率"]
results = []
for cat in sorted(agg["品类名"].unique()):
    apr = agg[(agg["品类名"] == cat) & (agg["统计月"] == "2026-04")]
    may = agg[(agg["品类名"] == cat) & (agg["统计月"] == "2026-05")]
    if len(apr) == 0 or len(may) == 0:
        continue
    apr = apr.iloc[0]
    may = may.iloc[0]
    row = {
        "品类": cat,
        "类型": get_type(cat),
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
    body = ""
    for _, r in rows.iterrows():
        def _color(v):
            if v < -10: return "text-error"
            if v < 0: return "text-tertiary"
            return "text-secondary"
        body += f"""
            <tr class="border-b border-outline-variant">
                <td class="py-2 px-3 text-body-standard font-body-standard">{r['品类']}</td>
                <td class="py-2 px-3 text-body-standard font-body-standard text-right">{r['4月线索']}</td>
                <td class="py-2 px-3 text-body-standard font-body-standard text-right">{r['5月线索']}</td>
                <td class="py-2 px-3 text-body-standard font-body-standard text-right {_color(r['好友率环比'])}">{r['好友率环比']:+.1f}%</td>
                <td class="py-2 px-3 text-body-standard font-body-standard text-right {_color(r['进群率环比'])}">{r['进群率环比']:+.1f}%</td>
                <td class="py-2 px-3 text-body-standard font-body-standard text-right {_color(r['先导课到课率环比'])}">{r['先导课到课率环比']:+.1f}%</td>
                <td class="py-2 px-3 text-body-standard font-body-standard text-right {_color(r['首课完课率环比'])}">{r['首课完课率环比']:+.1f}%</td>
                <td class="py-2 px-3 text-body-standard font-body-standard text-right {_color(r['综合转化率环比'])}">{r['综合转化率环比']:+.1f}%</td>
            </tr>"""
    return f"""
    <h3 class="text-module-title font-module-title text-on-surface mb-3">{title}</h3>
    <div class="overflow-x-auto">
        <table class="w-full text-left">
            <thead>
                <tr class="border-b-2 border-outline-variant">
                    <th class="py-2 px-3 text-subtext font-subtext">品类</th>
                    <th class="py-2 px-3 text-subtext font-subtext text-right">4月线索</th>
                    <th class="py-2 px-3 text-subtext font-subtext text-right">5月线索</th>
                    <th class="py-2 px-3 text-subtext font-subtext text-right">好友率环比</th>
                    <th class="py-2 px-3 text-subtext font-subtext text-right">进群率环比</th>
                    <th class="py-2 px-3 text-subtext font-subtext text-right">到课率环比</th>
                    <th class="py-2 px-3 text-subtext font-subtext text-right">完课率环比</th>
                    <th class="py-2 px-3 text-subtext font-subtext text-right">转化率环比</th>
                </tr>
            </thead>
            <tbody>{body}
            </tbody>
        </table>
    </div>"""

formal_html = _build_table(result_df[result_df["类型"] == "正式品"], "正式品后链路（5月 vs 4月）")
incub_html = _build_table(result_df[result_df["类型"] == "孵化品"], "孵化品后链路（5月 vs 4月）")

# 关键发现
key_findings = ""
if len(funnel_rows) >= 3:
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
            key_findings = f"5月正式品<strong class='text-primary'>{drops[0][0]}</strong>较4月下降 {drops[0][1]:.1f}pp，是漏斗中恶化最严重的环节。"
        else:
            key_findings = "5月正式品各过程指标与4月相比整体稳定。"
    else:
        key_findings = "5月正式品综合转化率较4月下降，需关注进群后运营与课程交付环节。"
else:
    key_findings = "数据不足，无法生成漏斗分析。"

backlink_section = f"""
    <!-- ========== 品类后链路分析 ========== -->
    <section class="glass-card rounded-xl p-card-padding">
        <div class="flex items-center gap-2 mb-4">
            <span class="material-symbols-outlined text-primary">trending_down</span>
            <h2 class="text-title-main font-title-main text-on-surface">品类后链路分析</h2>
        </div>
        <p class="text-body-standard font-body-standard text-on-surface mb-4">
            <span class="bg-primary-container/30 px-2 py-1 rounded text-primary font-bold">关键发现：</span> {key_findings} 首单流水因结算周期尚未完全体现，当前重点监控过程指标。
        </p>
        <h3 class="text-module-title font-module-title text-on-surface mb-3">正式品漏斗趋势</h3>
        {funnel_html}
        <div class="mt-6">{formal_html}</div>
        <div class="mt-6">{incub_html}</div>
    </section>
"""

# 插入到 dashboard.html 的 </main> 之前
with open(dashboard_file, 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace('</main>', backlink_section + '\n</main>')

with open(dashboard_file, 'w', encoding='utf-8') as f:
    f.write(content)

print(f"✅ 后链路分析板块已插入 dashboard.html")
print(f"   正式品漏斗: {len(funnel_rows)} 个月")
print(f"   正式品品类: {len(result_df[result_df['类型'] == '正式品'])} 个")
print(f"   孵化品品类: {len(result_df[result_df['类型'] == '孵化品'])} 个")

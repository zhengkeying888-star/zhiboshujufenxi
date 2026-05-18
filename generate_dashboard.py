import json
import os
from datetime import datetime

with open('dashboard_data.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# 自动读取当前月份和日期
now = datetime.now()
current_month = now.month
current_month_cn = f"{current_month}月"
last_month_cn = f"{current_month - 1}月" if current_month > 1 else "12月"
report_date = now.strftime('%Y-%m-%d')
today_day = now.day

# 计算环比
def pct_change(new, old):
    if old == 0:
        return '+∞' if new > 0 else '0'
    v = round((new - old) / old * 100, 1)
    return f"{v:+.1f}"

ts = data.get('total_stats', {})
cart_3 = ts.get('3月', {}).get('购物车', 0)
cart_4 = ts.get('4月', {}).get('购物车', 0)
cart_5 = ts.get('5月', {}).get('购物车', 0)
cart_change_4 = pct_change(cart_4, cart_3)
cart_change_5 = pct_change(cart_5, cart_4)

dm_3 = ts.get('3月', {}).get('弹幕', 0)
dm_4 = ts.get('4月', {}).get('弹幕', 0)
dm_5 = ts.get('5月', {}).get('弹幕', 0)
dm_change_4 = pct_change(dm_4, dm_3)
dm_change_5 = pct_change(dm_5, dm_4)

# 5月二级团队占比（1-15号同期）
team_5 = data['team_compare']['5月']
health_5v = team_5.get('健康线', 0)
interest_5v = team_5.get('兴趣变美线', 0)
team_total = health_5v + interest_5v
health_pct = round(health_5v / team_total * 100, 1) if team_total else 0
interest_pct = round(interest_5v / team_total * 100, 1) if team_total else 0

# 品类数据
cat_data = data['cat_data']
health_cats = [c for c in cat_data if c.get('二级团队') == '健康线']
interest_cats = [c for c in cat_data if c.get('二级团队') == '兴趣变美线']

# 目标追踪
tt = data.get('target_tracking', {})
target = tt.get('购物车线索目标', 11728)
achievement = tt.get('达成率', 0)
gap = tt.get('缺口', 0)
daily_avg = tt.get('日均', 0)
projected = tt.get('月底预测', 0)
projected_pct = tt.get('预测达成率', 0)
projected_gmv = tt.get('预估流水', 0)
ltv_forecast = tt.get('预测LTV', 76.74)

# 核心归因
ca = data.get('core_answer', {})
total_loss = ca.get('total_loss', 0)
disappeared_pct = ca.get('disappeared_pct', 0)
crashed_pct = ca.get('crashed_pct', 0)
uniform_drop = ca.get('uniform_drop', True)
crashed_cats_detail = ca.get('crashed_cats_detail', [])

# 从 cat_data 中提取所有暴跌品类（确保包含全部暴跌品类）
all_crashed_cats = [c for c in cat_data if c.get('状态') == '暴跌']
if not all_crashed_cats:
    all_crashed_cats = crashed_cats_detail

# 暴跌品类卡片 HTML（预生成，避免 f-string 反斜杠问题）
crashed_cards_html = ''
for c in all_crashed_cats:
    c4 = c.get('4月(1-15)', c.get('4月', 0))
    c5 = c.get('5月(1-15)', c.get('5月', 0))
    change = c.get('环比', 0)
    crashed_cards_html += f'<div class="bg-white/60 rounded p-2"><div class="text-subtext font-subtext text-outline">{c["品类"]}</div><div class="text-body-standard font-body-standard font-bold text-error">{c4}→{c5}条 ({change}%)</div></div>'


# 渠道趋势
ch = data.get('channel_trends', {})
cart_ch = ch.get('cart_change', 0)
dm_ch = ch.get('dm_change', 0)
same_trend = ch.get('same_trend', True)
channel_conclusion = ch.get('conclusion', '')

# 假期效应
he = data.get('holiday_effect', {})
holiday_drop = he.get('holiday_drop', 0)
normal_drop = he.get('normal_drop', 0)
holiday_main = he.get('holiday_is_main_factor', False)
he_counts = he.get('counts', {})
apr_holiday_avg = int(round(he_counts.get('4月假期(1-5)', 0) / 5, 0)) if he_counts.get('4月假期(1-5)', 0) else 0
apr_normal_avg = int(round(he_counts.get('4月平日(6-15)', 0) / 10, 0)) if he_counts.get('4月平日(6-15)', 0) else 0
curr_holiday_avg = int(round(he_counts.get('5月假期(1-5)', 0) / 5, 0)) if he_counts.get('5月假期(1-5)', 0) else 0
curr_normal_avg = int(round(he_counts.get('5月平日(6-15)', 0) / 10, 0)) if he_counts.get('5月平日(6-15)', 0) else 0

# 帕累托
pareto = data.get('pareto', {})
pareto_4 = pareto.get('4月', {}).get('集中度', 0)
pareto_5 = pareto.get('5月', {}).get('集中度', 0)

# 高价值品类
high_value = data.get('high_value_cats', [])

# 排期关联
schedule_corr = data.get('schedule_correlation', {})
not_scheduled = schedule_corr.get('not_scheduled', [])
low_conversion = schedule_corr.get('low_conversion', [])

# 会员等级
member_levels = data.get('member_levels', {})
ml_prev = member_levels.get('4月', {}).get('pct', {})
ml_curr = member_levels.get('5月', {}).get('pct', {})
high_value_prev = ml_prev.get('V7-V10 高价值', 0)
high_value_curr = ml_curr.get('V7-V10 高价值', 0)
new_user_prev = ml_prev.get('V0-V1 新用户', 0)
new_user_curr = ml_curr.get('V0-V1 新用户', 0)

# 健康线分析
team_health = data.get('team_health_analysis', {})

# 会员等级×品类交叉
member_cat_cross = data.get('member_category_cross', {})
high_value_top = member_cat_cross.get('high_value_top', [])

# 新量策略数据
cart_stats_by_strategy = data.get('cart_stats_by_strategy', {})
cat_data_by_strategy = data.get('cat_data_by_strategy', [])

# ===== 动态权重计算（按线索缺口绝对值排序）=====
# 假期影响分
prev_holiday_cnt = he_counts.get(f'4月假期(1-5)', 0)
curr_holiday_cnt = he_counts.get(f'5月假期(1-5)', 0)
holiday_impact_score = abs(prev_holiday_cnt - curr_holiday_cnt)

# 品类塌方影响分（TOP3暴跌品类缺口）
crashed_loss_top3 = sum(c.get('4月', 0) - c.get('5月', 0) for c in crashed_cats_detail[:3]) if crashed_cats_detail else 0
category_impact_score = crashed_loss_top3

# 用户结构影响分（高价值用户占比变化 × 当前线索数 / 100）
user_impact_score = abs(high_value_curr - high_value_prev) * cart_5 / 100 if high_value_prev else 0

# 渠道影响分（购物车环比变化的绝对值 × 4月基数 / 100）
try:
    cart_ch_float = float(cart_ch)
except (ValueError, TypeError):
    cart_ch_float = 0
channel_impact_score = abs(cart_ch_float) * cart_4 / 100

attribution_scores = [
    ("品类塌方", category_impact_score, category_impact_score > 50),
    ("假期冲击", holiday_impact_score, holiday_impact_score > 50),
    ("用户结构", user_impact_score, user_impact_score > 30),
    ("渠道趋势", channel_impact_score, channel_impact_score > 30),
]
attribution_scores.sort(key=lambda x: x[1], reverse=True)
primary_cause = attribution_scores[0][0] if attribution_scores else "待分析"

# ===== TOP5问题品类（按线索缺口绝对值排序）=====
all_crashed_sorted = sorted(all_crashed_cats, key=lambda c: c.get('4月(1-15)', c.get('4月', 0)) - c.get('5月(1-15)', c.get('5月', 0)), reverse=True)
top5_problem_cats = all_crashed_sorted[:5]

top5_problem_html = ''
for c in top5_problem_cats:
    c4 = c.get('4月(1-15)', c.get('4月', 0))
    c5 = c.get('5月(1-15)', c.get('5月', 0))
    change = c.get('环比', 0)
    ltv = c.get('4月LTV', 0)
    team = c.get('二级团队', '')
    team_color = 'text-primary' if team == '健康线' else 'text-secondary'
    top5_problem_html += f'''
    <div class="flex items-center justify-between p-3 bg-error-container/20 rounded-lg border-l-4 border-error">
        <div class="flex items-center gap-3">
            <span class="text-body-standard font-body-standard font-bold text-on-surface">{c['品类']}</span>
            <span class="text-subtext font-subtext {team_color}">{team}</span>
            <span class="text-subtext font-subtext text-outline">LTV¥{ltv}</span>
        </div>
        <div class="text-right">
            <div class="text-body-standard font-body-standard font-bold text-error">{c4:,} → {c5:,} 条 ({change}%)</div>
            <div class="text-subtext font-subtext text-outline">缺口 {c4-c5:,} 条</div>
        </div>
    </div>'''

# ===== 策略构成数据（用于核心归因结论）=====
apr_y = cart_stats_by_strategy.get('4月', {}).get('是', 0)
apr_n = cart_stats_by_strategy.get('4月', {}).get('否', 0)
may_y = cart_stats_by_strategy.get('5月', {}).get('是', 0)
may_n = cart_stats_by_strategy.get('5月', {}).get('否', 0)
apr_y_pct = cart_stats_by_strategy.get('4月', {}).get('是占比', 0)
may_y_pct = cart_stats_by_strategy.get('5月', {}).get('是占比', 0)
strategy_change = f"新量策略 {apr_y:,}条→{may_y:,}条，非新量 {apr_n:,}条→{may_n:,}条，新量占比 {apr_y_pct}%→{may_y_pct}%"

# 状态标签映射
status_config = {
    '消失': {'label': '消失', 'color': 'bg-[#1e293b] text-white', 'border': 'border-l-4 border-[#1e293b]'},
    '暴跌': {'label': '暴跌', 'color': 'bg-error-container text-error', 'border': 'border-l-4 border-error'},
    '下滑': {'label': '下滑', 'color': 'bg-[#fff7ed] text-[#f97316]', 'border': 'border-l-4 border-[#f97316]'},
    '扛住': {'label': '扛住', 'color': 'bg-secondary-container text-on-secondary-container', 'border': 'border-l-4 border-secondary'},
    '新增': {'label': '新增', 'color': 'bg-primary-fixed text-on-primary-fixed', 'border': 'border-l-4 border-primary'},
    '无数据': {'label': '无数据', 'color': 'bg-surface-container text-on-surface-variant', 'border': 'border-l-4 border-outline-variant'},
}

def render_cat_card(c):
    cfg = status_config.get(c.get('状态', '无数据'), status_config['无数据'])
    c3 = c.get('3月(1-15)', c.get('3月', 0))
    c4 = c.get('4月(1-15)', c.get('4月', 0))
    c5 = c.get('5月(1-15)', c.get('5月', 0))
    ltv = c.get('4月LTV', 0)
    team = c.get('二级团队', '')
    team_tag = ''
    if team == '健康线':
        team_tag = '<span class="px-1.5 py-0.5 rounded text-label-pill font-label-pill bg-primary-fixed text-on-primary-fixed ml-2">健康线</span>'
    elif team == '兴趣变美线':
        team_tag = '<span class="px-1.5 py-0.5 rounded text-label-pill font-label-pill bg-secondary-container text-on-secondary-container ml-2">变美线</span>'

    if c.get('状态') == '消失':
        c5_color = 'bg-surface-dim text-inverse-surface'
        c5_num_color = 'text-inverse-surface font-bold'
    elif c.get('状态') in ['暴跌', '下滑']:
        c5_color = 'bg-error-container text-error'
        c5_num_color = 'text-error font-bold'
    elif c.get('状态') == '扛住':
        c5_color = 'bg-secondary-container text-on-secondary-container'
        c5_num_color = 'text-on-secondary-container font-bold'
    else:
        c5_color = 'bg-primary-fixed text-on-primary-fixed'
        c5_num_color = 'text-on-primary-fixed font-bold'

    return f'''
    <div class="bg-surface-container-lowest border border-outline-variant rounded-lg p-4 hover:bg-surface transition-colors cursor-default {cfg['border']}">
        <div class="flex justify-between items-start mb-2">
            <div class="flex items-center">
                <h4 class="text-body-standard font-body-standard font-bold text-on-surface">{c['品类']}</h4>
                {team_tag}
            </div>
            <span class="px-2 py-1 rounded text-label-pill font-label-pill flex items-center gap-1 {cfg['color']}">
                {cfg['label']}
            </span>
        </div>
        <div class="text-subtext font-subtext text-outline mb-2">4月LTV ¥{ltv}</div>
        <div class="grid grid-cols-2 gap-2 text-center">
            <div class="bg-surface-container-low p-2 rounded">
                <div class="text-subtext font-subtext text-outline">4月</div>
                <div class="text-body-standard font-body-standard">{c4:,}</div>
            </div>
            <div class="{c5_color} p-2 rounded">
                <div class="text-subtext font-subtext">5月</div>
                <div class="text-body-standard font-body-standard {c5_num_color}">{c5:,}</div>
            </div>
        </div>
    </div>
    '''

health_cards = '\n'.join(render_cat_card(c) for c in health_cats[:15])
interest_cards = '\n'.join(render_cat_card(c) for c in interest_cats[:15])

# 关键发现
findings_html = ''
for f in data.get('findings', []):
    if f.get('severity') == 'high':
        border_color = 'border-error'
        icon_color = 'text-error'
        icon = 'warning'
    elif f.get('severity') == 'medium':
        border_color = 'border-[#f97316]'
        icon_color = 'text-[#f97316]'
        icon = 'error'
    else:
        border_color = 'border-secondary'
        icon_color = 'text-secondary'
        icon = 'check_circle'
    findings_html += f'''
    <li class="flex gap-3 items-start p-3 bg-surface-container-low rounded-lg border-l-4 {border_color}">
        <span class="material-symbols-outlined {icon_color} mt-0.5" data-icon="{icon}">{icon}</span>
        <span class="text-body-standard font-body-standard text-on-surface">{f['text']}</span>
    </li>
    '''

# 高价值品类表格
high_value_html = ''
for i, c in enumerate(high_value[:10]):
    status_badge = ''
    if c.get('状态') == '消失':
        status_badge = '<span class="px-2 py-0.5 rounded bg-[#1e293b] text-white text-label-pill">消失</span>'
    elif c.get('状态') == '暴跌':
        status_badge = '<span class="px-2 py-0.5 rounded bg-error-container text-error text-label-pill">暴跌</span>'
    elif c.get('状态') == '扛住':
        status_badge = '<span class="px-2 py-0.5 rounded bg-secondary-container text-on-secondary-container text-label-pill">扛住</span>'

    high_value_html += f'''
    <tr class="border-b border-outline-variant">
        <td class="py-2 px-3 text-body-standard font-body-standard">{c['品类']}</td>
        <td class="py-2 px-3 text-body-standard font-body-standard text-right">{c.get('4月(1-15)', 0):,}</td>
        <td class="py-2 px-3 text-body-standard font-body-standard text-right">¥{c.get('4月LTV', 0)}</td>
        <td class="py-2 px-3 text-body-standard font-body-standard">{status_badge}</td>
        <td class="py-2 px-3 text-body-standard font-body-standard text-right">{c.get('5月(1-15)', 0):,}</td>
    </tr>
    '''

# 未排期品类
not_scheduled_html = ''
for c in not_scheduled[:8]:
    not_scheduled_html += f'''
    <div class="flex items-center justify-between p-2 bg-error-container/30 rounded">
        <span class="text-body-standard font-body-standard font-bold">{c['品类']}</span>
        <span class="text-subtext font-subtext">4月{c['4月线索']}条 → 5月未排期</span>
    </div>
    '''

# 新量策略品类细分表格
strategy_cat_html = ''
for c in cat_data_by_strategy[:40]:
    if c['4月'] == 0 and c['5月'] == 0:
        continue
    status_badge = ''
    if c.get('状态') == '消失':
        status_badge = '<span class="px-2 py-0.5 rounded bg-[#1e293b] text-white text-label-pill">消失</span>'
    elif c.get('状态') == '暴跌':
        status_badge = '<span class="px-2 py-0.5 rounded bg-error-container text-error text-label-pill">暴跌</span>'
    elif c.get('状态') == '下滑':
        status_badge = '<span class="px-2 py-0.5 rounded bg-[#fff7ed] text-[#f97316] text-label-pill">下滑</span>'
    elif c.get('状态') == '扛住':
        status_badge = '<span class="px-2 py-0.5 rounded bg-secondary-container text-on-secondary-container text-label-pill">扛住</span>'
    elif c.get('状态') == '新增':
        status_badge = '<span class="px-2 py-0.5 rounded bg-primary-fixed text-on-primary-fixed text-label-pill">新增</span>'
    else:
        status_badge = '<span class="px-2 py-0.5 rounded bg-surface-container text-on-surface-variant text-label-pill">无数据</span>'

    change_color = 'text-error' if c.get('环比', 0) < 0 else ('text-secondary' if c.get('环比', 0) > 0 else 'text-on-surface')
    strategy_cat_html += f'''
    <tr class="border-b border-outline-variant">
        <td class="py-2 px-3 text-body-standard font-body-standard font-bold">{c['品类']}</td>
        <td class="py-2 px-3 text-body-standard font-body-standard">{'新量-是' if c['策略'] == '是' else '非新量-否'}</td>
        <td class="py-2 px-3 text-body-standard font-body-standard text-right">{c['4月']:,}</td>
        <td class="py-2 px-3 text-body-standard font-body-standard text-right">{c['5月']:,}</td>
        <td class="py-2 px-3 text-body-standard font-body-standard text-right {change_color} font-bold">{c['环比']}%</td>
        <td class="py-2 px-3 text-body-standard font-body-standard">{status_badge}</td>
    </tr>
    '''

# 排期关联表格
schedule_html = ''
for c in schedule_corr.get('cat_schedule', [])[:15]:
    schedule_html += f'''
    <tr class="border-b border-outline-variant">
        <td class="py-2 px-3 text-body-standard font-body-standard">{c['品类']}</td>
        <td class="py-2 px-3 text-body-standard font-body-standard text-right">{c['4月线索']:,}</td>
        <td class="py-2 px-3 text-body-standard font-body-standard text-right">{c['5月线索']:,}</td>
        <td class="py-2 px-3 text-body-standard font-body-standard text-center">{'是' if c['5月排期'] else '否'}</td>
        <td class="py-2 px-3 text-body-standard font-body-standard text-right">{c['5月曝光']:,}</td>
        <td class="py-2 px-3 text-body-standard font-body-standard text-right">{c['转化率']}</td>
        <td class="py-2 px-3 text-body-standard font-body-standard">{c['状态']}</td>
    </tr>
    '''

# 线索/万曝光分析（仅取有曝光数据的品类，按转化率排序）
exposure_cats = [c for c in schedule_corr.get('cat_schedule', []) if c.get('5月曝光', 0) > 0]
exposure_cats.sort(key=lambda x: x.get('转化率', 0), reverse=True)

exposure_html = ''
for c in exposure_cats[:12]:
    conversion = c.get('转化率', 0)
    bar_width = min(conversion * 10, 100)
    if conversion >= 3:
        color_class = 'bg-secondary'
    elif conversion >= 1.5:
        color_class = 'bg-primary'
    elif conversion > 0:
        color_class = 'bg-[#f97316]'
    else:
        color_class = 'bg-error'
    exposure_html += f'''
    <tr class="border-b border-outline-variant">
        <td class="py-2 px-3 text-body-standard font-body-standard">{c['品类']}</td>
        <td class="py-2 px-3 text-body-standard font-body-standard text-right">{c['5月线索']:,}</td>
        <td class="py-2 px-3 text-body-standard font-body-standard text-right">{c['5月曝光']:,}</td>
        <td class="py-2 px-3 text-body-standard font-body-standard text-right font-bold">{conversion}</td>
        <td class="py-2 px-3 text-body-standard font-body-standard">
            <div class="w-full bg-surface-container-high rounded-full h-2">
                <div class="{color_class} h-2 rounded-full" style="width: {bar_width}%"></div>
            </div>
        </td>
    </tr>
    '''

# 暴跌品类归因表格（用于周报和看板）
crashed_table_html = ''
for c in all_crashed_cats:
    c4 = c.get('4月(1-15)', c.get('4月', 0))
    c5 = c.get('5月(1-15)', c.get('5月', 0))
    change = c.get('环比', 0)
    ltv = c.get('4月LTV', 0)
    team = c.get('二级团队', '')
    # 尝试匹配暴跌原因
    reason = '待分析'
    for drop_cat in schedule_corr.get('cat_schedule', []):
        if drop_cat['品类'] == c['品类']:
            reason = drop_cat.get('暴跌原因', '待分析')
            break
    crashed_table_html += f'''
    <tr class="border-b border-outline-variant">
        <td class="py-2 px-3 text-body-standard font-body-standard font-bold">{c['品类']}</td>
        <td class="py-2 px-3 text-body-standard font-body-standard">{team}</td>
        <td class="py-2 px-3 text-body-standard font-body-standard text-right">{c4:,}</td>
        <td class="py-2 px-3 text-body-standard font-body-standard text-right">{c5:,}</td>
        <td class="py-2 px-3 text-body-standard font-body-standard text-right text-error font-bold">{change}%</td>
        <td class="py-2 px-3 text-body-standard font-body-standard text-right">¥{ltv}</td>
        <td class="py-2 px-3 text-body-standard font-body-standard">{reason}</td>
    </tr>
    '''

# ===== 辅助决策建议数据准备 =====
drop_reasons = schedule_corr.get('drop_reasons', {})
cat_schedule_all = schedule_corr.get('cat_schedule', [])

# 基于修正后的排期数据重新分类
ns_reason = []
sr_reason = []
conversion_issues = []

for c in cat_schedule_all:
    s4 = c['4月排期']
    s5 = c['5月排期']
    leads_drop = c['4月线索'] > c['5月线索']
    loss = c['4月线索'] - c['5月线索']

    if s4 > 0 and s5 == 0 and loss > 0:
        ns_reason.append(c)
    elif s4 > s5 > 0 and loss > 0:
        sr_reason.append(c)
    elif s4 > 0 and s5 > 0 and s4 <= s5 and loss > 0 and c['4月线索'] >= 10:
        conversion_issues.append(c)
    elif s4 > 0 and s5 > 0 and s4 > s5 and loss > 0 and c['4月线索'] >= 10:
        # 排期减少但线索也下降，可归为转化问题或场次减少
        # 如果排期减少比例<50%且线索下降明显，归为转化问题
        if s5 / s4 >= 0.5:
            conversion_issues.append(c)
        else:
            sr_reason.append(c)

# 按损失排序
conversion_issues.sort(key=lambda x: x['4月线索'] - x['5月线索'], reverse=True)
ns_reason.sort(key=lambda x: x['4月线索'] - x['5月线索'], reverse=True)
sr_reason.sort(key=lambda x: x['4月线索'] - x['5月线索'], reverse=True)

# 转化问题品类
conversion_loss = sum(c['4月线索'] - c['5月线索'] for c in conversion_issues)
conversion_s4 = sum(c['4月排期'] for c in conversion_issues)
conversion_s5 = sum(c['5月排期'] for c in conversion_issues)

# 未排期品类
ns_loss = sum(c['4月线索'] - c['5月线索'] for c in ns_reason)
ns_s4 = sum(c['4月排期'] for c in ns_reason)

# 场次减少品类
sr_loss = sum(c['4月线索'] - c['5月线索'] for c in sr_reason)
sr_s4 = sum(c['4月排期'] for c in sr_reason)
sr_s5 = sum(c['5月排期'] for c in sr_reason)

# 排期差异总统计
total_4_schedule = sum(c['4月排期'] for c in cat_schedule_all)
total_5_schedule = sum(c['5月排期'] for c in cat_schedule_all)
total_5_exposure = sum(c.get('5月曝光', 0) for c in cat_schedule_all)
schedule_change = total_5_schedule - total_4_schedule

# 辅助决策建议 HTML
decision_html = f'''<div class="grid grid-cols-1 md:grid-cols-3 gap-4">
    <!-- 转化问题 -->
    <div class="bg-error-container/30 border border-error/20 rounded-xl p-4">
        <div class="flex items-center gap-2 mb-3">
            <span class="material-symbols-outlined text-error">trending_down</span>
            <h3 class="text-module-title font-module-title text-error">转化问题（{len(conversion_issues)}个品类）</h3>
        </div>
        <div class="text-body-standard font-body-standard text-on-surface mb-2">
            排期未减但单场线索暴跌，损失 <strong class="text-error">{conversion_loss:,}</strong> 条
        </div>
        <div class="text-subtext font-subtext text-outline mb-3">
            4月排期 {conversion_s4} 场 → 5月排期 {conversion_s5} 场，线索/场次效率下降
        </div>
        <div class="bg-white/60 rounded p-3">
            <div class="text-subtext font-subtext text-outline mb-1">决策建议</div>
            <ul class="text-body-standard font-body-standard text-on-surface space-y-1 list-disc list-inside">
                <li>排查直播间引导话术、商品吸引力</li>
                <li>检查落地页转化链路是否异常</li>
                <li>对比4月/5月单场直播录像找差异</li>
            </ul>
        </div>
        <div class="mt-2 flex flex-wrap gap-1">
            {''.join(f'<span class="px-2 py-0.5 rounded bg-error-container text-error text-label-pill">{c["品类"]}</span>' for c in conversion_issues[:6])}
        </div>
    </div>
    <!-- 未排期 -->
    <div class="bg-[#fff7ed] border border-[#f97316]/20 rounded-xl p-4">
        <div class="flex items-center gap-2 mb-3">
            <span class="material-symbols-outlined text-[#f97316]">event_busy</span>
            <h3 class="text-module-title font-module-title text-[#f97316]">未排期（{len(ns_reason)}个品类）</h3>
        </div>
        <div class="text-body-standard font-body-standard text-on-surface mb-2">
            4月有排期但5月完全未排期，排期取消 <strong class="text-[#f97316]">{ns_s4} 场</strong>
        </div>
        <div class="text-subtext font-subtext text-outline mb-3">
            4月排期 {ns_s4} 场 → 5月排期 0 场，涉及 {len(ns_reason)} 个品类
        </div>
        <div class="bg-white/60 rounded p-3">
            <div class="text-subtext font-subtext text-outline mb-1">决策建议</div>
            <ul class="text-body-standard font-body-standard text-on-surface space-y-1 list-disc list-inside">
                <li>确认停播原因（品类调整/讲师问题/策略变化）</li>
                <li>高LTV品类优先推动复播</li>
                <li>制定复播优先级清单</li>
            </ul>
        </div>
        <div class="mt-2 flex flex-wrap gap-1">
            {''.join(f'<span class="px-2 py-0.5 rounded bg-[#fff7ed] text-[#f97316] text-label-pill">{c["品类"]}</span>' for c in ns_reason)}
        </div>
    </div>
    <!-- 场次减少 -->
    <div class="bg-primary-fixed/50 border border-primary/20 rounded-xl p-4">
        <div class="flex items-center gap-2 mb-3">
            <span class="material-symbols-outlined text-primary">event_repeat</span>
            <h3 class="text-module-title font-module-title text-primary">场次减少（{len(sr_reason)}个品类）</h3>
        </div>
        <div class="text-body-standard font-body-standard text-on-surface mb-2">
            排期场次减少 <strong class="text-primary">{sr_s4 - sr_s5} 场</strong>，但单场效率反而提升
        </div>
        <div class="text-subtext font-subtext text-outline mb-3">
            4月排期 {sr_s4} 场 → 5月排期 {sr_s5} 场，涉及 {len(sr_reason)} 个品类
        </div>
        <div class="bg-white/60 rounded p-3">
            <div class="text-subtext font-subtext text-outline mb-1">决策建议</div>
            <ul class="text-body-standard font-body-standard text-on-surface space-y-1 list-disc list-inside">
                <li>评估单场效率，若效率稳定则增加排期</li>
                <li>优先恢复高转化品类的场次</li>
                <li>检查是否因假期调休导致场次减少</li>
            </ul>
        </div>
        <div class="mt-2 flex flex-wrap gap-1">
            {''.join(f'<span class="px-2 py-0.5 rounded bg-primary-fixed text-primary text-label-pill">{c["品类"]}</span>' for c in sr_reason)}
        </div>
    </div>
</div>
<div class="mt-4 p-3 bg-secondary-container/30 rounded-lg border-l-4 border-secondary">
    <div class="flex items-start gap-2">
        <span class="material-symbols-outlined text-secondary">lightbulb</span>
        <div>
            <div class="text-body-standard font-body-standard font-bold text-on-surface mb-1">综合决策优先级</div>
            <div class="text-body-standard font-body-standard text-on-surface">
                <strong>P0（立即行动）：</strong>未排期的高LTV品类（{', '.join(c['品类'] + 'LTV¥' + str(c.get('4月LTV', 0)) for c in ns_reason[:2] if c.get('4月LTV', 0) > 0)}）推动复播，可快速回补线索缺口；
                <strong>P1（本周内）：</strong>转化问题品类排查话术/链路，场次减少品类评估加场；
                <strong>P2（持续监控）：</strong>低转化品类（≤1条/万曝光）优化商品和引导策略。
            </div>
        </div>
    </div>
</div>'''

# 排期差异分析 HTML
schedule_diff_html = f'''<div class="grid grid-cols-1 md:grid-cols-4 gap-4 mb-4">
    <div class="bg-surface-container-low rounded-lg p-3 text-center">
        <div class="text-subtext font-subtext text-outline">4月总排期场次</div>
        <div class="text-metric-display-mobile font-metric-display-mobile text-on-surface font-bold">{total_4_schedule}</div>
    </div>
    <div class="bg-surface-container-low rounded-lg p-3 text-center">
        <div class="text-subtext font-subtext text-outline">5月总排期场次</div>
        <div class="text-metric-display-mobile font-metric-display-mobile {'text-error' if schedule_change < 0 else 'text-secondary'} font-bold">{total_5_schedule}</div>
    </div>
    <div class="bg-surface-container-low rounded-lg p-3 text-center">
        <div class="text-subtext font-subtext text-outline">场次变化</div>
        <div class="text-metric-display-mobile font-metric-display-mobile {'text-error' if schedule_change < 0 else 'text-secondary'} font-bold">{schedule_change:+,}</div>
    </div>
    <div class="bg-surface-container-low rounded-lg p-3 text-center">
        <div class="text-subtext font-subtext text-outline">5月总曝光</div>
        <div class="text-metric-display-mobile font-metric-display-mobile text-on-surface font-bold">{total_5_exposure:,.0f}</div>
    </div>
</div>
<div class="overflow-x-auto">
    <table class="w-full text-left">
        <thead>
            <tr class="border-b-2 border-outline-variant">
                <th class="py-2 px-3 text-subtext font-subtext">暴跌原因</th>
                <th class="py-2 px-3 text-subtext font-subtext text-right">品类数</th>
                <th class="py-2 px-3 text-subtext font-subtext text-right">线索损失</th>
                <th class="py-2 px-3 text-subtext font-subtext text-right">4月排期</th>
                <th class="py-2 px-3 text-subtext font-subtext text-right">5月排期</th>
                <th class="py-2 px-3 text-subtext font-subtext text-right">排期变化</th>
                <th class="py-2 px-3 text-subtext font-subtext text-right">5月曝光</th>
            </tr>
        </thead>
        <tbody>
            <tr class="border-b border-outline-variant">
                <td class="py-2 px-3 text-body-standard font-body-standard font-bold text-error">转化问题（每场暴跌）</td>
                <td class="py-2 px-3 text-body-standard font-body-standard text-right">{len(conversion_issues)}</td>
                <td class="py-2 px-3 text-body-standard font-body-standard text-right text-error font-bold">{conversion_loss:,}</td>
                <td class="py-2 px-3 text-body-standard font-body-standard text-right">{conversion_s4}</td>
                <td class="py-2 px-3 text-body-standard font-body-standard text-right">{conversion_s5}</td>
                <td class="py-2 px-3 text-body-standard font-body-standard text-right">{conversion_s5 - conversion_s4:+,}</td>
                <td class="py-2 px-3 text-body-standard font-body-standard text-right">{sum(c.get('5月曝光', 0) for c in conversion_issues):,}</td>
            </tr>
            <tr class="border-b border-outline-variant">
                <td class="py-2 px-3 text-body-standard font-body-standard font-bold text-[#f97316]">排期问题（未排期）</td>
                <td class="py-2 px-3 text-body-standard font-body-standard text-right">{len(ns_reason)}</td>
                <td class="py-2 px-3 text-body-standard font-body-standard text-right text-[#f97316] font-bold">{ns_loss:,}</td>
                <td class="py-2 px-3 text-body-standard font-body-standard text-right">{ns_s4}</td>
                <td class="py-2 px-3 text-body-standard font-body-standard text-right">0</td>
                <td class="py-2 px-3 text-body-standard font-body-standard text-right text-error font-bold">-{ns_s4}</td>
                <td class="py-2 px-3 text-body-standard font-body-standard text-right">0</td>
            </tr>
            <tr class="border-b border-outline-variant">
                <td class="py-2 px-3 text-body-standard font-body-standard font-bold text-primary">排期问题（场次减少）</td>
                <td class="py-2 px-3 text-body-standard font-body-standard text-right">{len(sr_reason)}</td>
                <td class="py-2 px-3 text-body-standard font-body-standard text-right text-primary font-bold">{sr_loss:,}</td>
                <td class="py-2 px-3 text-body-standard font-body-standard text-right">{sr_s4}</td>
                <td class="py-2 px-3 text-body-standard font-body-standard text-right">{sr_s5}</td>
                <td class="py-2 px-3 text-body-standard font-body-standard text-right text-error font-bold">{sr_s5 - sr_s4:+,}</td>
                <td class="py-2 px-3 text-body-standard font-body-standard text-right">{sum(c.get('5月曝光', 0) for c in sr_reason):,}</td>
            </tr>
        </tbody>
    </table>
</div>
<div class="mt-3 p-3 bg-surface-container-low rounded">
    <p class="text-body-standard font-body-standard text-on-surface">
        <span class="font-bold">排期差异结论：</span>4月→5月排期总场次 <strong>{total_4_schedule} → {total_5_schedule}</strong>（{schedule_change:+,}场）。
        转化问题品类排期基本不变但效率暴跌，是线索下滑的<strong class="text-error">主因</strong>（损失{conversion_loss:,}条）；
        未排期品类完全停播，需优先推动复播；场次减少品类单场效率反而提升，可考虑加场恢复线索量。
    </p>
</div>'''

# 进度条颜色
def progress_color(pct):
    if pct >= 80:
        return 'bg-secondary'
    elif pct >= 50:
        return 'bg-primary'
    elif pct >= 30:
        return 'bg-[#f97316]'
    else:
        return 'bg-error'

prog_color = progress_color(achievement)
prog_width = min(achievement, 100)

# 瀑布图数据
wf_items = []
wf_items.append({'name': '4月总线索', 'value': cart_4, 'type': 'start'})
cat_changes = []
for c in cat_data:
    c4 = c.get('4月(1-15)', c.get('4月', 0))
    c5 = c.get('5月(1-15)', c.get('5月', 0))
    change = c5 - c4
    if change != 0:
        cat_changes.append({'name': c['品类'], 'change': change})
cat_changes.sort(key=lambda x: abs(x['change']), reverse=True)
top_changes = cat_changes[:12]
other_decrease = sum(c['change'] for c in cat_changes[12:] if c['change'] < 0)
other_increase = sum(c['change'] for c in cat_changes[12:] if c['change'] > 0)
for c in top_changes:
    if c['change'] > 0:
        wf_items.append({'name': c['name'], 'value': c['change'], 'type': 'increase'})
    else:
        wf_items.append({'name': c['name'], 'value': c['change'], 'type': 'decrease'})
if other_decrease < 0:
    wf_items.append({'name': '其他减少', 'value': other_decrease, 'type': 'decrease'})
if other_increase > 0:
    wf_items.append({'name': '其他增长', 'value': other_increase, 'type': 'increase'})
wf_items.append({'name': '5月总线索', 'value': cart_5, 'type': 'end'})
waterfall_data_json = json.dumps(wf_items, ensure_ascii=False)

# 图表数据JSON
charts_data_json = json.dumps({
    'daily_cart': data['daily_cart'],
    'daily_dm': data['daily_dm'],
    'team_compare': data['team_compare'],
    'level_data': data.get('level_data', {}),
    'all_levels': data.get('all_levels', []),
    'health_pct': health_pct,
    'interest_pct': interest_pct,
    'member_levels': member_levels,
    'channel_trends': ch,
    'holiday_effect': he,
    'weekday_pattern': data.get('weekday_pattern', {}),
    'pareto': pareto,
    'waterfall': wf_items,
    'cart_stats_by_strategy': data.get('cart_stats_by_strategy', {}),
}, ensure_ascii=False)

html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>直播间线索归因复盘看板</title>
<script src="https://cdn.tailwindcss.com?plugins=forms,container-queries"></script>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap" rel="stylesheet"/>
<link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&display=swap" rel="stylesheet"/>
<script src="https://cdn.jsdelivr.net/npm/echarts@5.5.0/dist/echarts.min.js"></script>
<script id="tailwind-config">
    tailwind.config = {{
        darkMode: "class",
        theme: {{
            extend: {{
                colors: {{
                    "on-tertiary-container": "#3e0097",
                    "surface-dim": "#d8dadc",
                    "inverse-surface": "#2d3133",
                    "error-container": "#ffdad6",
                    "outline": "#6e7881",
                    "on-primary-container": "#003751",
                    "surface-container": "#eceef0",
                    "surface-container-highest": "#e0e3e5",
                    "primary-fixed": "#c9e6ff",
                    "surface": "#f7f9fb",
                    "on-secondary-fixed": "#002113",
                    "on-error": "#ffffff",
                    "tertiary": "#6d3bd7",
                    "on-secondary": "#ffffff",
                    "on-primary-fixed-variant": "#004c6e",
                    "surface-container-high": "#e6e8ea",
                    "secondary-fixed": "#6ffbbe",
                    "on-primary-fixed": "#001e2f",
                    "surface-container-low": "#f2f4f6",
                    "background": "#f7f9fb",
                    "on-error-container": "#93000a",
                    "inverse-on-surface": "#eff1f3",
                    "surface-variant": "#e0e3e5",
                    "surface-tint": "#006591",
                    "on-surface": "#191c1e",
                    "surface-container-lowest": "#ffffff",
                    "on-tertiary": "#ffffff",
                    "on-secondary-container": "#00714d",
                    "tertiary-fixed-dim": "#d0bcff",
                    "surface-bright": "#f7f9fb",
                    "tertiary-fixed": "#e9ddff",
                    "inverse-primary": "#89ceff",
                    "primary": "#006591",
                    "secondary-container": "#6cf8bb",
                    "primary-container": "#0ea5e9",
                    "on-surface-variant": "#3e4850",
                    "secondary-fixed-dim": "#4edea3",
                    "secondary": "#006c49",
                    "on-secondary-fixed-variant": "#005236",
                    "on-tertiary-fixed-variant": "#5516be",
                    "error": "#ba1a1a",
                    "on-tertiary-fixed": "#23005c",
                    "primary-fixed-dim": "#89ceff",
                    "on-primary": "#ffffff",
                    "outline-variant": "#bec8d2",
                    "on-background": "#191c1e",
                    "tertiary-container": "#a986ff"
                }},
                borderRadius: {{
                    DEFAULT: "0.25rem",
                    lg: "0.5rem",
                    xl: "0.75rem",
                    full: "9999px"
                }},
                spacing: {{
                    margin: "32px",
                    base: "4px",
                    "card-padding": "24px",
                    "container-max": "1440px",
                    gutter: "24px"
                }},
                fontFamily: {{
                    "metric-display-mobile": ["Inter"],
                    "metric-display": ["Inter"],
                    "module-title": ["Inter"],
                    "title-main-mobile": ["Inter"],
                    "label-pill": ["Inter"],
                    "title-main": ["Inter"],
                    "subtext": ["Inter"],
                    "body-standard": ["Inter"]
                }},
                fontSize: {{
                    "metric-display-mobile": ["24px", {{"lineHeight": "32px", "fontWeight": "700"}}],
                    "metric-display": ["32px", {{"lineHeight": "40px", "letterSpacing": "-0.03em", "fontWeight": "700"}}],
                    "module-title": ["16px", {{"lineHeight": "24px", "fontWeight": "600"}}],
                    "title-main-mobile": ["20px", {{"lineHeight": "28px", "fontWeight": "600"}}],
                    "label-pill": ["12px", {{"lineHeight": "16px", "fontWeight": "600"}}],
                    "title-main": ["24px", {{"lineHeight": "32px", "letterSpacing": "-0.02em", "fontWeight": "600"}}],
                    "subtext": ["12px", {{"lineHeight": "16px", "fontWeight": "400"}}],
                    "body-standard": ["14px", {{"lineHeight": "20px", "fontWeight": "400"}}]
                }}
            }}
        }}
    }}
</script>
<style>
    .material-symbols-outlined {{
        font-variation-settings: 'FILL' 0, 'wght' 400, 'GRAD' 0, 'opsz' 24;
    }}
    .material-symbols-outlined.fill {{
        font-variation-settings: 'FILL' 1, 'wght' 400, 'GRAD' 0, 'opsz' 24;
    }}
    .glass-card {{
        background: rgba(255, 255, 255, 0.95);
        backdrop-filter: blur(10px);
        border: 1px solid rgba(226, 232, 240, 0.5);
        box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.05), 0 12px 24px -4px rgba(0, 0, 0, 0.05);
    }}
</style>
</head>
<body class="bg-background text-on-background antialiased selection:bg-primary-container selection:text-on-primary-container">
<header class="bg-surface dark:bg-inverse-surface border-b border-outline-variant dark:border-outline shadow-sm docked full-width top-0 sticky z-50">
    <div class="flex justify-between items-center w-full px-margin h-16 max-w-container-max mx-auto">
        <div>
            <h1 class="text-title-main font-title-main text-on-surface dark:text-inverse-on-surface">直播间线索归因复盘看板 | {now.year}年{current_month}月</h1>
            <p class="text-subtext font-subtext text-outline mt-0.5">{last_month_cn} vs {current_month_cn}同期对比 · 数据截至{report_date}</p>
        </div>
        <div class="flex items-center gap-4">
            <span class="text-subtext font-subtext text-outline">最后更新: {report_date}</span>
            <button onclick="window.location.reload()" class="text-primary dark:text-primary-fixed-dim hover:bg-surface-container-high dark:hover:bg-surface-variant transition-colors p-2 rounded-full active:scale-95 duration-100 ease-in-out">
                <span class="material-symbols-outlined" data-icon="refresh">refresh</span>
            </button>
        </div>
    </div>
</header>

<main class="max-w-container-max mx-auto px-margin py-margin space-y-8 pb-32">

    <!-- ========== 核心归因结论 ========== -->
    <section class="glass-card rounded-xl p-card-padding border-l-4 border-error">
        <div class="flex items-start gap-4">
            <span class="material-symbols-outlined text-error text-3xl">crisis_alert</span>
            <div class="flex-1">
                <h2 class="text-title-main font-title-main text-error mb-2">核心归因结论</h2>
                <p class="text-body-standard font-body-standard text-on-surface leading-relaxed">
                    {current_month_cn}较{last_month_cn}同期购物车线索跌 <strong class="text-error">{total_loss:,}</strong> 条（{pct_change(cart_5, cart_4)}）。
                    <span class="text-error font-bold">{primary_cause}是主因</span>：
                    {'暴跌品类贡献' + str(crashed_pct) + '%跌幅，' if crashed_pct > 0 else ''}
                    {'劳动节假期是主要影响因素：假期日均线索较4月同期跌' + str(abs(holiday_drop)) + '%，' if holiday_main else ''}
                    渠道端购物车和弹幕同比例下跌，判断为<span class="text-primary font-bold">曝光端问题</span>，非直播间引导问题。
                    策略构成方面：{strategy_change}。
                </p>

                <!-- 暴跌品类TOP3 -->
                <div class="mt-4 bg-error-container/20 rounded-lg p-3">
                    <div class="text-body-standard font-body-standard font-bold text-error mb-2">📉 暴跌品类明细（贡献{crashed_pct}%跌幅）</div>
                    <div class="grid grid-cols-1 md:grid-cols-3 gap-2">
                        {top5_problem_html}
                    </div>
                </div>

                <!-- 线级对比 -->
                <div class="mt-3 bg-surface-container-low rounded-lg p-3">
                    <div class="text-body-standard font-body-standard font-bold text-on-surface mb-1">🏥 健康线跌幅更大</div>
                    <div class="text-body-standard font-body-standard text-on-surface">
                        健康线 {last_month_cn}{team_health.get('健康线_4月', 0):,}条 → {current_month_cn}{team_health.get('健康线_5月', 0):,}条（<strong class="text-error">{team_health.get('健康线跌幅', 0)}%</strong>），
                        兴趣变美线 {last_month_cn}{team_health.get('兴趣变美线_4月', 0):,}条 → {current_month_cn}{team_health.get('兴趣变美线_5月', 0):,}条（<strong class="text-error">{team_health.get('兴趣变美线跌幅', 0)}%</strong>）。
                        健康线跌幅是变美线的 <strong>{abs(round(team_health.get('健康线跌幅', 0)/team_health.get('兴趣变美线跌幅', 1), 1)) if team_health.get('兴趣变美线跌幅', 1) != 0 else 'N/A'}</strong> 倍。
                    </div>
                </div>

                <!-- 底部小标签 -->
                <div class="mt-3 flex flex-wrap gap-4 text-subtext font-subtext">
                    <span class="flex items-center gap-1"><span class="w-2 h-2 rounded-full bg-error"></span> 购物车跌 {cart_change_5}</span>
                    <span class="flex items-center gap-1"><span class="w-2 h-2 rounded-full bg-tertiary"></span> 弹幕跌 {dm_change_5}</span>
                    <span class="flex items-center gap-1"><span class="w-2 h-2 rounded-full bg-primary"></span> TOP5集中度 {last_month_cn}{pareto_4}% → {current_month_cn}{pareto_5}%</span>
                    <span class="flex items-center gap-1"><span class="w-2 h-2 rounded-full bg-secondary"></span> 新量占比 {apr_y_pct}% → {may_y_pct}%</span>
                </div>
            </div>
        </div>
    </section>

    <!-- ========== KPIs + 目标追踪 ========== -->
    <section class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-gutter">
        <!-- Cart -->
        <div class="glass-card rounded-xl p-card-padding flex flex-col gap-4">
            <div class="flex items-center justify-between">
                <h2 class="text-module-title font-module-title text-on-surface-variant">购物车线索</h2>
                <span class="material-symbols-outlined text-outline-variant">shopping_cart</span>
            </div>
            <div class="flex items-end gap-4">
                <div>
                    <div class="text-metric-display font-metric-display text-error">{cart_5:,}</div>
                    <div class="text-subtext font-subtext text-on-surface-variant mt-1">{current_month_cn} (1-{today_day}日)</div>
                </div>
                <div class="flex items-center text-error bg-error-container px-2 py-1 rounded-md mb-1">
                    <span class="material-symbols-outlined text-[16px] mr-1">trending_down</span>
                    <span class="text-label-pill font-label-pill">{cart_change_5}%</span>
                </div>
            </div>
            <div class="grid grid-cols-2 gap-4 pt-4 border-t border-surface-container-highest mt-2">
                <div><div class="text-body-standard font-body-standard">{cart_4:,}</div><div class="text-subtext text-outline">{last_month_cn}</div></div>
                <div><div class="text-body-standard font-body-standard">{cart_3:,}</div><div class="text-subtext text-outline">3月</div></div>
            </div>
        </div>
        <!-- 新量策略 -->
        <div class="glass-card rounded-xl p-card-padding flex flex-col gap-4">
            <div class="flex items-center justify-between">
                <h2 class="text-module-title font-module-title text-on-surface-variant">新量策略</h2>
                <span class="material-symbols-outlined text-outline-variant">group_add</span>
            </div>
            <div class="flex items-end gap-4">
                <div>
                    <div class="text-metric-display font-metric-display text-on-surface">{may_y:,}</div>
                    <div class="text-subtext font-subtext text-on-surface-variant mt-1">占比 {may_y_pct}%</div>
                </div>
                <div class="flex items-center text-error bg-error-container px-2 py-1 rounded-md mb-1">
                    <span class="material-symbols-outlined text-[16px] mr-1">trending_down</span>
                    <span class="text-label-pill font-label-pill">{pct_change(may_y, apr_y)}</span>
                </div>
            </div>
            <div class="grid grid-cols-2 gap-4 pt-4 border-t border-surface-container-highest mt-2">
                <div><div class="text-body-standard font-body-standard">{apr_y:,}</div><div class="text-subtext text-outline">{last_month_cn}</div></div>
                <div><div class="text-body-standard font-body-standard">{may_y - apr_y:+,}</div><div class="text-subtext text-outline">变化</div></div>
            </div>
        </div>
        <!-- 非新量策略 -->
        <div class="glass-card rounded-xl p-card-padding flex flex-col gap-4">
            <div class="flex items-center justify-between">
                <h2 class="text-module-title font-module-title text-on-surface-variant">非新量策略</h2>
                <span class="material-symbols-outlined text-outline-variant">groups</span>
            </div>
            <div class="flex items-end gap-4">
                <div>
                    <div class="text-metric-display font-metric-display text-on-surface">{may_n:,}</div>
                    <div class="text-subtext font-subtext text-on-surface-variant mt-1">占比 {100 - may_y_pct}%</div>
                </div>
                <div class="flex items-center text-error bg-error-container px-2 py-1 rounded-md mb-1">
                    <span class="material-symbols-outlined text-[16px] mr-1">trending_down</span>
                    <span class="text-label-pill font-label-pill">{pct_change(may_n, apr_n)}</span>
                </div>
            </div>
            <div class="grid grid-cols-2 gap-4 pt-4 border-t border-surface-container-highest mt-2">
                <div><div class="text-body-standard font-body-standard">{apr_n:,}</div><div class="text-subtext text-outline">{last_month_cn}</div></div>
                <div><div class="text-body-standard font-body-standard">{may_n - apr_n:+,}</div><div class="text-subtext text-outline">变化</div></div>
            </div>
        </div>
        <!-- 目标追踪 -->
        <div class="glass-card rounded-xl p-card-padding flex flex-col gap-4">
            <div class="flex items-center justify-between">
                <h2 class="text-module-title font-module-title text-on-surface-variant">{current_month_cn}目标追踪</h2>
                <span class="material-symbols-outlined text-outline-variant">track_changes</span>
            </div>
            <div>
                <div class="text-metric-display font-metric-display text-error">{achievement}%</div>
                <div class="text-subtext font-subtext text-on-surface-variant mt-1">目标达成率 ({cart_5:,} / {target:,})</div>
            </div>
            <div class="flex-1 pb-2">
                <div class="w-full bg-surface-container-high rounded-full h-3">
                    <div class="{prog_color} h-3 rounded-full transition-all" style="width: {prog_width}%"></div>
                </div>
                <div class="flex justify-between text-subtext font-subtext mt-1">
                    <span>缺口 {gap:,}</span>
                    <span>预测 {projected_pct}%</span>
                </div>
            </div>
            <div class="pt-4 border-t border-surface-container-highest">
                <div class="text-body-standard font-body-standard text-on-surface">
                    预估流水 <strong>¥{projected_gmv:,.0f}</strong> / 目标¥900,000
                    <span class="text-subtext font-subtext text-outline ml-1">(LTV¥{ltv_forecast})</span>
                </div>
            </div>
        </div>
    </section>

    <!-- ========== 日趋势 + 假期效应 ========== -->
    <section class="grid grid-cols-1 lg:grid-cols-3 gap-gutter">
        <div class="lg:col-span-2 glass-card rounded-xl p-card-padding">
            <h2 class="text-module-title font-module-title text-on-surface mb-6">3-5月购物车线索日趋势对比</h2>
            <div class="w-full h-[400px]" id="mainTrendChart"></div>
        </div>
        <div class="glass-card rounded-xl p-card-padding">
            <h2 class="text-module-title font-module-title text-on-surface mb-4">假期效应分析</h2>
            <div class="w-full h-[200px]" id="holidayChart"></div>
            <div class="mt-4 space-y-3">
                <div class="flex justify-between items-center p-3 bg-surface-container-low rounded">
                    <span class="text-body-standard font-body-standard">4月假期(1-5)日均</span>
                    <span class="text-body-standard font-body-standard font-bold">{apr_holiday_avg}</span>
                </div>
                <div class="flex justify-between items-center p-3 bg-error-container/30 rounded">
                    <span class="text-body-standard font-body-standard text-error">5月假期(1-5)日均</span>
                    <span class="text-body-standard font-body-standard font-bold text-error">{curr_holiday_avg} ({holiday_drop}%)</span>
                </div>
                <div class="flex justify-between items-center p-3 bg-surface-container-low rounded">
                    <span class="text-body-standard font-body-standard">4月平日(6-15)日均</span>
                    <span class="text-body-standard font-body-standard font-bold">{apr_normal_avg}</span>
                </div>
                <div class="flex justify-between items-center p-3 bg-secondary-container/30 rounded">
                    <span class="text-body-standard font-body-standard text-secondary">5月平日(6-15)日均</span>
                    <span class="text-body-standard font-body-standard font-bold text-secondary">{curr_normal_avg} ({'+' if normal_drop >= 0 else ''}{normal_drop}%)</span>
                </div>
            </div>
            <p class="text-subtext font-subtext text-outline mt-4">
                {'⚠️ 假期是主要影响因素，假期后已恢复正常水平。' if holiday_main else '假期有一定影响，但平日也已下跌。'}
            </p>
        </div>
    </section>

    <!-- ========== 新量策略对比 + 会员等级 ========== -->
    <section class="grid grid-cols-1 lg:grid-cols-2 gap-gutter">
        <div class="glass-card rounded-xl p-card-padding">
            <h2 class="text-module-title font-module-title text-on-surface mb-4">新量策略同期对比 <span class="text-subtext font-subtext text-outline font-normal">· 购物车1-{today_day}号</span></h2>
            <div class="w-full h-[250px]" id="strategyBarChart"></div>
            <div class="mt-4 p-3 bg-surface-container-low rounded">
                <p class="text-body-standard font-body-standard text-on-surface">
                    <span class="font-bold">结论：</span>
                    新量策略（是）{cart_stats_by_strategy.get('4月', {}).get('是', 0)}条 → {cart_stats_by_strategy.get('5月', {}).get('是', 0)}条，
                    非新量（否）{cart_stats_by_strategy.get('4月', {}).get('否', 0)}条 → {cart_stats_by_strategy.get('5月', {}).get('否', 0)}条。
                    新量占比 {cart_stats_by_strategy.get('4月', {}).get('是占比', 0)}% → {cart_stats_by_strategy.get('5月', {}).get('是占比', 0)}%。
                </p>
            </div>
        </div>
        <div class="glass-card rounded-xl p-card-padding">
            <h2 class="text-module-title font-module-title text-on-surface mb-4">会员等级结构变化 <span class="text-subtext font-subtext text-outline font-normal">· 1-{today_day}号同期</span></h2>
            <div class="w-full h-[250px]" id="memberLevelChart"></div>
            <div class="mt-4 space-y-2 text-subtext font-subtext">
                <div class="flex justify-between p-2 bg-surface-container-low rounded">
                    <span>V7-V10 高价值用户</span>
                    <span class="text-error font-bold">4月{high_value_prev}% → 5月{high_value_curr}% {'↓' if high_value_curr < high_value_prev else '↑'}</span>
                </div>
                <div class="flex justify-between p-2 bg-surface-container-low rounded">
                    <span>V0-V1 新用户</span>
                    <span class="text-error font-bold">4月{new_user_prev}% → 5月{new_user_curr}% {'↑' if new_user_curr > new_user_prev else '↓'}</span>
                </div>
            </div>
        </div>
    </section>

    <!-- ========== 团队对比 + 星期几 ========== -->
    <section class="grid grid-cols-1 lg:grid-cols-2 gap-gutter">
        <div class="glass-card rounded-xl p-card-padding">
            <h2 class="text-module-title font-module-title text-on-surface mb-6">同期对比 (1-{today_day}号) · 二级团队线索量</h2>
            <div class="w-full h-[300px]" id="teamBarChart"></div>
        </div>
        <div class="glass-card rounded-xl p-card-padding">
            <h2 class="text-module-title font-module-title text-on-surface mb-6">星期几线索分布</h2>
            <div class="w-full h-[300px]" id="weekdayChart"></div>
        </div>
    </section>

    <!-- ========== 高价值品类 + 排期关联 ========== -->
    <section class="grid grid-cols-1 lg:grid-cols-2 gap-gutter">
        <div class="glass-card rounded-xl p-card-padding">
            <h2 class="text-module-title font-module-title text-on-surface mb-4">高LTV高线索品类 (4月TOP10)</h2>
            <p class="text-subtext font-subtext text-outline mb-4">线索≥50 & LTV≥80，按4月线索×LTV排序</p>
            <div class="overflow-x-auto">
                <table class="w-full text-left">
                    <thead>
                        <tr class="border-b border-outline-variant">
                            <th class="py-2 px-3 text-subtext font-subtext">品类</th>
                            <th class="py-2 px-3 text-subtext font-subtext text-right">4月线索</th>
                            <th class="py-2 px-3 text-subtext font-subtext text-right">4月LTV</th>
                            <th class="py-2 px-3 text-subtext font-subtext">5月状态</th>
                            <th class="py-2 px-3 text-subtext font-subtext text-right">5月线索</th>
                        </tr>
                    </thead>
                    <tbody>
                        {high_value_html}
                    </tbody>
                </table>
            </div>
        </div>
        <div class="glass-card rounded-xl p-card-padding">
            <h2 class="text-module-title font-module-title text-on-surface mb-4">未排期高线索品类 (需复播)</h2>
            <p class="text-subtext font-subtext text-outline mb-4">4月线索≥20但5月未排期的品类</p>
            <div class="space-y-2">
                {not_scheduled_html if not_scheduled_html else '<div class="text-subtext font-subtext text-outline">暂无</div>'}
            </div>
        </div>
    </section>

    <!-- ========== 线索变化瀑布图 ========== -->
    <section class="glass-card rounded-xl p-card-padding">
        <h2 class="text-module-title font-module-title text-on-surface mb-4">线索变化瀑布图 <span class="text-subtext font-subtext text-outline font-normal">· 4月(1-{today_day})→5月(1-{today_day})品类归因</span></h2>
        <div class="w-full h-[450px]" id="waterfallChart"></div>
        <div class="mt-4 p-3 bg-surface-container-low rounded">
            <p class="text-body-standard font-body-standard text-on-surface">
                <span class="font-bold">规律：</span>摄影美学、一杰瑜伽、气血【扶阳】三大品类合计减少 <strong class="text-error">1,080</strong> 条，占总跌幅的 <strong class="text-error">107.8%</strong>；风光摄影、短视频等增长品类抵消了部分跌幅。暴跌集中在前3个头部品类，非均匀下跌。
            </p>
        </div>
    </section>

    <!-- ========== 新量策略品类细分 ========== -->
    <section class="glass-card rounded-xl p-card-padding">
        <h2 class="text-module-title font-module-title text-on-surface mb-4">新量策略品类细分 <span class="text-subtext font-subtext text-outline font-normal">· 4月(1-15)→5月(1-15) 同期对比 · 购物车</span></h2>
        <div class="overflow-x-auto">
            <table class="w-full text-left">
                <thead>
                    <tr class="border-b-2 border-outline-variant">
                        <th class="py-2 px-3 text-subtext font-subtext">品类</th>
                        <th class="py-2 px-3 text-subtext font-subtext">策略</th>
                        <th class="py-2 px-3 text-subtext font-subtext text-right">4月线索</th>
                        <th class="py-2 px-3 text-subtext font-subtext text-right">5月线索</th>
                        <th class="py-2 px-3 text-subtext font-subtext text-right">环比</th>
                        <th class="py-2 px-3 text-subtext font-subtext">状态</th>
                    </tr>
                </thead>
                <tbody>
                    {strategy_cat_html}
                </tbody>
            </table>
        </div>
    </section>

    <!-- ========== 品类归因卡片 ========== -->
    <section class="glass-card rounded-xl p-card-padding">
        <div class="flex items-center justify-between mb-4">
            <h2 class="text-title-main font-title-main text-on-surface">问题品类 TOP5 <span class="text-subtext font-subtext text-outline font-normal">（按线索缺口绝对值排序 · {last_month_cn} vs {current_month_cn}）</span></h2>
            <div class="flex gap-3 text-subtext font-subtext">
                <span class="flex items-center gap-1"><span class="w-3 h-3 rounded bg-error"></span> 暴跌</span>
                <span class="flex items-center gap-1"><span class="w-3 h-3 rounded bg-[#1e293b]"></span> 消失</span>
            </div>
        </div>
        <div class="space-y-2">
            {top5_problem_html}
        </div>
    </section>

    <!-- ========== 发现 + 复盘 ========== -->
    <section class="grid grid-cols-1 lg:grid-cols-3 gap-gutter">
        <div class="lg:col-span-1 glass-card rounded-xl p-card-padding h-full">
            <h2 class="text-module-title font-module-title text-on-surface mb-4">数据发现 & 业务归因</h2>
            <ul class="space-y-4">
                {findings_html}
            </ul>
        </div>
        <div class="lg:col-span-2 glass-card rounded-xl p-card-padding h-full flex flex-col gap-6">
            <div>
                <label class="block text-body-standard font-body-standard font-bold text-on-surface mb-2">根因推演</label>
                <textarea class="w-full h-32 rounded-lg border-outline-variant bg-surface focus:border-primary focus:ring-2 focus:ring-primary-container/20 text-body-standard font-body-standard p-3 resize-none" placeholder="输入核心排查点..."></textarea>
            </div>
            <div>
                <label class="block text-body-standard font-body-standard font-bold text-on-surface mb-2">调整策略</label>
                <textarea class="w-full h-32 rounded-lg border-outline-variant bg-surface focus:border-primary focus:ring-2 focus:ring-primary-container/20 text-body-standard font-body-standard p-3 resize-none" placeholder="输入下一步计划..."></textarea>
            </div>
            <div class="flex justify-end gap-3 mt-auto">
                <button class="px-4 py-2 rounded-lg border border-outline-variant text-on-surface text-body-standard font-body-standard font-bold hover:bg-surface-container-high transition-colors">保存草稿</button>
                <button class="px-4 py-2 rounded-lg bg-primary text-on-primary text-body-standard font-body-standard font-bold hover:bg-surface-tint transition-colors">提交复盘报告</button>
            </div>
        </div>
    </section>
</main>

<script>
    const chartsData = {charts_data_json};

    document.addEventListener('DOMContentLoaded', function() {{
        const colors = {{
            primary: '#006591',
            primaryContainer: '#0ea5e9',
            secondary: '#006c49',
            tertiary: '#6d3bd7',
            error: '#ba1a1a',
            outline: '#6e7881',
            surfaceContainerLow: '#f2f4f6',
            grayMarch: '#94a3b8'
        }};

        // 1. Main Trend Chart
        const mainTrendChart = echarts.init(document.getElementById('mainTrendChart'));
        const days = Array.from({{length: 31}}, (_, i) => `${{i+1}}日`);
        const hasMar = chartsData.daily_cart && '3月' in chartsData.daily_cart;
        const marData = hasMar ? Object.values(chartsData.daily_cart['3月']) : [];
        const aprData = Object.values(chartsData.daily_cart['4月']);
        const mayData = Object.values(chartsData.daily_cart['5月']).map((v, i) => i < {today_day} ? v : null);
        const legendData = ['4月', '5月'];
        if (hasMar) legendData.unshift('3月');
        const seriesList = [
            {{
                name: '4月', type: 'line', data: aprData,
                itemStyle: {{ color: colors.primaryContainer }},
                lineStyle: {{ width: 2 }},
                areaStyle: {{
                    color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                        {{ offset: 0, color: 'rgba(14, 165, 233, 0.2)' }},
                        {{ offset: 1, color: 'rgba(14, 165, 233, 0.0)' }}
                    ])
                }},
                symbol: 'none'
            }},
            {{
                name: '5月', type: 'line', data: mayData,
                itemStyle: {{ color: colors.error }},
                lineStyle: {{ width: 2 }},
                areaStyle: {{
                    color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                        {{ offset: 0, color: 'rgba(186, 26, 26, 0.2)' }},
                        {{ offset: 1, color: 'rgba(186, 26, 26, 0.0)' }}
                    ])
                }},
                markArea: {{
                    silent: true,
                    data: [[
                        {{ xAxis: '1日', itemStyle: {{ color: 'rgba(186,26,26,0.05)' }} }},
                        {{ xAxis: '5日', itemStyle: {{ color: 'rgba(186,26,26,0.05)' }} }}
                    ]]
                }},
                symbol: 'circle',
                symbolSize: 6
            }}
        ];
        if (hasMar) {{
            seriesList.unshift({{
                name: '3月', type: 'line', data: marData,
                itemStyle: {{ color: colors.grayMarch }},
                lineStyle: {{ type: 'dashed', width: 2 }},
                symbol: 'none'
            }});
        }}

        mainTrendChart.setOption({{
            tooltip: {{ trigger: 'axis', backgroundColor: '#fff', textStyle: {{ color: '#191c1e' }}, extraCssText: 'box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);' }},
            legend: {{ data: legendData, bottom: 0 }},
            grid: {{ left: '3%', right: '4%', bottom: '10%', top: '5%', containLabel: true }},
            xAxis: {{ type: 'category', boundaryGap: false, data: days, axisLine: {{ lineStyle: {{ color: colors.outline }} }} }},
            yAxis: {{ type: 'value', splitLine: {{ lineStyle: {{ color: colors.surfaceContainerLow }} }} }},
            series: seriesList
        }});

        // 2. Holiday Chart
        const holidayChart = echarts.init(document.getElementById('holidayChart'));
        const he = chartsData.holiday_effect;
        holidayChart.setOption({{
            tooltip: {{ trigger: 'axis', axisPointer: {{ type: 'shadow' }} }},
            legend: {{ bottom: 0 }},
            grid: {{ left: '3%', right: '4%', bottom: '15%', top: '5%', containLabel: true }},
            xAxis: {{ type: 'category', data: ['假期日均(1-5)', '平日日均(6-15)'], axisLine: {{ lineStyle: {{ color: colors.outline }} }} }},
            yAxis: {{ type: 'value', splitLine: {{ lineStyle: {{ color: colors.surfaceContainerLow }} }} }},
            color: [colors.primaryContainer, colors.error],
            series: [
                {{ name: '4月', type: 'bar', data: [307, 319], barWidth: '30%', itemStyle: {{ borderRadius: [4,4,0,0] }} }},
                {{ name: '5月', type: 'bar', data: [106, 320], barWidth: '30%', itemStyle: {{ borderRadius: [4,4,0,0] }} }}
            ]
        }});

        // 3. Strategy Bar Chart
        const strategyBarChart = echarts.init(document.getElementById('strategyBarChart'));
        const st = chartsData.cart_stats_by_strategy || {{}};
        strategyBarChart.setOption({{
            tooltip: {{ trigger: 'axis', axisPointer: {{ type: 'shadow' }} }},
            legend: {{ bottom: 0 }},
            grid: {{ left: '3%', right: '4%', bottom: '15%', top: '5%', containLabel: true }},
            xAxis: {{ type: 'category', data: ['4月', '5月'], axisLine: {{ lineStyle: {{ color: colors.outline }} }} }},
            yAxis: {{ type: 'value', splitLine: {{ lineStyle: {{ color: colors.surfaceContainerLow }} }} }},
            color: [colors.primary, colors.tertiary],
            series: [
                {{ name: '新量-是', type: 'bar', data: [st['4月']?.['是']||0, st['5月']?.['是']||0], barWidth: '30%', itemStyle: {{ borderRadius: [4,4,0,0] }} }},
                {{ name: '非新量-否', type: 'bar', data: [st['4月']?.['否']||0, st['5月']?.['否']||0], barWidth: '30%', itemStyle: {{ borderRadius: [4,4,0,0] }} }}
            ]
        }});

        // 4. Member Level Chart
        const memberLevelChart = echarts.init(document.getElementById('memberLevelChart'));
        const ml = chartsData.member_levels;
        const months = ['4月', '5月'];
        const groups = ['V0-V1 新用户', 'V2-V6 普通会员', 'V7-V10 高价值'];
        const groupColors = ['#0ea5e9', '#64748b', '#ba1a1a'];
        const mlSeries = groups.map((g, i) => ({{
            name: g,
            type: 'bar',
            stack: 'total',
            data: months.map(m => ml[m]?.pct?.[g] || 0),
            itemStyle: {{ color: groupColors[i] }}
        }}));
        memberLevelChart.setOption({{
            tooltip: {{ trigger: 'axis', axisPointer: {{ type: 'shadow' }} }},
            legend: {{ bottom: 0 }},
            grid: {{ left: '3%', right: '4%', bottom: '15%', top: '5%', containLabel: true }},
            xAxis: {{ type: 'category', data: months, axisLine: {{ lineStyle: {{ color: colors.outline }} }} }},
            yAxis: {{ type: 'value', max: 100, axisLabel: {{ formatter: '{{value}}%' }}, splitLine: {{ lineStyle: {{ color: colors.surfaceContainerLow }} }} }},
            series: mlSeries
        }});

        // 5. Team Bar Chart
        const teamBarChart = echarts.init(document.getElementById('teamBarChart'));
        const t4 = chartsData.team_compare['4月'];
        const t5 = chartsData.team_compare['5月'];
        teamBarChart.setOption({{
            tooltip: {{ trigger: 'axis', axisPointer: {{ type: 'shadow' }} }},
            legend: {{ bottom: 0 }},
            grid: {{ left: '3%', right: '4%', bottom: '15%', top: '5%', containLabel: true }},
            xAxis: {{ type: 'category', data: ['4月(1-{today_day})', '5月(1-{today_day})'], axisLine: {{ lineStyle: {{ color: colors.outline }} }} }},
            yAxis: {{ type: 'value', splitLine: {{ lineStyle: {{ color: colors.surfaceContainerLow }} }} }},
            color: [colors.primary, colors.secondary],
            series: [
                {{ name: '健康线', type: 'bar', data: [t4['健康线']||0, t5['健康线']||0], barWidth: '30%', itemStyle: {{ borderRadius: [4,4,0,0] }} }},
                {{ name: '兴趣变美线', type: 'bar', data: [t4['兴趣变美线']||0, t5['兴趣变美线']||0], barWidth: '30%', itemStyle: {{ borderRadius: [4,4,0,0] }} }}
            ]
        }});

        // 6. Weekday Chart
        const weekdayChart = echarts.init(document.getElementById('weekdayChart'));
        const wd = chartsData.weekday_pattern;
        const wdNames = ['周一', '周二', '周三', '周四', '周五', '周六', '周日'];
        weekdayChart.setOption({{
            tooltip: {{ trigger: 'axis' }},
            legend: {{ bottom: 0 }},
            grid: {{ left: '3%', right: '4%', bottom: '15%', top: '5%', containLabel: true }},
            xAxis: {{ type: 'category', data: wdNames, axisLine: {{ lineStyle: {{ color: colors.outline }} }} }},
            yAxis: {{ type: 'value', splitLine: {{ lineStyle: {{ color: colors.surfaceContainerLow }} }} }},
            color: [colors.primaryContainer, colors.error],
            series: [
                {{ name: '4月', type: 'line', data: wdNames.map((_, i) => wd['4月']?.[wdNames[i]] || 0), smooth: true, symbol: 'circle' }},
                {{ name: '5月', type: 'line', data: wdNames.map((_, i) => wd['5月']?.[wdNames[i]] || 0), smooth: true, symbol: 'circle' }}
            ]
        }});

        // Waterfall Chart
        const waterfallChart = echarts.init(document.getElementById('waterfallChart'));
        const wfItems = chartsData.waterfall;
        const wfCategories = [];
        const wfBaseData = [];
        const wfBarData = [];
        let runningTotal = 0;
        const COLOR_START = '#006591';
        const COLOR_INCREASE = '#006c49';
        const COLOR_DECREASE = '#ba1a1a';
        const COLOR_END = '#f97316';
        wfItems.forEach(item => {{
            wfCategories.push(item.name);
            if (item.type === 'start') {{
                runningTotal = item.value;
                wfBaseData.push(0);
                wfBarData.push({{ value: item.value, itemStyle: {{ color: COLOR_START, borderRadius: [4,4,0,0] }} }});
            }} else if (item.type === 'end') {{
                wfBaseData.push(0);
                wfBarData.push({{ value: runningTotal, itemStyle: {{ color: COLOR_END, borderRadius: [4,4,0,0] }} }});
            }} else {{
                const change = item.value;
                if (change > 0) {{
                    wfBaseData.push(runningTotal);
                    wfBarData.push({{ value: change, itemStyle: {{ color: COLOR_INCREASE, borderRadius: [4,4,0,0] }} }});
                    runningTotal += change;
                }} else {{
                    runningTotal += change;
                    wfBaseData.push(runningTotal);
                    wfBarData.push({{ value: -change, itemStyle: {{ color: COLOR_DECREASE, borderRadius: [4,4,0,0] }} }});
                }}
            }}
        }});
        waterfallChart.setOption({{
            tooltip: {{
                trigger: 'axis',
                axisPointer: {{ type: 'shadow' }},
                formatter: params => {{
                    const bar = params.find(p => p.seriesIndex === 1);
                    if (!bar) return '';
                    const item = wfItems[bar.dataIndex];
                    const isDecrease = item.type === 'decrease';
                    const sign = isDecrease ? '-' : (item.type === 'start' || item.type === 'end') ? '' : '+';
                    const val = isDecrease ? -item.value : (item.type === 'end' ? bar.value : item.value);
                    return `<b>${{bar.name}}</b><br/>${{sign}}${{val.toLocaleString()}}`;
                }}
            }},
            legend: {{
                top: 8,
                data: [
                    {{ name: '起始/结束', icon: 'rect', itemStyle: {{ color: COLOR_START }} }},
                    {{ name: '增长', icon: 'rect', itemStyle: {{ color: COLOR_INCREASE }} }},
                    {{ name: '减少', icon: 'rect', itemStyle: {{ color: COLOR_DECREASE }} }}
                ]
            }},
            grid: {{ top: 50, right: 30, bottom: 80, left: 60 }},
            xAxis: {{
                type: 'category',
                data: wfCategories,
                axisLabel: {{ rotate: 30, color: colors.outline, fontSize: 11 }}
            }},
            yAxis: {{
                type: 'value',
                name: '购物车线索',
                splitLine: {{ lineStyle: {{ color: colors.surfaceContainerLow }} }}
            }},
            series: [
                {{
                    name: '_base',
                    type: 'bar',
                    stack: 'waterfall',
                    silent: true,
                    itemStyle: {{ color: 'transparent', borderColor: 'transparent' }},
                    data: wfBaseData
                }},
                {{
                    name: 'Change',
                    type: 'bar',
                    stack: 'waterfall',
                    data: wfBarData,
                    barMaxWidth: 40,
                    label: {{
                        show: true,
                        position: 'top',
                        color: colors.outline,
                        fontSize: 11,
                        formatter: p => {{
                            const item = wfItems[p.dataIndex];
                            if (item.type === 'start' || item.type === 'end') return p.value.toLocaleString();
                            return (item.value > 0 ? '+' : '') + item.value.toLocaleString();
                        }}
                    }}
                }}
            ]
        }});

        window.addEventListener('resize', function() {{
            mainTrendChart.resize();
            holidayChart.resize();
            strategyBarChart.resize();
            memberLevelChart.resize();
            teamBarChart.resize();
            weekdayChart.resize();
            waterfallChart.resize();
        }});
    }});
</script>
</body>
</html>
'''

with open('dashboard.html', 'w', encoding='utf-8') as f:
    f.write(html)

# 自动重排 section 顺序（确保与最新框架一致）
import re
with open('dashboard.html', 'r', encoding='utf-8') as f:
    html_content = f.read()

main_match = re.search(r'(<main.*?>)(.*?)(</main>)', html_content, re.DOTALL)
if main_match:
    main_start = main_match.group(1)
    main_content = main_match.group(2)
    main_end = main_match.group(3)
    headers = re.findall(r'<!-- ========== .*? ========== -->', main_content)
    splits = re.split(r'(<!-- ========== .*? ========== -->)', main_content)
    blocks = {}
    current_header = None
    for part in splits:
        if part.strip() in headers:
            current_header = part.strip()
            blocks[current_header] = part
        elif current_header:
            blocks[current_header] += part
    new_order = [
        '<!-- ========== 核心归因结论 ========== -->',
        '<!-- ========== KPIs + 目标追踪 ========== -->',
        '<!-- ========== 日趋势 + 假期效应 ========== -->',
        '<!-- ========== 线索变化瀑布图 ========== -->',
        '<!-- ========== 品类归因卡片 ========== -->',
        '<!-- ========== 辅助决策建议 ========== -->',
        '<!-- ========== 排期差异分析 ========== -->',
        '<!-- ========== 新量策略对比 + 会员等级 ========== -->',
        '<!-- ========== 团队对比 + 星期几 ========== -->',
        '<!-- ========== 高价值品类 + 排期关联 ========== -->',
    ]
    new_main_content = ''
    for h in new_order:
        if h in blocks:
            new_main_content += blocks[h]
    new_html = html_content[:main_match.start()] + main_start + new_main_content + main_end + html_content[main_match.end():]
    with open('dashboard.html', 'w', encoding='utf-8') as f:
        f.write(new_html)

print("✅ dashboard.html 已生成")

# ==================== 生成图表 ====================
chart_imgs = {}
try:
    import sys
    sys.path.insert(0, '/Users/zhengkeying/.claude/skills/chart/scripts')
    from build_chart import create_project, build_chart_custom, save_chart, screenshot_chart, save_data
    import shutil

    charts_out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'weekly_report_charts')
    os.makedirs(charts_out_dir, exist_ok=True)

    # 图表1: 暴跌品类对比
    proj1 = os.path.join(charts_out_dir, 'crashed-cats-20260517')
    os.makedirs(proj1, exist_ok=True)
    c_names = [c['品类'] for c in all_crashed_cats]
    c4_vals = [c.get('4月(1-15)', c.get('4月', 0)) for c in all_crashed_cats]
    c5_vals = [c.get('5月(1-15)', c.get('5月', 0)) for c in all_crashed_cats]
    chart_js1 = f"""
window.CHART_INSTANCES = [];
const chart = echarts.init(document.getElementById('main-chart'), 'dark');
chart.setOption({{
  backgroundColor: 'transparent',
  tooltip: {{ trigger: 'axis', axisPointer: {{ type: 'shadow' }} }},
  legend: {{ top: 8 }},
  grid: {{ top: 50, right: 30, bottom: 30, left: 60 }},
  xAxis: {{ type: 'category', data: {json.dumps(c_names, ensure_ascii=False)} }},
  yAxis: {{ type: 'value', name: '线索数' }},
  series: [
    {{ name: '4月线索', type: 'bar', data: {json.dumps(c4_vals)}, itemStyle: {{ color: '#0ea5e9', borderRadius: [4,4,0,0] }} }},
    {{ name: '5月线索', type: 'bar', data: {json.dumps(c5_vals)}, itemStyle: {{ color: '#ba1a1a', borderRadius: [4,4,0,0] }} }}
  ]
}});
CHART_INSTANCES.push(chart);
"""
    html1 = build_chart_custom(title='暴跌品类线索对比', subtitle='4月 vs 5月（1-15日同期）', body_html='<div id="main-chart" style="width:100%;height:450px;"></div>', chart_js=chart_js1)
    save_chart(html1, project_dir=proj1)
    save_data({'categories': c_names, 'series': [{'name':'4月','data':c4_vals},{'name':'5月','data':c5_vals}]}, project_dir=proj1)
    png1 = screenshot_chart(proj1)
    if png1:
        chart_imgs['crashed_cats'] = os.path.join(charts_out_dir, 'crashed-cats-20260517.png')
        shutil.copy(png1, chart_imgs['crashed_cats'])

    # 图表2: 线索/万曝光效率排名（横向，按值着色）
    proj2 = os.path.join(charts_out_dir, 'exposure-efficiency-20260517')
    os.makedirs(proj2, exist_ok=True)
    exp_names = [c['品类'] for c in exposure_cats[:10]][::-1]
    exp_vals = [c['转化率'] for c in exposure_cats[:10]][::-1]
    exp_data = []
    for v in exp_vals:
        if v >= 3: color = '#006c49'
        elif v >= 1.5: color = '#006591'
        elif v > 0: color = '#f97316'
        else: color = '#ba1a1a'
        exp_data.append({'value': v, 'itemStyle': {'color': color, 'borderRadius': [0,4,4,0]}})
    chart_js2 = f"""
window.CHART_INSTANCES = [];
const chart = echarts.init(document.getElementById('main-chart'), 'dark');
chart.setOption({{
  backgroundColor: 'transparent',
  tooltip: {{ trigger: 'axis', axisPointer: {{ type: 'shadow' }} }},
  legend: {{ show: false }},
  grid: {{ top: 20, right: 60, bottom: 30, left: 100 }},
  xAxis: {{ type: 'value', name: '线索/万曝光' }},
  yAxis: {{ type: 'category', data: {json.dumps(exp_names, ensure_ascii=False)} }},
  series: [{{
    name: '线索/万曝光',
    type: 'bar',
    data: {json.dumps(exp_data, ensure_ascii=False)},
    label: {{ show: true, position: 'right' }}
  }}]
}});
CHART_INSTANCES.push(chart);
"""
    html2 = build_chart_custom(title='线索/万曝光效率排名', subtitle='5月有曝光品类（按转化率降序）', body_html='<div id="main-chart" style="width:100%;height:450px;"></div>', chart_js=chart_js2)
    save_chart(html2, project_dir=proj2)
    save_data({'categories': exp_names, 'values': exp_vals}, project_dir=proj2)
    png2 = screenshot_chart(proj2)
    if png2:
        chart_imgs['exposure_efficiency'] = os.path.join(charts_out_dir, 'exposure-efficiency-20260517.png')
        shutil.copy(png2, chart_imgs['exposure_efficiency'])

    # 图表3: 假期效应对比
    proj3 = os.path.join(charts_out_dir, 'holiday-effect-20260517')
    os.makedirs(proj3, exist_ok=True)
    chart_js3 = """
window.CHART_INSTANCES = [];
const chart = echarts.init(document.getElementById('main-chart'), 'dark');
chart.setOption({
  backgroundColor: 'transparent',
  tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
  legend: { top: 8 },
  grid: { top: 50, right: 30, bottom: 30, left: 60 },
  xAxis: { type: 'category', data: ['假期日均(1-5日)', '平日日均(6-15日)'] },
  yAxis: { type: 'value', name: '日均线索' },
  series: [
    { name: '4月', type: 'bar', data: [307, 319], itemStyle: { color: '#0ea5e9', borderRadius: [4,4,0,0] } },
    { name: '5月', type: 'bar', data: [106, 320], itemStyle: { color: '#ba1a1a', borderRadius: [4,4,0,0] } }
  ]
});
CHART_INSTANCES.push(chart);
"""
    html3 = build_chart_custom(title='假期效应分析', subtitle='4月 vs 5月 假期/平日日均线索对比', body_html='<div id="main-chart" style="width:100%;height:450px;"></div>', chart_js=chart_js3)
    save_chart(html3, project_dir=proj3)
    save_data({'categories': ['假期日均(1-5日)', '平日日均(6-15日)'], 'series': [{'name':'4月','data':[307,319]},{'name':'5月','data':[106,320]}]}, project_dir=proj3)
    png3 = screenshot_chart(proj3)
    if png3:
        chart_imgs['holiday_effect'] = os.path.join(charts_out_dir, 'holiday-effect-20260517.png')
        shutil.copy(png3, chart_imgs['holiday_effect'])

    print("✅ 周报图表已生成")
except Exception as e:
    print(f"[chart] 图表生成跳过: {e}")
    chart_imgs = {}

img_crashed = "![暴跌品类线索对比](weekly_report_charts/crashed-cats-20260517.png)" if chart_imgs.get('crashed_cats') else ''
img_exposure = "![线索/万曝光效率排名](weekly_report_charts/exposure-efficiency-20260517.png)" if chart_imgs.get('exposure_efficiency') else ''
img_holiday = "![假期效应分析](weekly_report_charts/holiday-effect-20260517.png)" if chart_imgs.get('holiday_effect') else ''

# ==================== 生成周报 ====================
# 未排期品类 markdown
not_scheduled_md = ''
for c in not_scheduled[:10]:
    not_scheduled_md += "- **{0}**: 4月{1}条 → 5月未排期\n".format(c['品类'], c['4月线索'])

# 暴跌品类 markdown 表格
crashed_md_rows = ''
for c in all_crashed_cats:
    c4 = c.get('4月(1-15)', c.get('4月', 0))
    c5 = c.get('5月(1-15)', c.get('5月', 0))
    change = c.get('环比', 0)
    ltv = c.get('4月LTV', 0)
    team = c.get('二级团队', '')
    reason = '待分析'
    for drop_cat in schedule_corr.get('cat_schedule', []):
        if drop_cat['品类'] == c['品类']:
            reason = drop_cat.get('暴跌原因', '待分析')
            break
    crashed_md_rows += "| **{0}** | {1} | {2} | {3} | **{4}%** | ¥{5} | {6} |\n".format(
        c['品类'], team, c4, c5, change, ltv, reason
    )

# 线索/万曝光 markdown 表格
exposure_md_rows = ''
for c in exposure_cats[:10]:
    exposure_md_rows += "| {0} | {1:,} | {2:,} | {3} |\n".format(
        c['品类'], c['5月线索'], c['5月曝光'], c['转化率']
    )

# 未排期品类复播建议
recommendation_md = ''
if not_scheduled:
    recommendation_md = '\n'.join(
        "- **{0}**（4月{1}条，5月未排期）".format(c['品类'], c['4月线索'])
        for c in not_scheduled[:8]
    )
else:
    recommendation_md = '暂无'

# 高价值风险品类
high_value_risk = ''
for c in high_value[:10]:
    if c.get('状态') in ['暴跌', '下滑', '消失']:
        high_value_risk += "- **{0}**（LTV ¥{1}）: {2} {3}%\n".format(
            c['品类'], c['4月LTV'], c['状态'], c['环比']
        )

# 团队跌幅倍数
team_ratio = abs(round(team_health['健康线跌幅']/team_health['兴趣变美线跌幅'],1)) if team_health['兴趣变美线跌幅'] != 0 else 'N/A'

# 预测达成率
predicted_achievement = round(projected_gmv/900000*100,1)

# 缺口弥补预测
recoverable = sum(
    c.get('4月(1-15)', c.get('4月',0)) - c.get('5月(1-15)', c.get('5月',0))
    for c in all_crashed_cats
) // 2

# 预测缺口（目标-预测）
predicted_gap = target - projected

# 场次减少品类恢复排期的理论增量
schedule_recoverable = 0
schedule_recover_detail = []
for c in sr_reason:
    s4 = c['4月排期']
    s5 = c['5月排期']
    eff5 = c['线索/场次_5月']
    if s4 > s5 and eff5 > 0:
        potential = round(s4 * eff5 - c['5月线索'])
        schedule_recoverable += potential
        schedule_recover_detail.append((c['品类'], s4, s5, eff5, potential))

# 未排期高线索/高LTV品类恢复排期的理论增量
# 从not_scheduled中找4月线索>50且5月线索<4月的品类
ns_recoverable = 0
ns_recover_detail = []
for c in not_scheduled:
    if c['4月线索'] >= 50 and c['5月线索'] < c['4月线索']:
        c4 = c['4月线索']
        c5 = c['5月线索']
        potential = round(c4 - c5)
        ns_recoverable += potential
        ns_recover_detail.append((c['品类'], c4, c5, c.get('4月排期', 0), potential))

# 气血扶阳单独处理（4月排期为0但线索暴跌的高LTV品类）
qi_xue = None
for c in cat_schedule_all:
    if '气血' in c['品类'] and c['5月排期'] == 0:
        qi_xue = c
        break

# 达标策略总增量
total_recoverable = recoverable + schedule_recoverable + ns_recoverable
new_projected = projected + total_recoverable
new_achievement = round(new_projected / target * 100, 1)

# === 动态生成周报表格 ===
# P0-1 转化效率暴跌表格
p01_rows = []
for c in conversion_issues[:5]:
    loss = c['4月线索'] - c['5月线索']
    s4 = c['4月排期']
    s5 = c['5月排期']
    eff4 = c.get('线索/场次_4月', round(c['4月线索']/s4,1) if s4 else 0)
    eff5 = c.get('线索/场次_5月', round(c['5月线索']/s5,1) if s5 else 0)
    p01_rows.append(f"| {c['品类']} | {c['4月线索']:,} | {c['5月线索']:,} | {loss:,} | {s4}→{s5} | {eff4}→{eff5} |")
p01_table_rows = '\n'.join(p01_rows)

# P0-2 未排期表格
p02_rows = []
for c in ns_reason[:5]:
    s4 = c.get('4月排期', 0)
    ltv_val = c.get('4月LTV', 0)
    p02_rows.append(f"| {c['品类']} | {c['4月线索']:,} | {c['5月线索']:,} | {s4} | ¥{ltv_val} | 高LTV停播，流水损失大 |")
p02_table_rows = '\n'.join(p02_rows)

# P1 场次减少表格
p1_rows = []
for c in sr_reason[:5]:
    s4 = c['4月排期']
    s5 = c['5月排期']
    eff4 = c.get('线索/场次_4月', round(c['4月线索']/s4,1) if s4 else 0)
    eff5 = c.get('线索/场次_5月', round(c['5月线索']/s5,1) if s5 else 0)
    added = round((s4 - s5) * eff4) if s4 > s5 else 0
    p1_rows.append(f"| {c['品类']} | {s4}→{s5} | {eff4}→{eff5} | +{added:,} 条 |")
p1_table_rows = '\n'.join(p1_rows)

# P2 低转化品类文本
low_conv_cats = [c for c in cat_schedule_all if c.get('转化率', 0) > 0 and c.get('转化率', 999) <= 1]
low_conv_text = '、'.join([f"{c['品类']}（{c['转化率']:.1f}）" for c in low_conv_cats[:6]]) if low_conv_cats else '暂无'

weekly_report = f"""# 直播间线索周报

**汇报周期**: 2026年5月1日-15日（对比4月1-15日同期）
**汇报人**: 数据分析组
**生成时间**: 2026-05-17

---

## 一、核心目标进度

| 指标 | 数值 | 状态 |
|------|------|------|
| 5月目标 | {target:,} 条 | - |
| 当前（1-15日） | {cart_5:,} 条 | 达成率 **{achievement}%** |
| 缺口 | {gap:,} 条 | - |
| 预测月底 | {projected:,.0f} 条 | 预测达成率 **{projected_pct}%** |
| 预测缺口 | {predicted_gap:,.0f} 条 | 需回补 |
| 预估流水 | ¥{projected_gmv:,.0f} | 目标 ¥900,000，预测达成 {predicted_achievement}% |

**结论**: 5月较4月同期购物车线索跌 **{total_loss:,}** 条。按当前趋势预测月底仅 {projected:,.0f} 条，距目标 **{predicted_gap:,.0f}** 条。问题集中在品类排期端：转化效率暴跌、高LTV品类未排期、场次减少三重因素叠加。

---

## 二、原因拆解（按P0优先级分层）

### 2.1 P0-1 转化效率暴跌（最大损失源，损失 {conversion_loss:,} 条）

**特征**: 排期未减或微增，但单场线索效率暴跌。{len(conversion_issues)}个品类中核心损失来自：

| 品类 | 4月线索 | 5月线索 | 损失 | 排期变化 | 单场效率变化 |
|------|---------|---------|------|----------|--------------|
{p01_table_rows}

**决策**: 立即排查直播间引导话术、商品吸引力、落地页转化链路。建议对比4月/5月单场直播录像找差异。

**回补潜力**: 若恢复至4月50%水平，可增加约 **{recoverable:,}** 条线索。

### 2.2 P0-2 高LTV品类未排期（对流水影响最大）

**特征**: 4月有排期但5月完全停播，排期取消 4月{ns_s4}场 → 5月0场。

| 品类 | 4月线索 | 5月线索 | 4月排期 | LTV | 停播影响 |
|------|---------|---------|---------|-----|----------|
{p02_table_rows}

**决策**: 优先推动复播。{', '.join(c['品类'] + '（4月单场次' + str(round(c['4月线索']/c['4月排期']) if c['4月排期'] else 0) + '条）' for c in ns_reason[:2])}复播价值高。

**回补潜力**: 恢复排期后按4月水平估算，可增加约 **{ns_recoverable:,}** 条线索。

### 2.3 P1 场次减少但效率提升（可快速恢复，理论可增 {schedule_recoverable:,} 条）

**特征**: 场次减少但单场效率反而提升，加场即可快速恢复。

| 品类 | 4月排期 | 5月排期 | 单场效率变化 | 若恢复4月场次可增 |
|------|---------|---------|--------------|-------------------|
{p1_table_rows}

**决策**: 评估加场。这3个品类单场效率均提升，说明内容和用户匹配度没问题，只是曝光不足。加场是最快回补方式。

### 2.4 P2 低转化品类优化（长期提升）

线索/万曝光 ≤1 的品类：{low_conv_text}。需优化商品吸引力和直播间引导策略。

### 2.5 其他相关性因素

**假期效应**: 假期后平日已恢复正常（320 vs 319），平日下跌与假期无关。

**团队对比**: 健康线跌幅 {team_health['健康线跌幅']}% 是变美线 {team_health['兴趣变美线跌幅']}% 的 **{team_ratio}** 倍，健康线受损更重。

**高价值用户流失**: V7-V10 占比从 18.0% 降至 12.3%，需关注用户质量。

---

## 三、关键发现

1. **转化效率暴跌是最大损失源**: 排期未减但单场暴跌，损失 {conversion_loss:,} 条，占总跌幅的 {round(conversion_loss/total_loss*100,1) if total_loss else 0}%
2. **高LTV品类停播对流水影响最大**: {', '.join(c['品类'] + ' LTV ¥' + str(c.get('4月LTV', 0)) for c in ns_reason[:2] if c.get('4月LTV', 0) > 0)} 停播，对流水影响最大
3. **场次减少品类反而效率提升**: {sr_reason[0]['品类'] if sr_reason else '部分品类'}单场效率提升，加场即可快速回补
4. **假期因素已消退**: 平日数据已恢复至4月水平
5. **健康线受损更重**: 跌幅是变美线的 {team_ratio} 倍

---

## 四、下一步策略（达标路径）

**当前预测缺口**: {predicted_gap:,.0f} 条（预测 {projected:,.0f} → 目标 {target:,}）

| 策略 | 优先级 | 具体行动 | 预期回补 | 月底预测 |
|------|--------|----------|----------|----------|
| 策略1：恢复转化问题品类至4月50% | P0-1 | 排查{', '.join(c['品类'] for c in conversion_issues[:3])}话术/链路 | +{recoverable:,} 条 | {projected+recoverable:,.0f} |
| 策略2：恢复未排期高LTV品类排期 | P0-2 | 推动{', '.join(c['品类'] for c in ns_reason[:2])}复播 | +{ns_recoverable:,} 条 | {projected+recoverable+ns_recoverable:,.0f} |
| 策略3：场次减少品类加场 | P1 | {', '.join(c['品类'] + '+' + str(c['4月排期']-c['5月排期']) + '场' for c in sr_reason[:3] if c['4月排期'] > c['5月排期'])} | +{schedule_recoverable:,} 条 | {new_projected:,.0f} |
| 策略4：低转化品类优化 | P2 | 优化{', '.join(c['品类'] for c in low_conv_cats[:2])}商品和引导 | +~200 条 | {new_projected+200:,.0f} |

**综合达标路径**: 若P0+P1策略全部执行，月底预测可达 **{new_projected:,.0f}** 条（达成率 {new_achievement}%），接近目标 {target:,} 条。核心抓手是：
- **立即行动**：恢复{', '.join(c['品类'] for c in ns_reason[:2])}排期（高LTV，对流水影响最大）
- **本周完成**：排查{conversion_issues[0]['品类'] if conversion_issues else '核心'}转化链路（损失最大）
- **同步推进**：{', '.join(c['品类'] for c in sr_reason[:3])}加场（效率已提升，加场即见效）
"""

with open('weekly_report_20260517.md', 'w', encoding='utf-8') as f:
    f.write(weekly_report)

print("✅ weekly_report_20260517.md 已生成")

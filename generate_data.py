import pandas as pd
import json
from collections import defaultdict
from datetime import datetime

# 读取数据
files = {
    '3月': '3月直播间数据分析.xlsx',
    '4月': '4月直播间数据分析.xlsx',
    '5月': '5月直播间数据分析.xlsx',
}

dfs = {}
for m, f in files.items():
    df = pd.read_excel(f, sheet_name='明细')
    df['例子日期'] = pd.to_datetime(df['例子时间']).dt.date
    df['例子日'] = pd.to_datetime(df['例子时间']).dt.day
    dfs[m] = df

# 1. 购物车/弹幕按月总量
total_stats = {}
for m, df in dfs.items():
    cart = df[df['三级团队'] == '直播间购物车']
    dm = df[df['三级团队'] == '直播间弹幕']
    total_stats[m] = {
        '购物车': len(cart),
        '弹幕': len(dm),
    }

# 2. 购物车日趋势（整月按天）
daily_cart = {}
for m, df in dfs.items():
    cart = df[df['三级团队'] == '直播间购物车']
    daily = cart.groupby('例子日').size().to_dict()
    # 补全到31天
    daily_cart[m] = {str(d): int(daily.get(d, 0)) for d in range(1, 32)}

# 3. 弹幕日趋势
daily_dm = {}
for m, df in dfs.items():
    dm = df[df['三级团队'] == '直播间弹幕']
    daily = dm.groupby('例子日').size().to_dict()
    daily_dm[m] = {str(d): int(daily.get(d, 0)) for d in range(1, 32)}

# 4. 二级团队1-15号同期对比
team_compare = {}
for m, df in dfs.items():
    cart = df[(df['三级团队'] == '直播间购物车') & (df['例子日'] <= 15)]
    team = cart.groupby('二级团队').size().to_dict()
    team_compare[m] = {k: int(v) for k, v in team.items()}

# 5. 品类下钻数据（1-15号）
cat_data = []
# 先收集所有品类和团队
all_cats = set()
cat_team_map = {}
for m, df in dfs.items():
    cart = df[(df['三级团队'] == '直播间购物车') & (df['例子日'] <= 15)]
    for _, row in cart.iterrows():
        cat = row['品类名']
        team = row['二级团队']
        all_cats.add(cat)
        cat_team_map[cat] = team

for cat in sorted(all_cats):
    team = cat_team_map.get(cat, '未知')
    counts = {}
    for m, df in dfs.items():
        cart = df[(df['三级团队'] == '直播间购物车') & (df['例子日'] <= 15)]
        cnt = len(cart[cart['品类名'] == cat])
        counts[m] = cnt

    # 计算状态
    c3, c4, c5 = counts['3月'], counts['4月'], counts['5月']
    if c4 > 0 and c5 == 0:
        status = '消失'
        change = -100
    elif c4 > 0:
        change = round((c5 - c4) / c4 * 100, 1)
        if change <= -70:
            status = '暴跌'
        elif change <= -30:
            status = '下滑'
        else:
            status = '扛住'
    elif c4 == 0 and c5 > 0:
        status = '新增'
        change = 999
    else:
        status = '无数据'
        change = 0

    cat_data.append({
        '品类': cat,
        '二级团队': team,
        '3月': c3,
        '4月': c4,
        '5月': c5,
        '环比': change,
        '状态': status,
    })

# 按4月降序排
cat_data.sort(key=lambda x: x['4月'], reverse=True)

# 6. 会员等级占比变化（整月购物车）
level_data = {}
all_levels = set()
for m, df in dfs.items():
    cart = df[df['三级团队'] == '直播间购物车']
    levels = cart['会员等级'].value_counts().to_dict()
    level_data[m] = {k: int(v) for k, v in levels.items()}
    all_levels.update(levels.keys())

# 7. 关键发现清单
findings = []
# 消失的品类
for c in cat_data:
    if c['状态'] == '消失':
        findings.append({
            'severity': 'high',
            'text': f"{c['品类']} 4月{c['4月']}条→5月直接消失（未排期）",
        })
# 暴跌的品类
for c in cat_data:
    if c['状态'] == '暴跌':
        findings.append({
            'severity': 'high',
            'text': f"{c['品类']} 4月{c['4月']}条→5月{c['5月']}条（跌幅{c['环比']}%）",
        })
# 团队波动
health_3 = team_compare['3月'].get('健康线', 0)
health_4 = team_compare['4月'].get('健康线', 0)
health_5 = team_compare['5月'].get('健康线', 0)
interest_3 = team_compare['3月'].get('兴趣变美线', 0)
interest_4 = team_compare['4月'].get('兴趣变美线', 0)
interest_5 = team_compare['5月'].get('兴趣变美线', 0)

if health_4 > 0:
    h_change = round((health_5 - health_4) / health_4 * 100, 1)
    findings.append({
        'severity': 'medium',
        'text': f"健康线同期波动剧烈：4月较3月+{round((health_4-health_3)/health_3*100,0):.0f}%，5月较4月{h_change}%",
    })

if interest_4 > 0:
    i_change = round((interest_5 - interest_4) / interest_4 * 100, 1)
    findings.append({
        'severity': 'low',
        'text': f"兴趣变美线相对稳定：5月较4月{i_change}%",
    })

# 汇总输出
data = {
    'total_stats': total_stats,
    'daily_cart': daily_cart,
    'daily_dm': daily_dm,
    'team_compare': team_compare,
    'cat_data': cat_data,
    'level_data': level_data,
    'all_levels': sorted(list(all_levels)),
    'findings': findings,
}

with open('dashboard_data.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print("数据已生成到 dashboard_data.json")
print(f"品类数: {len(cat_data)}")
print(f"关键发现: {len(findings)}")
print(f"会员等级: {sorted(list(all_levels))}")

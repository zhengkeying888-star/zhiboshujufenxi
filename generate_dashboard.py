import json

with open('dashboard_data.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# 计算环比
def pct_change(new, old):
    if old == 0:
        return '+∞' if new > 0 else '0'
    v = round((new - old) / old * 100, 1)
    return f"{v:+.1f}"

cart_3 = data['total_stats']['3月']['购物车']
cart_4 = data['total_stats']['4月']['购物车']
cart_5 = data['total_stats']['5月']['购物车']
cart_change_4 = pct_change(cart_4, cart_3)
cart_change_5 = pct_change(cart_5, cart_4)

dm_3 = data['total_stats']['3月']['弹幕']
dm_4 = data['total_stats']['4月']['弹幕']
dm_5 = data['total_stats']['5月']['弹幕']
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
health_cats = [c for c in cat_data if c['二级团队'] == '健康线']
interest_cats = [c for c in cat_data if c['二级团队'] == '兴趣变美线']

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
    cfg = status_config.get(c['状态'], status_config['无数据'])
    c3, c4, c5 = c['3月'], c['4月'], c['5月']
    # 5月数字颜色
    if c['状态'] == '消失':
        c5_color = 'bg-surface-dim text-inverse-surface'
        c5_num_color = 'text-inverse-surface font-bold'
    elif c['状态'] in ['暴跌', '下滑']:
        c5_color = 'bg-error-container text-error'
        c5_num_color = 'text-error font-bold'
    elif c['状态'] == '扛住':
        c5_color = 'bg-secondary-container text-on-secondary-container'
        c5_num_color = 'text-on-secondary-container font-bold'
    else:
        c5_color = 'bg-primary-fixed text-on-primary-fixed'
        c5_num_color = 'text-on-primary-fixed font-bold'

    return f'''
    <div class="bg-surface-container-lowest border border-outline-variant rounded-lg p-4 hover:bg-surface transition-colors cursor-default {cfg['border']}">
        <div class="flex justify-between items-start mb-3">
            <h4 class="text-body-standard font-body-standard font-bold text-on-surface">{c['品类']}</h4>
            <span class="px-2 py-1 rounded text-label-pill font-label-pill flex items-center gap-1 {cfg['color']}">
                {cfg['label']}
            </span>
        </div>
        <div class="grid grid-cols-3 gap-2 text-center">
            <div class="bg-surface-container-low p-2 rounded">
                <div class="text-subtext font-subtext text-outline">3月</div>
                <div class="text-body-standard font-body-standard">{c3:,}</div>
            </div>
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

health_cards = '\n'.join(render_cat_card(c) for c in health_cats)
interest_cards = '\n'.join(render_cat_card(c) for c in interest_cats)

# 关键发现
findings_html = ''
for f in data['findings']:
    if f['severity'] == 'high':
        border_color = 'border-error'
        icon_color = 'text-error'
        icon = 'warning'
    elif f['severity'] == 'medium':
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

# 图表数据JSON
charts_data_json = json.dumps({
    'daily_cart': data['daily_cart'],
    'daily_dm': data['daily_dm'],
    'team_compare': data['team_compare'],
    'level_data': data['level_data'],
    'all_levels': data['all_levels'],
    'health_pct': health_pct,
    'interest_pct': interest_pct,
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
            <h1 class="text-title-main font-title-main text-on-surface dark:text-inverse-on-surface">直播间线索归因复盘看板</h1>
            <p class="text-subtext font-subtext text-outline mt-0.5">2026年3-5月趋势对比 · 数据截至5月15日</p>
        </div>
        <div class="flex items-center gap-4">
            <span class="text-subtext font-subtext text-outline">最后更新: 2026-05-15</span>
            <button onclick="window.location.reload()" class="text-primary dark:text-primary-fixed-dim hover:bg-surface-container-high dark:hover:bg-surface-variant transition-colors p-2 rounded-full active:scale-95 duration-100 ease-in-out">
                <span class="material-symbols-outlined" data-icon="refresh">refresh</span>
            </button>
        </div>
    </div>
</header>

<main class="max-w-container-max mx-auto px-margin py-margin space-y-8 pb-32">
    <!-- KPIs -->
    <section class="grid grid-cols-1 md:grid-cols-3 gap-gutter">
        <!-- Cart -->
        <div class="glass-card rounded-xl p-card-padding flex flex-col gap-4">
            <div class="flex items-center justify-between">
                <h2 class="text-module-title font-module-title text-on-surface-variant">购物车线索 (Cart Leads)</h2>
                <span class="material-symbols-outlined text-outline-variant" data-icon="shopping_cart">shopping_cart</span>
            </div>
            <div class="flex items-end gap-4">
                <div>
                    <div class="text-metric-display font-metric-display text-error">{cart_5:,}</div>
                    <div class="text-subtext font-subtext text-on-surface-variant mt-1">5月 (May) · 截至15日</div>
                </div>
                <div class="flex items-center text-error bg-error-container px-2 py-1 rounded-md mb-1">
                    <span class="material-symbols-outlined text-[16px] mr-1" data-icon="trending_down">trending_down</span>
                    <span class="text-label-pill font-label-pill">{cart_change_5}%</span>
                </div>
            </div>
            <div class="grid grid-cols-2 gap-4 pt-4 border-t border-surface-container-highest mt-2">
                <div>
                    <div class="text-body-standard font-body-standard text-on-surface">{cart_3:,}</div>
                    <div class="text-subtext font-subtext text-outline">3月 (Mar)</div>
                </div>
                <div>
                    <div class="text-body-standard font-body-standard text-on-surface">{cart_4:,}</div>
                    <div class="text-subtext font-subtext text-outline">4月 (Apr)</div>
                </div>
            </div>
        </div>
        <!-- Chat -->
        <div class="glass-card rounded-xl p-card-padding flex flex-col gap-4">
            <div class="flex items-center justify-between">
                <h2 class="text-module-title font-module-title text-on-surface-variant">公屏弹幕线索 (Chat Leads)</h2>
                <span class="material-symbols-outlined text-outline-variant" data-icon="chat_bubble">chat_bubble</span>
            </div>
            <div class="flex items-end gap-4">
                <div>
                    <div class="text-metric-display font-metric-display text-error">{dm_5:,}</div>
                    <div class="text-subtext font-subtext text-on-surface-variant mt-1">5月 (May) · 截至15日</div>
                </div>
                <div class="flex items-center text-error bg-error-container px-2 py-1 rounded-md mb-1">
                    <span class="material-symbols-outlined text-[16px] mr-1" data-icon="trending_down">trending_down</span>
                    <span class="text-label-pill font-label-pill">{dm_change_5}%</span>
                </div>
            </div>
            <div class="grid grid-cols-2 gap-4 pt-4 border-t border-surface-container-highest mt-2">
                <div>
                    <div class="text-body-standard font-body-standard text-on-surface">{dm_3:,}</div>
                    <div class="text-subtext font-subtext text-outline">3月 (Mar)</div>
                </div>
                <div>
                    <div class="text-body-standard font-body-standard text-on-surface">{dm_4:,}</div>
                    <div class="text-subtext font-subtext text-outline">4月 (Apr)</div>
                </div>
            </div>
        </div>
        <!-- Mix -->
        <div class="glass-card rounded-xl p-card-padding flex flex-col gap-4">
            <div class="flex items-center justify-between">
                <h2 class="text-module-title font-module-title text-on-surface-variant">业务线占比分布</h2>
                <span class="material-symbols-outlined text-outline-variant" data-icon="pie_chart">pie_chart</span>
            </div>
            <div class="w-full h-32 flex-1" id="kpiRingChart"></div>
        </div>
    </section>

    <!-- Main Trend -->
    <section class="glass-card rounded-xl p-card-padding">
        <h2 class="text-module-title font-module-title text-on-surface mb-6">3-5月购物车线索日趋势对比</h2>
        <div class="w-full h-[400px]" id="mainTrendChart"></div>
    </section>

    <!-- Team + Level -->
    <section class="grid grid-cols-1 lg:grid-cols-2 gap-gutter">
        <div class="glass-card rounded-xl p-card-padding">
            <h2 class="text-module-title font-module-title text-on-surface mb-6">同期对比 (1-15号) · 二级团队线索量</h2>
            <div class="w-full h-[300px]" id="teamBarChart"></div>
            <p class="text-subtext font-subtext text-outline mt-4">
                健康线同期波动剧烈：4月较3月+72%，5月较4月-31%；兴趣变美线相对稳定：5月较4月-14%
            </p>
        </div>
        <div class="glass-card rounded-xl p-card-padding">
            <h2 class="text-module-title font-module-title text-on-surface mb-6">线索用户等级结构变化</h2>
            <div class="w-full h-[300px]" id="userLevelChart"></div>
        </div>
    </section>

    <!-- Category Attribution -->
    <section class="space-y-6">
        <h2 class="text-title-main font-title-main text-on-surface">品类线索归因分析 <span class="text-subtext font-subtext text-outline font-normal">（1-15号同期对比）</span></h2>
        <div class="grid grid-cols-1 md:grid-cols-2 gap-gutter">
            <div class="space-y-4">
                <h3 class="text-module-title font-module-title text-primary border-b-2 border-primary-container pb-2 inline-block">健康线 (Health Line)</h3>
                {health_cards}
            </div>
            <div class="space-y-4">
                <h3 class="text-module-title font-module-title text-secondary border-b-2 border-secondary-container pb-2 inline-block">兴趣变美线 (Beauty Line)</h3>
                {interest_cards}
            </div>
        </div>
    </section>

    <!-- Chat Trend -->
    <section class="glass-card rounded-xl p-card-padding">
        <h2 class="text-module-title font-module-title text-on-surface mb-6">公屏弹幕线索趋势 (Chat Trend)</h2>
        <div class="w-full h-[250px]" id="chatTrendChart"></div>
    </section>

    <!-- Analysis -->
    <section class="grid grid-cols-1 lg:grid-cols-3 gap-gutter">
        <div class="lg:col-span-1 glass-card rounded-xl p-card-padding h-full">
            <h2 class="text-module-title font-module-title text-on-surface mb-4">数据发现 & 业务归因</h2>
            <ul class="space-y-4">
                {findings_html}
            </ul>
        </div>
        <div class="lg:col-span-2 glass-card rounded-xl p-card-padding h-full flex flex-col gap-6">
            <div>
                <label class="block text-body-standard font-body-standard font-bold text-on-surface mb-2">Root Cause Analysis (根因推演)</label>
                <textarea class="w-full h-32 rounded-lg border-outline-variant bg-surface focus:border-primary focus:ring-2 focus:ring-primary-container/20 text-body-standard font-body-standard p-3 resize-none" placeholder="输入核心排查点... 例如：主播话术变更、投流模型调整、商品库下架等"></textarea>
            </div>
            <div>
                <label class="block text-body-standard font-body-standard font-bold text-on-surface mb-2">Action Plan (调整策略)</label>
                <textarea class="w-full h-32 rounded-lg border-outline-variant bg-surface focus:border-primary focus:ring-2 focus:ring-primary-container/20 text-body-standard font-body-standard p-3 resize-none" placeholder="输入下一步计划... 例如：恢复4月高转化话术切片，重启大健康特定产品投流等"></textarea>
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

        // 1. KPI Ring Chart
        const kpiRingChart = echarts.init(document.getElementById('kpiRingChart'));
        kpiRingChart.setOption({{
            tooltip: {{ trigger: 'item' }},
            color: [colors.primary, colors.secondary],
            series: [
                {{
                    type: 'pie',
                    radius: ['60%', '90%'],
                    avoidLabelOverlap: false,
                    label: {{
                        show: true,
                        position: 'center',
                        formatter: function(p) {{
                            return p.name.includes('Health')
                                ? '健康线\\n' + p.percent + '%'
                                : '兴趣变美线\\n' + p.percent + '%';
                        }},
                        fontSize: 13,
                        fontWeight: 'bold',
                        color: function(p) {{
                            return p.name.includes('Health') ? colors.primary : colors.secondary;
                        }}
                    }},
                    labelLine: {{ show: false }},
                    data: [
                        {{ value: chartsData.health_pct, name: '健康线 (Health)' }},
                        {{ value: chartsData.interest_pct, name: '兴趣变美线 (Beauty)' }}
                    ]
                }}
            ]
        }});

        // 2. Main Trend Chart
        const mainTrendChart = echarts.init(document.getElementById('mainTrendChart'));
        const days = Array.from({{length: 31}}, (_, i) => `${{i+1}}日`);
        const marData = Object.values(chartsData.daily_cart['3月']);
        const aprData = Object.values(chartsData.daily_cart['4月']);
        const mayData = Object.values(chartsData.daily_cart['5月']).map((v, i) => i < 15 ? v : null);

        mainTrendChart.setOption({{
            tooltip: {{ trigger: 'axis', backgroundColor: '#fff', textStyle: {{ color: '#191c1e' }}, extraCssText: 'box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);' }},
            legend: {{ data: ['3月 (Mar)', '4月 (Apr)', '5月 (May)'], bottom: 0 }},
            grid: {{ left: '3%', right: '4%', bottom: '10%', top: '5%', containLabel: true }},
            xAxis: {{ type: 'category', boundaryGap: false, data: days, axisLine: {{ lineStyle: {{ color: colors.outline }} }} }},
            yAxis: {{ type: 'value', splitLine: {{ lineStyle: {{ color: colors.surfaceContainerLow }} }} }},
            series: [
                {{
                    name: '3月 (Mar)', type: 'line', data: marData,
                    itemStyle: {{ color: colors.grayMarch }},
                    lineStyle: {{ type: 'dashed', width: 2 }},
                    symbol: 'none'
                }},
                {{
                    name: '4月 (Apr)', type: 'line', data: aprData,
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
                    name: '5月 (May)', type: 'line', data: mayData,
                    itemStyle: {{ color: colors.error }},
                    lineStyle: {{ width: 2 }},
                    areaStyle: {{
                        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                            {{ offset: 0, color: 'rgba(186, 26, 26, 0.2)' }},
                            {{ offset: 1, color: 'rgba(186, 26, 26, 0.0)' }}
                        ])
                    }},
                    symbol: 'circle',
                    symbolSize: 6
                }}
            ]
        }});

        // 3. Team Bar Chart
        const teamBarChart = echarts.init(document.getElementById('teamBarChart'));
        const t3 = chartsData.team_compare['3月'];
        const t4 = chartsData.team_compare['4月'];
        const t5 = chartsData.team_compare['5月'];
        teamBarChart.setOption({{
            tooltip: {{ trigger: 'axis', axisPointer: {{ type: 'shadow' }} }},
            legend: {{ bottom: 0 }},
            grid: {{ left: '3%', right: '4%', bottom: '15%', top: '5%', containLabel: true }},
            xAxis: {{ type: 'category', data: ['3月(1-15)', '4月(1-15)', '5月(1-15)'], axisLine: {{ lineStyle: {{ color: colors.outline }} }} }},
            yAxis: {{ type: 'value', splitLine: {{ lineStyle: {{ color: colors.surfaceContainerLow }} }} }},
            color: [colors.primary, colors.secondary],
            series: [
                {{ name: '健康线 (Health)', type: 'bar', data: [t3['健康线']||0, t4['健康线']||0, t5['健康线']||0], barWidth: '30%', itemStyle: {{ borderRadius: [4,4,0,0] }} }},
                {{ name: '兴趣变美线 (Beauty)', type: 'bar', data: [t3['兴趣变美线']||0, t4['兴趣变美线']||0, t5['兴趣变美线']||0], barWidth: '30%', itemStyle: {{ borderRadius: [4,4,0,0] }} }}
            ]
        }});

        // 4. User Level Chart - percentage stacked
        const userLevelChart = echarts.init(document.getElementById('userLevelChart'));
        const levels = chartsData.all_levels;
        const months = ['3月', '4月', '5月'];
        // 计算每个月各等级的占比
        const levelSeries = [];
        const palette = ['#003751', '#006591', '#0ea5e9', '#89ceff', '#c9e6ff', '#e0e3e5', '#bec8d2', '#94a3b8', '#64748b', '#475569', '#334155'];
        for (let i = 0; i < levels.length; i++) {{
            const lvl = levels[i];
            const pdata = months.map(m => {{
                const total = Object.values(chartsData.level_data[m] || {{}}).reduce((a,b) => a+b, 0);
                const val = (chartsData.level_data[m] || {{}})[lvl] || 0;
                return total ? Math.round(val / total * 100) : 0;
            }});
            levelSeries.push({{
                name: lvl,
                type: 'bar',
                stack: 'total',
                data: pdata,
                itemStyle: {{ color: palette[i % palette.length] }}
            }});
        }}
        userLevelChart.setOption({{
            tooltip: {{ trigger: 'axis', axisPointer: {{ type: 'shadow' }} }},
            legend: {{ bottom: 0, type: 'scroll', textStyle: {{ fontSize: 10 }} }},
            grid: {{ left: '3%', right: '4%', bottom: '18%', top: '5%', containLabel: true }},
            xAxis: {{ type: 'category', data: months, axisLine: {{ lineStyle: {{ color: colors.outline }} }} }},
            yAxis: {{ type: 'value', max: 100, axisLabel: {{ formatter: '{{value}}%' }}, splitLine: {{ lineStyle: {{ color: colors.surfaceContainerLow }} }} }},
            series: levelSeries
        }});

        // 5. Chat Trend Chart
        const chatTrendChart = echarts.init(document.getElementById('chatTrendChart'));
        const dmDays = Array.from({{length: 31}}, (_, i) => `${{i+1}}日`);
        const dmMar = Object.values(chartsData.daily_dm['3月']);
        const dmApr = Object.values(chartsData.daily_dm['4月']);
        const dmMay = Object.values(chartsData.daily_dm['5月']).map((v, i) => i < 15 ? v : null);
        chatTrendChart.setOption({{
            tooltip: {{ trigger: 'axis', backgroundColor: '#fff', textStyle: {{ color: '#191c1e' }} }},
            legend: {{ data: ['3月 (Mar)', '4月 (Apr)', '5月 (May)'], bottom: 0 }},
            grid: {{ left: '3%', right: '4%', bottom: '12%', top: '5%', containLabel: true }},
            xAxis: {{ type: 'category', boundaryGap: false, data: dmDays, axisLine: {{ lineStyle: {{ color: colors.outline }} }} }},
            yAxis: {{ type: 'value', splitLine: {{ lineStyle: {{ color: colors.surfaceContainerLow }} }} }},
            series: [
                {{
                    name: '3月 (Mar)', type: 'line', data: dmMar,
                    itemStyle: {{ color: colors.grayMarch }},
                    lineStyle: {{ type: 'dashed', width: 2 }},
                    symbol: 'none'
                }},
                {{
                    name: '4月 (Apr)', type: 'line', data: dmApr,
                    itemStyle: {{ color: colors.tertiary }},
                    lineStyle: {{ width: 2 }},
                    areaStyle: {{
                        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                            {{ offset: 0, color: 'rgba(109, 59, 215, 0.2)' }},
                            {{ offset: 1, color: 'rgba(109, 59, 215, 0.0)' }}
                        ])
                    }},
                    symbol: 'none'
                }},
                {{
                    name: '5月 (May)', type: 'line', data: dmMay,
                    itemStyle: {{ color: colors.error }},
                    lineStyle: {{ width: 2 }},
                    symbol: 'circle',
                    symbolSize: 6
                }}
            ]
        }});

        window.addEventListener('resize', function() {{
            kpiRingChart.resize();
            mainTrendChart.resize();
            teamBarChart.resize();
            userLevelChart.resize();
            chatTrendChart.resize();
        }});
    }});
</script>
</body>
</html>
'''

with open('dashboard.html', 'w', encoding='utf-8') as f:
    f.write(html)

print("dashboard.html 已生成")

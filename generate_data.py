"""
数据生成脚本（多维表直连版）
==================
功能：
1. 从飞书多维表格读取所有线索明细
2. 按月/天/品类/团队等维度汇总
3. 输出 dashboard_data.json（供 generate_dashboard.py 使用）

使用方法：
    python generate_data.py
"""

import json
import sys
import os
from collections import defaultdict
from datetime import datetime

# 加载飞书配置
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'feishu_agent'))
try:
    from config_local import (APP_ID, APP_SECRET, BITABLE_APP_TOKEN, BITABLE_TABLE_ID,
                               SCHEDULE_APP_TOKEN, SCHEDULE_TABLE_ID)
except ImportError:
    from config import (APP_ID, APP_SECRET, BITABLE_APP_TOKEN, BITABLE_TABLE_ID,
                         SCHEDULE_APP_TOKEN, SCHEDULE_TABLE_ID)

from feishu_client import FeishuClient

# ========== 品类规范化（复用 deep_dive_analysis.py） ==========
STANDARD_CATS = [
    "健康营养", "太极", "五禽戏", "睡眠调理", "气血调理", "固气活血", "君合太极",
    "开心太极", "内养太极", "云帆太极", "东方食养", "古法居家养生", "华佗肩颈舒活功",
    "健康家厨", "健康食养", "儿童健康", "食养助长", "体质食养", "易筋经", "营养调理",
    "中式美食制作", "轻训营", "亚健康管理", "私域",
    "普拉提", "瑜伽", "中医变美", "穿搭", "懒人吃瘦", "面部瑜伽驻颜", "逆龄女神瑜伽",
    "逆龄普拉提", "女性保养瑜伽", "东方养正瑜伽", "塑形流瑜伽", "体态", "体态塑形瑜伽",
    "形体芭蕾", "养正变美", "一杰瑜伽", "正位塑形瑜伽", "瑜伽会员",
    "手机摄影", "摄影美学", "唱歌", "短视频", "风光摄影", "相机摄影", "声乐", "国际声乐",
    "电子琴", "键盘乐", "真书法", "油画", "国画", "国学朗诵", "戏曲", "舞蹈", "优雅舞蹈",
    "茶道", "编织工艺美学", "钩针编织美学", "美学收纳",
    "中医瑜伽", "面部驻颜瑜伽",
]

CAT_ALIASES = {
    "居家古法": "古法居家养生",
    "气血": "气血调理",
    "睡眠": "睡眠调理",
    "五禽戏晨练": "五禽戏",
    "普拉提晨练": "普拉提",
    "瑜伽晨练": "瑜伽",
    "君合太极晨练": "君合太极",
    "逆龄女神瑜伽晨练": "逆龄女神瑜伽",
    "东方养正瑜伽晨练": "东方养正瑜伽",
    "一杰晨练": "一杰瑜伽",
    "晨练焕醒计划": "晨练",
    "节气养正公开课": "节气养正",
    "老师，请回答！": "健康营养",
    "才艺名师公开课": "才艺",
    "元气干货分享课": "元气干货",
    "中医瑜伽-陈浙南": "中医瑜伽",
    "瑜伽：杨淇": "瑜伽",
    "固气": "固气活血",
    "亚健康": "亚健康管理",
    "姚国诚单人": "古法居家养生",
    "古法居家姚国诚": "古法居家养生",
    "4.9姚国诚单人": "古法居家养生",
    "陈浙南0元新体验营": "中医瑜伽",
    "王溪0元（新栏目）": "中医变美",
    "写作课": "健康营养",
    "朗诵IP": "国学朗诵",
    "编织-0元": "编织工艺美学",
    "影像一点通": "摄影美学",
    "魏巍异地": "普拉提",
    "收纳，不需要剪辑": "美学收纳",
    "2026.4.2唐一杰": "一杰瑜伽",
}


def normalize_category(name):
    """品类规范化"""
    if not name:
        return None
    name = str(name).strip()
    # 1. 精确匹配
    if name in STANDARD_CATS:
        return name
    # 2. 别名匹配
    if name in CAT_ALIASES:
        return CAT_ALIASES[name]
    # 3. 去除常见后缀
    for suffix in ["晨练", "带练", "公开课", "直播", "IP", "大赛"]:
        if name.endswith(suffix):
            base = name[: -len(suffix)].strip()
            if base in STANDARD_CATS:
                return base
            if base in CAT_ALIASES:
                return CAT_ALIASES[base]
    # 4. 子串包含匹配（优先最长）
    for cat in sorted(STANDARD_CATS, key=len, reverse=True):
        if cat in name:
            return cat
    for alias in sorted(CAT_ALIASES.keys(), key=len, reverse=True):
        if alias in name:
            return CAT_ALIASES[alias]
    return name


def _parse_datetime_field(fields, *field_names):
    """尝试从多个字段名中解析日期时间"""
    for name in field_names:
        val = fields.get(name)
        if val is None:
            continue
        if isinstance(val, (int, float)):
            return datetime.fromtimestamp(val / 1000)
        # 字符串日期
        if isinstance(val, str):
            for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%Y/%m/%d %H:%M:%S", "%Y/%m/%d"):
                try:
                    return datetime.strptime(val, fmt)
                except ValueError:
                    pass
    return None


def fetch_all_records(client: FeishuClient, app_token: str, table_id: str):
    """从多维表读取所有明细记录（兼容不同字段结构）"""
    records = client.query_records(app_token, table_id, page_size=500)
    print(f"✅ 从多维表读取 {len(records)} 条明细记录")

    if not records:
        return []

    # 探测实际字段名
    sample_fields = records[0].get("fields", {})
    has_example_time = "例子时间" in sample_fields
    has_date = "日期" in sample_fields
    has_stats_month = "统计月" in sample_fields

    rows = []
    for rec in records:
        fields = rec.get("fields", {})

        # 解析日期时间
        if has_example_time:
            dt = _parse_datetime_field(fields, "例子时间")
        elif has_date:
            dt = _parse_datetime_field(fields, "日期")
        else:
            dt = None

        if not dt:
            continue

        # 统计月（从日期推断或读取字段）
        if has_stats_month:
            month_label = fields.get("统计月", "")
        else:
            month_label = f"{dt.month}月"

        rows.append({
            "统计月": month_label,
            "例子时间": dt,
            "例子日期": dt.date(),
            "例子日": dt.day,
            "一级渠道": fields.get("一级渠道", ""),
            "二级渠道": fields.get("二级渠道", ""),
            "三级渠道": fields.get("三级渠道", ""),
            "一级团队": fields.get("一级团队", ""),
            "二级团队": fields.get("二级团队", ""),
            "三级团队": fields.get("三级团队", ""),
            "品类": fields.get("品类", ""),
            "品类名": fields.get("品类名", ""),
            "老师名": fields.get("老师名", ""),
            "训练营id": fields.get("训练营id", 0),
            "训练营名": fields.get("训练营名", ""),
            "订单id": fields.get("订单id", 0),
            "用户id": fields.get("用户id", 0),
            "会员等级": fields.get("会员等级", ""),
            "渠道参": fields.get("渠道参", ""),
            "渠道名": fields.get("渠道名", ""),
            "付费类型": fields.get("付费类型", ""),
            "sku_id": fields.get("sku_id", 0),
            "sku名称": fields.get("sku名称", ""),
            "开营时间": fields.get("开营时间", None),
            "结营时间": fields.get("结营时间", None),
            "首单时间": fields.get("首单时间", None),
            "投手id": fields.get("投手id", 0),
            "投手名称": fields.get("投手名称", ""),
            "投手部门": fields.get("投手部门", ""),
            "例子价格": fields.get("例子价格", 0),
            "首单流水": fields.get("首单流水", 0),
        })
    return rows


def fetch_schedule_records(client: FeishuClient, app_token: str, table_id: str):
    """从排期多维表读取所有排期记录"""
    if not app_token or not table_id:
        print("   ⚠️ 未配置排期多维表，跳过排期读取")
        return []

    records = client.query_records(app_token, table_id, page_size=500)
    print(f"   ✅ 从排期多维表读取 {len(records)} 条排期记录")

    rows = []
    for rec in records:
        fields = rec.get("fields", {})

        # 解析日期（飞书日期字段是毫秒时间戳）
        ts = fields.get("日期")
        if isinstance(ts, (int, float)):
            dt = datetime.fromtimestamp(ts / 1000)
        else:
            continue

        # 解析曝光量级
        exp = fields.get("曝光量级", 0)
        if isinstance(exp, (int, float)):
            exposure = int(exp)
        else:
            exposure = 0

        rows.append({
            "日期": dt,
            "月份": fields.get("月份", dt.strftime("%m月").lstrip("0")),
            "品类": fields.get("品类", ""),
            "直播名": fields.get("直播名", ""),
            "时段": fields.get("时段", ""),
            "曝光量级": exposure,
            "标记": fields.get("标记", ""),
            "线级": fields.get("线级", ""),
            "文案负责人": fields.get("文案负责人", ""),
            "所属周次": fields.get("所属周次", ""),
            "时间": fields.get("时间", ""),
        })
    return rows


def build_schedule_correlation(leads_rows, schedule_rows):
    """基于线索明细 + 排期明细生成 schedule_correlation"""
    if not schedule_rows:
        print("   ⚠️ 无排期数据，跳过排期关联分析")
        return None

    # 排期数据按日期+品类索引（品类名规范化）
    schedule_by_date = {}  # date_str -> {norm_cat}
    exposure_by_date_cat = {}  # (date_str, norm_cat) -> int
    schedule_counts = {}   # month -> norm_cat -> count

    for r in schedule_rows:
        cat = normalize_category(r["品类"])
        if not cat:
            continue
        date_str = r["日期"].strftime("%Y-%m-%d")
        month_key = r["月份"]

        if date_str not in schedule_by_date:
            schedule_by_date[date_str] = set()
        schedule_by_date[date_str].add(cat)

        exposure_by_date_cat[(date_str, cat)] = exposure_by_date_cat.get((date_str, cat), 0) + r["曝光量级"]

        if month_key not in schedule_counts:
            schedule_counts[month_key] = {}
        schedule_counts[month_key][cat] = schedule_counts[month_key].get(cat, 0) + 1

    # 线索数据按月份+品类+日期索引（品类名规范化）
    cart_rows = [r for r in leads_rows if r["三级团队"] == "直播间购物车"]

    # 收集所有品类（规范化后）
    all_cats = set(normalize_category(r["品类名"]) for r in cart_rows if r["品类名"])
    # 移除未规范化的 None
    all_cats = {c for c in all_cats if c}

    results = []
    for cat in all_cats:
        # 4月线索（1-15号）
        apr_leads = sum(1 for r in cart_rows
                        if normalize_category(r["品类名"]) == cat and r["统计月"] == "4月" and r["例子日"] <= 15)
        # 5月线索（1-15号）
        may_leads = sum(1 for r in cart_rows
                        if normalize_category(r["品类名"]) == cat and r["统计月"] == "5月" and r["例子日"] <= 15)

        # 排期场次
        apr_schedule_count = schedule_counts.get("4月", {}).get(cat, 0)
        may_schedule_count = schedule_counts.get("5月", {}).get(cat, 0)

        # 5月是否排期
        may_scheduled = any(cat in schedule_by_date.get(d, set())
                            for d in [f"2026-05-{day:02d}" for day in range(1, 16)])

        # 5月曝光（该品类在5月1-15日所有排期的曝光总和）
        may_exposure = 0
        for day in range(1, 16):
            d = f"2026-05-{day:02d}"
            if cat in schedule_by_date.get(d, set()):
                may_exposure += exposure_by_date_cat.get((d, cat), 0)

        # 转化率 = 线索 / 曝光 * 10000
        conversion = round(may_leads / may_exposure * 10000, 1) if may_exposure > 0 else 0

        # 线索/场次
        apr_leads_per_show = round(apr_leads / apr_schedule_count, 1) if apr_schedule_count > 0 else 0
        may_leads_per_show = round(may_leads / may_schedule_count, 1) if may_schedule_count > 0 else 0

        # 判断暴跌原因
        if may_schedule_count == 0 and apr_schedule_count > 0:
            drop_reason = "排期问题（未排期）"
        elif may_schedule_count < apr_schedule_count and may_leads_per_show >= apr_leads_per_show * 0.8:
            drop_reason = "排期问题（场次减少）"
        elif may_schedule_count > 0 and may_leads_per_show < apr_leads_per_show * 0.7:
            drop_reason = "转化问题（每场线索暴跌）"
        else:
            drop_reason = "待分析"

        # 状态
        if may_leads == 0 and apr_leads >= 10:
            status = "🔴 未播或播了无人领"
        elif may_leads == 0:
            status = "➖ 无数据"
        elif may_scheduled and may_exposure > 0 and conversion < 1:
            status = "🟡 播了但转化率极低"
        elif may_scheduled:
            status = "🟢 正常"
        else:
            status = "⚪ 自然流量"

        results.append({
            "品类": cat,
            "4月线索": apr_leads,
            "5月线索": may_leads,
            "4月排期": apr_schedule_count,
            "5月排期": may_schedule_count,
            "5月排期_bool": may_scheduled,
            "5月曝光": may_exposure,
            "线索/场次_4月": apr_leads_per_show,
            "线索/场次_5月": may_leads_per_show,
            "转化率": conversion,
            "暴跌原因": drop_reason,
            "状态": status,
        })

    # 按4月线索降序
    results.sort(key=lambda x: x["4月线索"], reverse=True)

    not_scheduled = [r for r in results if not r["5月排期_bool"] and r["4月线索"] >= 20]
    low_conversion = [r for r in results if r["状态"] == "🟡 播了但转化率极低"]

    drop_reasons = {}
    for r in results:
        if r["暴跌原因"] != "待分析":
            drop_reasons.setdefault(r["暴跌原因"], []).append(r)

    print(f"   ✅ 排期关联分析完成：{len(results)} 个品类，未排期 {len(not_scheduled)} 个")

    return {
        "cat_schedule": results[:30],
        "not_scheduled": not_scheduled[:10],
        "low_conversion": low_conversion[:10],
        "drop_reasons": drop_reasons,
    }


def generate_dashboard_data(rows, schedule_rows=None):
    """基于明细记录生成 dashboard_data.json"""

    # 按月分组
    monthly_rows = defaultdict(list)
    for r in rows:
        month_key = r["统计月"] if r["统计月"] else r["例子时间"].strftime("%Y-%m")
        monthly_rows[month_key].append(r)

    # 如果统计月为空，用日期推断
    if len(monthly_rows) == 1 and "" in monthly_rows:
        # 按日期重新分组
        monthly_rows = defaultdict(list)
        for r in rows:
            m = r["例子时间"].strftime("%Y-%m")
            monthly_rows[m].append(r)

    # 标准化月份名称（3月、4月、5月）
    month_alias = {}
    for m in sorted(monthly_rows.keys()):
        # 从 YYYY-MM 提取月份数字
        try:
            month_num = int(m.split("-")[1])
            month_alias[m] = f"{month_num}月"
        except:
            month_alias[m] = m

    # 1. 购物车/弹幕按月总量
    total_stats = {}
    for m, alias in month_alias.items():
        df = monthly_rows[m]
        cart = [r for r in df if r["三级团队"] == "直播间购物车"]
        dm = [r for r in df if r["三级团队"] == "直播间弹幕"]
        total_stats[alias] = {
            "购物车": len(cart),
            "弹幕": len(dm),
        }

    # 2. 购物车日趋势（整月按天）
    daily_cart = {}
    for m, alias in month_alias.items():
        df = monthly_rows[m]
        cart = [r for r in df if r["三级团队"] == "直播间购物车"]
        daily = defaultdict(int)
        for r in cart:
            daily[r["例子日"]] += 1
        daily_cart[alias] = {str(d): int(daily.get(d, 0)) for d in range(1, 32)}

    # 3. 弹幕日趋势
    daily_dm = {}
    for m, alias in month_alias.items():
        df = monthly_rows[m]
        dm = [r for r in df if r["三级团队"] == "直播间弹幕"]
        daily = defaultdict(int)
        for r in dm:
            daily[r["例子日"]] += 1
        daily_dm[alias] = {str(d): int(daily.get(d, 0)) for d in range(1, 32)}

    # 4. 二级团队1-15号同期对比
    team_compare = {}
    for m, alias in month_alias.items():
        df = monthly_rows[m]
        cart = [r for r in df if r["三级团队"] == "直播间购物车" and r["例子日"] <= 15]
        team = defaultdict(int)
        for r in cart:
            team[r["二级团队"]] += 1
        team_compare[alias] = {k: int(v) for k, v in team.items()}

    # 5. 品类下钻数据（1-15号）
    cat_data = []
    all_cats = set()
    cat_team_map = {}

    for m, alias in month_alias.items():
        df = monthly_rows[m]
        cart = [r for r in df if r["三级团队"] == "直播间购物车" and r["例子日"] <= 15]
        for r in cart:
            cat = r["品类名"]
            team = r["二级团队"]
            all_cats.add(cat)
            cat_team_map[cat] = team

    for cat in sorted(all_cats):
        team = cat_team_map.get(cat, "未知")
        counts = {}
        for m, alias in month_alias.items():
            df = monthly_rows[m]
            cart = [r for r in df if r["三级团队"] == "直播间购物车" and r["例子日"] <= 15]
            cnt = len([r for r in cart if r["品类名"] == cat])
            counts[alias] = cnt

        # 获取连续三个月的数据（假设最多3个月）
        months = sorted(counts.keys())
        c3 = counts.get(months[0], 0) if len(months) > 0 else 0
        c4 = counts.get(months[1], 0) if len(months) > 1 else 0
        c5 = counts.get(months[2], 0) if len(months) > 2 else 0

        # 计算状态（以最近两个月对比）
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

        cat_data.append({
            "品类": cat,
            "二级团队": team,
            "3月": c3,
            "4月": c4,
            "5月": c5,
            "环比": change,
            "状态": status,
        })

    # 按4月降序排
    cat_data.sort(key=lambda x: x["4月"], reverse=True)

    # 6. 会员等级占比变化（整月购物车）
    level_data = {}
    all_levels = set()
    for m, alias in month_alias.items():
        df = monthly_rows[m]
        cart = [r for r in df if r["三级团队"] == "直播间购物车"]
        levels = defaultdict(int)
        for r in cart:
            levels[r["会员等级"]] += 1
        level_data[alias] = {k: int(v) for k, v in levels.items()}
        all_levels.update(levels.keys())

    # 7. 关键发现清单
    findings = []
    # 消失的品类
    for c in cat_data:
        if c["状态"] == "消失":
            findings.append({
                "severity": "high",
                "text": f"{c['品类']} 4月{c['4月']}条→5月直接消失（未排期）",
            })
    # 暴跌的品类
    for c in cat_data:
        if c["状态"] == "暴跌":
            findings.append({
                "severity": "high",
                "text": f"{c['品类']} 4月{c['4月']}条→5月{c['5月']}条（跌幅{c['环比']}%）",
            })

    # 团队波动
    months = sorted(total_stats.keys())
    if len(months) >= 3:
        m1, m2, m3 = months[0], months[1], months[2]
        health_1 = team_compare.get(m1, {}).get("健康线", 0)
        health_2 = team_compare.get(m2, {}).get("健康线", 0)
        health_3 = team_compare.get(m3, {}).get("健康线", 0)
        interest_1 = team_compare.get(m1, {}).get("兴趣变美线", 0)
        interest_2 = team_compare.get(m2, {}).get("兴趣变美线", 0)
        interest_3 = team_compare.get(m3, {}).get("兴趣变美线", 0)

        if health_2 > 0:
            h_change = round((health_3 - health_2) / health_2 * 100, 1)
            findings.append({
                "severity": "medium",
                "text": f"健康线同期波动剧烈：4月较3月+{round((health_2 - health_1) / health_1 * 100, 0):.0f}%，5月较4月{h_change}%",
            })

        if interest_2 > 0:
            i_change = round((interest_3 - interest_2) / interest_2 * 100, 1)
            findings.append({
                "severity": "low",
                "text": f"兴趣变美线相对稳定：5月较4月{i_change}%",
            })

    # 8. 排期关联分析（如果提供了排期数据）
    schedule_correlation = None
    if schedule_rows:
        print("\n🔗 排期关联分析 ...")
        schedule_correlation = build_schedule_correlation(rows, schedule_rows)

    # 汇总输出
    data = {
        "generated_at": datetime.now().isoformat(),
        "total_stats": total_stats,
        "daily_cart": daily_cart,
        "daily_dm": daily_dm,
        "team_compare": team_compare,
        "cat_data": cat_data,
        "level_data": level_data,
        "all_levels": sorted(list(all_levels)),
        "findings": findings,
    }
    if schedule_correlation:
        data["schedule_correlation"] = schedule_correlation

    return data


def main():
    print("=" * 50)
    print("数据生成（多维表直连版）")
    print("=" * 50)

    if not APP_ID or APP_ID.startswith("cli_xxxxxxxx") or not APP_SECRET:
        print("\n❌ 错误：请先配置 feishu_agent/config_local.py")
        print("   填入 BITABLE_APP_TOKEN、BITABLE_TABLE_ID、APP_ID、APP_SECRET")
        sys.exit(1)

    # 1. 连接飞书
    print("\n📡 连接飞书多维表 ...")
    client = FeishuClient(APP_ID, APP_SECRET)

    # 2. 读取线索明细
    print("\n📥 读取线索明细 ...")
    rows = fetch_all_records(client, BITABLE_APP_TOKEN, BITABLE_TABLE_ID)

    if not rows:
        print("❌ 多维表中没有数据")
        sys.exit(1)

    # 3. 读取排期明细（可选）
    schedule_rows = []
    if SCHEDULE_APP_TOKEN and SCHEDULE_TABLE_ID:
        print("\n📅 读取排期明细 ...")
        schedule_rows = fetch_schedule_records(client, SCHEDULE_APP_TOKEN, SCHEDULE_TABLE_ID)
    else:
        print("\n   ℹ️ 未配置排期多维表（SCHEDULE_APP_TOKEN / SCHEDULE_TABLE_ID），跳过排期读取")
        print("   如需排期关联分析，请先运行: python feishu_agent/setup_schedule_bitable.py")

    # 4. 生成汇总数据
    print("\n🔧 生成 dashboard_data.json ...")
    data = generate_dashboard_data(rows, schedule_rows)

    # 5. 保留现有 dashboard_data.json 中的额外字段（如高级分析模块）
    if os.path.exists("dashboard_data.json"):
        try:
            with open("dashboard_data.json", "r", encoding="utf-8") as f:
                existing = json.load(f)
            # 保留旧数据中独有的字段
            preserve_keys = [
                "high_value_cats", "pareto", "core_answer",
                "member_levels", "channel_trends", "holiday_effect", "weekday_pattern",
                "target_tracking", "team_health_analysis", "member_category_cross"
            ]
            for key in preserve_keys:
                if key in existing and key not in data:
                    data[key] = existing[key]
                    print(f"   ℹ️ 保留现有字段: {key}")
        except Exception as e:
            print(f"   ⚠️ 读取旧 dashboard_data.json 失败: {e}")

    # 6. 写入文件
    with open("dashboard_data.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print("\n" + "=" * 50)
    print("✅ 数据已生成到 dashboard_data.json")
    print(f"   品类数: {len(data['cat_data'])}")
    print(f"   关键发现: {len(data['findings'])}")
    print(f"   月份: {sorted(data['total_stats'].keys())}")
    print("=" * 50)


if __name__ == "__main__":
    main()

"""
深度归因分析脚本
================
读取3-5月原始线索数据 + 排期表 + 直播明细表
输出增强版 dashboard_data.json

核心问题：
1. 5月下跌是"高LTV高线索品类消失"导致的，还是"所有品类均匀下跌"导致的？
2. 会员等级维度：高价值用户 vs 新用户占比变化
3. 弹幕vs购物车趋势是否一致
4. 假期效应
5. 帕累托集中度
6. 排期关联：播没播 + 线索/曝光转化率
"""

import pandas as pd
import json
import re
import os
from collections import defaultdict
from datetime import datetime, timedelta

# ============ 配置 ============
# 同期对比截止日（5月数据更新到18号，4月同期也取1-18号）
CUTOFF_DAY = 18
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
EXCEL_FILES = {
    "3月": os.path.join(BASE_DIR, "3月直播间数据分析.xlsx"),
    "4月": os.path.join(BASE_DIR, "4月直播间数据分析.xlsx"),
    "5月": os.path.join(BASE_DIR, "直播间5月19日数据分析.xlsx"),
}
SCHEDULE_FILE = os.path.join(BASE_DIR, "../直播间排期策略/平台私域直播线宣发排期（新）.xlsx")
DETAIL_FILE = os.path.join(BASE_DIR, "直播明细表（仅供参考）.xlsx")
OUTPUT_JSON = os.path.join(BASE_DIR, "dashboard_data.json")

# 标准品类列表（从PRD提取关键品类）
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

# 品类别名映射
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
}


def normalize_category(name):
    """品类规范化"""
    if pd.isna(name):
        return None
    name = str(name).strip()
    # 1. 精确匹配标准名
    if name in STANDARD_CATS:
        return name
    # 2. 别名匹配
    if name in CAT_ALIASES:
        return CAT_ALIASES[name]
    # 3. 去除常见后缀
    for suffix in ["晨练", "带练", "公开课", "直播"]:
        if name.endswith(suffix):
            base = name[: -len(suffix)].strip()
            if base in STANDARD_CATS:
                return base
            if base in CAT_ALIASES:
                return CAT_ALIASES[base]
    # 4. 联合直播拆分
    for sep in [" + ", " x ", " X ", " × ", "+", "x", "X", "×"]:
        if sep in name:
            parts = [p.strip() for p in name.split(sep)]
            # 返回主品类（第一部分）
            main = normalize_category(parts[0])
            if main:
                return main
    # 5. 前缀匹配（等级变体）
    for cat in sorted(STANDARD_CATS, key=len, reverse=True):
        if name.startswith(cat):
            return cat
    # 6. 子串包含匹配
    for cat in sorted(STANDARD_CATS, key=len, reverse=True):
        if cat in name:
            return cat
    return name


def load_all_data():
    """加载3-5月所有线索数据"""
    all_dfs = []
    for month_label, path in EXCEL_FILES.items():
        print(f"📖 读取 {month_label} 数据 ...")
        df = pd.read_excel(path, sheet_name="明细")
        df["例子时间"] = pd.to_datetime(df["例子时间"], errors="coerce")
        df = df[df["例子时间"].notna()].copy()
        df["月份"] = month_label
        df["日期"] = df["例子时间"].dt.date
        df["day"] = df["例子时间"].dt.day
        df["hour"] = df["例子时间"].dt.hour
        df["weekday"] = df["例子时间"].dt.weekday  # 0=周一
        df["weekday_name"] = df["例子时间"].dt.day_name()
        df["品类_norm"] = df["品类名"].apply(normalize_category)

        # 场次判断
        def get_slot(h):
            if 5 <= h <= 11:
                return "早间"
            elif 18 <= h <= 23:
                return "晚间"
            else:
                return "其他"

        df["场次"] = df["hour"].apply(get_slot)
        all_dfs.append(df)
        print(f"   ✅ {len(df)} 条记录")

    df_all = pd.concat(all_dfs, ignore_index=True)
    print(f"\n📊 总计 {len(df_all)} 条线索记录")
    return df_all


def analyze_category_trends(df_all):
    """品类级分析：线索数、首单流水、LTV、占比趋势"""
    print("\n🔬 品类级归因分析 ...")
    cart_df = df_all[df_all["三级团队"] == "直播间购物车"].copy()

    # 按月+品类汇总
    cat_monthly = []
    for month in ["3月", "4月", "5月"]:
        m_df = cart_df[cart_df["月份"] == month]
        # 只取1-CUTOFF_DAY号做同期对比
        m_df = m_df[m_df["day"] <= CUTOFF_DAY]

        for cat in m_df["品类_norm"].dropna().unique():
            sub = m_df[m_df["品类_norm"] == cat]
            leads = len(sub)
            gmv = sub[sub["首单流水"].notna()]["首单流水"].sum()
            ltv = gmv / leads if leads > 0 else 0
            # 首单数
            first_orders = sub[sub["首单流水"].notna() & (sub["首单流水"] > 0)]["首单流水"].count()
            conversion = first_orders / leads if leads > 0 else 0

            cat_monthly.append({
                "月份": month,
                "品类": cat,
                "线索数": int(leads),
                "首单流水": float(gmv),
                "首单数": int(first_orders),
                "首单转化率": round(conversion * 100, 2),
                "LTV": round(ltv, 1),
                "二级团队": sub["二级团队"].mode().iloc[0] if len(sub) > 0 else "未知",
            })

    cat_df = pd.DataFrame(cat_monthly)

    # 计算占比和变化
    total_by_month = cat_df.groupby("月份")["线索数"].sum().to_dict()
    cat_df["线索占比"] = cat_df.apply(lambda r: round(r["线索数"] / total_by_month.get(r["月份"], 1) * 100, 2), axis=1)

    # 透视：品类 x 月份
    pivot = cat_df.pivot(index="品类", columns="月份", values="线索数").fillna(0)
    for m in ["3月", "4月", "5月"]:
        if m not in pivot.columns:
            pivot[m] = 0

    # 计算状态标签
    results = []
    for cat in pivot.index:
        c3 = int(pivot.loc[cat, "3月"])
        c4 = int(pivot.loc[cat, "4月"])
        c5 = int(pivot.loc[cat, "5月"])

        # 状态判断（基于4月→5月变化，因为4月是最近完整月）
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

        # 获取4月LTV（最完整）
        ltv_row = cat_df[(cat_df["品类"] == cat) & (cat_df["月份"] == "4月")]
        ltv = ltv_row["LTV"].iloc[0] if len(ltv_row) > 0 else 0
        team = ltv_row["二级团队"].iloc[0] if len(ltv_row) > 0 else "未知"

        results.append({
            "品类": cat,
            "二级团队": team,
            "3月(1-15)": c3,
            "4月(1-15)": c4,
            "5月(1-15)": c5,
            "环比": change,
            "状态": status,
            "4月LTV": ltv,
        })

    # 按4月线索数降序
    results.sort(key=lambda x: x["4月(1-15)"], reverse=True)

    # 帕累托分析：TOP5品类集中度
    top5_4 = sorted([r for r in results if r["4月(1-15)"] > 0], key=lambda x: x["4月(1-15)"], reverse=True)[:5]
    top5_sum_4 = sum(r["4月(1-15)"] for r in top5_4)
    total_4 = sum(r["4月(1-15)"] for r in results)
    pareto_4 = round(top5_sum_4 / total_4 * 100, 1) if total_4 > 0 else 0

    top5_5 = sorted([r for r in results if r["5月(1-15)"] > 0], key=lambda x: x["5月(1-15)"], reverse=True)[:5]
    top5_sum_5 = sum(r["5月(1-15)"] for r in top5_5)
    total_5 = sum(r["5月(1-15)"] for r in results)
    pareto_5 = round(top5_sum_5 / total_5 * 100, 1) if total_5 > 0 else 0

    print(f"   4月 TOP5 集中度: {pareto_4}%")
    print(f"   5月 TOP5 集中度: {pareto_5}%")

    # 高LTV高线索品类（4月）
    high_value = [r for r in results if r["4月(1-15)"] >= 50 and r["4月LTV"] >= 80]
    high_value.sort(key=lambda x: x["4月(1-15)"] * x["4月LTV"], reverse=True)

    # 关键发现
    findings = []
    disappeared = [r for r in results if r["状态"] == "消失" and r["4月(1-15)"] >= 20]
    crashed = [r for r in results if r["状态"] == "暴跌" and r["4月(1-15)"] >= 50]

    for r in disappeared[:5]:
        findings.append({
            "severity": "high",
            "text": f"{r['品类']} 4月{r['4月(1-15)']}条→5月消失（未排期），LTV¥{r['4月LTV']}",
        })
    for r in crashed[:5]:
        findings.append({
            "severity": "high",
            "text": f"{r['品类']} 4月{r['4月(1-15)']}条→5月{r['5月(1-15)']}条（跌幅{r['环比']}%），LTV¥{r['4月LTV']}",
        })

    # 回答核心问题
    disappeared_loss = sum(r["4月(1-15)"] for r in disappeared)
    crashed_loss = sum(r["4月(1-15)"] - r["5月(1-15)"] for r in crashed)
    total_loss = total_4 - total_5

    if total_loss > 0:
        disappeared_pct = round(disappeared_loss / total_loss * 100, 1)
        crashed_pct = round(crashed_loss / total_loss * 100, 1)
    else:
        disappeared_pct = 0
        crashed_pct = 0

    # 暴跌品类一句话总结
    crashed_summary = "、".join([
        f"{r['品类']}({r['4月(1-15)']}→{r['5月(1-15)']}条)"
        for r in crashed[:3]
    ])

    findings.insert(0, {
        "severity": "high",
        "text": f"核心归因：5月较4月同期购物车线索跌{total_loss}条。其中{disappeared_pct}%由消失品类导致，{crashed_pct}%由暴跌品类导致。暴跌主力：{crashed_summary}。",
    })

    print(f"   消失品类贡献跌幅: {disappeared_pct}%")
    print(f"   暴跌品类贡献跌幅: {crashed_pct}%")
    print(f"   暴跌主力: {crashed_summary}")

    return {
        "cat_data": results,
        "high_value_cats": high_value[:10],
        "pareto": {
            "4月": {"top5_sum": top5_sum_4, "total": total_4, "集中度": pareto_4},
            "5月": {"top5_sum": top5_sum_5, "total": total_5, "集中度": pareto_5},
        },
        "findings": findings,
        "core_answer": {
            "total_loss": int(total_loss),
            "disappeared_pct": disappeared_pct,
            "crashed_pct": crashed_pct,
            "uniform_drop": disappeared_pct + crashed_pct < 50,
            "crashed_cats_detail": [
                {
                    "品类": r["品类"],
                    "4月": r["4月(1-15)"],
                    "5月": r["5月(1-15)"],
                    "环比": r["环比"],
                    "LTV": r["4月LTV"],
                }
                for r in crashed[:5]
            ],
        },
    }


def analyze_member_levels(df_all):
    """会员等级维度分析"""
    print("\n👑 会员等级维度分析 ...")
    cart_df = df_all[df_all["三级团队"] == "直播间购物车"].copy()

    # 简化等级分组
    def level_group(lvl):
        if pd.isna(lvl):
            return "未知"
        lvl_str = str(lvl)
        if "V0" in lvl_str or "V1" in lvl_str:
            return "V0-V1 新用户"
        elif "V2" in lvl_str or "V3" in lvl_str or "V4" in lvl_str or "V5" in lvl_str or "V6" in lvl_str:
            return "V2-V6 普通会员"
        elif "V7" in lvl_str or "V8" in lvl_str or "V9" in lvl_str or "V10" in lvl_str:
            return "V7-V10 高价值"
        return "未知"

    cart_df["等级分组"] = cart_df["会员等级"].apply(level_group)

    results = {}
    for month in ["3月", "4月", "5月"]:
        m_df = cart_df[cart_df["月份"] == month]
        m_df = m_df[m_df["day"] <= CUTOFF_DAY]

        total = len(m_df)
        groups = m_df["等级分组"].value_counts().to_dict()
        pct = {k: round(v / total * 100, 1) if total > 0 else 0 for k, v in groups.items()}
        results[month] = {
            "total": int(total),
            "groups": {k: int(v) for k, v in groups.items()},
            "pct": pct,
        }

    # 判断高价值用户是否下跌
    v7_4 = results.get("4月", {}).get("groups", {}).get("V7-V10 高价值", 0)
    v7_5 = results.get("5月", {}).get("groups", {}).get("V7-V10 高价值", 0)
    v0_4 = results.get("4月", {}).get("groups", {}).get("V0-V1 新用户", 0)
    v0_5 = results.get("5月", {}).get("groups", {}).get("V0-V1 新用户", 0)

    print(f"   4月 V7-V10: {v7_4} ({results.get('4月', {}).get('pct', {}).get('V7-V10 高价值', 0)}%)")
    print(f"   5月 V7-V10: {v7_5} ({results.get('5月', {}).get('pct', {}).get('V7-V10 高价值', 0)}%)")
    print(f"   4月 V0-V1: {v0_4} ({results.get('4月', {}).get('pct', {}).get('V0-V1 新用户', 0)}%)")
    print(f"   5月 V0-V1: {v0_5} ({results.get('5月', {}).get('pct', {}).get('V0-V1 新用户', 0)}%)")

    return results


def analyze_channel_trends(df_all):
    """弹幕 vs 购物车趋势对比"""
    print("\n📺 渠道趋势对比 ...")
    results = {}
    for month in ["3月", "4月", "5月"]:
        m_df = df_all[df_all["月份"] == month]
        m_df = m_df[m_df["day"] <= CUTOFF_DAY]

        cart = len(m_df[m_df["三级团队"] == "直播间购物车"])
        dm = len(m_df[m_df["三级团队"] == "直播间弹幕"])
        results[month] = {"购物车": cart, "弹幕": dm, "total": cart + dm}

    # 环比
    cart_4 = results["4月"]["购物车"]
    cart_5 = results["5月"]["购物车"]
    dm_4 = results["4月"]["弹幕"]
    dm_5 = results["5月"]["弹幕"]

    cart_change = round((cart_5 - cart_4) / cart_4 * 100, 1) if cart_4 > 0 else 0
    dm_change = round((dm_5 - dm_4) / dm_4 * 100, 1) if dm_4 > 0 else 0

    print(f"   购物车: 4月{cart_4} → 5月{cart_5} ({cart_change}%)")
    print(f"   弹幕: 4月{dm_4} → 5月{dm_5} ({dm_change}%)")

    # 判断是否同比例跌
    same_trend = abs(cart_change - dm_change) <= CUTOFF_DAY
    print(f"   同比例下跌: {same_trend}")

    return {
        "monthly": results,
        "cart_change": cart_change,
        "dm_change": dm_change,
        "same_trend": same_trend,
        "conclusion": "曝光端问题" if same_trend else "直播间引导问题（购物车跌更多）",
    }


def analyze_holiday_effect(df_all):
    """假期效应分析"""
    print("\n🏖️ 假期效应分析 ...")
    cart_df = df_all[df_all["三级团队"] == "直播间购物车"].copy()

    # 劳动节 5月1-5日
    may_holiday = cart_df[(cart_df["月份"] == "5月") & (cart_df["day"] <= 5)]
    may_normal = cart_df[(cart_df["月份"] == "5月") & (cart_df["day"] > 5) & (cart_df["day"] <= CUTOFF_DAY)]

    # 4月同期（4月1-5日 vs 4月6-15日）
    apr_holiday = cart_df[(cart_df["月份"] == "4月") & (cart_df["day"] <= 5)]
    apr_normal = cart_df[(cart_df["月份"] == "4月") & (cart_df["day"] > 5) & (cart_df["day"] <= CUTOFF_DAY)]

    results = {
        "4月假期(1-5)": len(apr_holiday),
        "4月平日(6-15)": len(apr_normal),
        "5月假期(1-5)": len(may_holiday),
        "5月平日(6-15)": len(may_normal),
    }

    # 4月假期日均 vs 5月假期日均
    apr_holiday_daily = results["4月假期(1-5)"] / 5
    may_holiday_daily = results["5月假期(1-5)"] / 5
    holiday_drop = round((may_holiday_daily - apr_holiday_daily) / apr_holiday_daily * 100, 1) if apr_holiday_daily > 0 else 0

    # 4月平日日均 vs 5月平日日均
    apr_normal_daily = results["4月平日(6-15)"] / 10
    may_normal_daily = results["5月平日(6-15)"] / 10
    normal_drop = round((may_normal_daily - apr_normal_daily) / apr_normal_daily * 100, 1) if apr_normal_daily > 0 else 0

    print(f"   4月假期日均: {apr_holiday_daily:.0f}, 5月假期日均: {may_holiday_daily:.0f} ({holiday_drop}%)")
    print(f"   4月平日日均: {apr_normal_daily:.0f}, 5月平日日均: {may_normal_daily:.0f} ({normal_drop}%)")

    # 判断假期是否是主因
    holiday_is_main = abs(holiday_drop) > abs(normal_drop) + 20

    return {
        "counts": results,
        "holiday_drop": holiday_drop,
        "normal_drop": normal_drop,
        "holiday_is_main_factor": holiday_is_main,
    }


def analyze_weekday_pattern(df_all):
    """星期几效应"""
    print("\n📅 星期几效应分析 ...")
    cart_df = df_all[df_all["三级团队"] == "直播间购物车"].copy()

    weekdays = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
    results = {}

    for month in ["3月", "4月", "5月"]:
        m_df = cart_df[cart_df["月份"] == month]
        m_df = m_df[m_df["day"] <= CUTOFF_DAY]

        wd_counts = m_df["weekday"].value_counts().sort_index().to_dict()
        results[month] = {weekdays[i]: int(wd_counts.get(i, 0)) for i in range(7)}

    # 找出4月高峰日和5月低谷日
    print(f"   4月高峰: {max(results['4月'], key=results['4月'].get)} ({max(results['4月'].values())})")
    print(f"   5月低谷: {min(results['5月'], key=results['5月'].get)} ({min(results['5月'].values())})")

    return results


def analyze_member_category_cross(df_all):
    """会员等级 × 品类交叉分析"""
    print("\n👑 会员等级 × 品类交叉分析 ...")
    cart_df = df_all[df_all["三级团队"] == "直播间购物车"].copy()

    def level_group(lvl):
        if pd.isna(lvl):
            return "未知"
        lvl_str = str(lvl)
        if "V0" in lvl_str or "V1" in lvl_str:
            return "V0-V1 新用户"
        elif "V2" in lvl_str or "V3" in lvl_str or "V4" in lvl_str or "V5" in lvl_str or "V6" in lvl_str:
            return "V2-V6 普通会员"
        elif "V7" in lvl_str or "V8" in lvl_str or "V9" in lvl_str or "V10" in lvl_str:
            return "V7-V10 高价值"
        return "未知"

    cart_df["等级分组"] = cart_df["会员等级"].apply(level_group)

    # 按品类+月份+等级分组统计
    results = []
    for month in ["4月", "5月"]:
        m_df = cart_df[cart_df["月份"] == month]
        m_df = m_df[m_df["day"] <= CUTOFF_DAY]

        for cat in m_df["品类_norm"].dropna().unique():
            sub = m_df[m_df["品类_norm"] == cat]
            total = len(sub)
            if total == 0:
                continue
            high_value = len(sub[sub["等级分组"] == "V7-V10 高价值"])
            new_user = len(sub[sub["等级分组"] == "V0-V1 新用户"])
            results.append({
                "月份": month,
                "品类": cat,
                "总线索": total,
                "高价值用户": high_value,
                "新用户": new_user,
                "高价值占比": round(high_value / total * 100, 1),
                "新用户占比": round(new_user / total * 100, 1),
            })

    # 找出高价值占比最高的品类（线索≥20）
    high_value_cats = [r for r in results if r["月份"] == "4月" and r["总线索"] >= 20]
    high_value_cats.sort(key=lambda x: x["高价值占比"], reverse=True)

    print(f"   分析完成，共 {len(results)} 条记录")
    print(f"   4月高价值占比TOP: {high_value_cats[0]['品类'] if high_value_cats else 'N/A'} ({high_value_cats[0]['高价值占比'] if high_value_cats else 0}%)")

    return {
        "cross_data": results,
        "high_value_top": high_value_cats[:10],
    }


def parse_schedule_light():
    """轻量解析排期表：提取 日期->品类集合"""
    print("\n📅 解析排期表 ...")
    if not os.path.exists(SCHEDULE_FILE):
        print(f"   ⚠️ 排期表未找到: {SCHEDULE_FILE}")
        return {}

    xls = pd.ExcelFile(SCHEDULE_FILE)
    schedule_by_date = defaultdict(set)  # date_str -> {品类}
    exposure_by_date = defaultdict(int)  # date_str -> 曝光

    for sheet_name in xls.sheet_names:
        if "排期" not in sheet_name:
            continue
        try:
            df = pd.read_excel(xls, sheet_name=sheet_name, header=None)
        except Exception:
            continue

        # 找日期行：通常第3-4行，格式是 NaN, 周一, 周二, ... 或 日期, NaN, 4/20, 4/21, ...
        date_row_idx = None
        dates = []
        for i in range(min(10, len(df))):
            row = df.iloc[i]
            row_vals = [str(v) if pd.notna(v) else "" for v in row]
            row_str = " ".join(row_vals)
            if "周一" in row_str or "周二" in row_str or "星期" in row_str:
                date_row_idx = i
                # 找下一行或当前行的日期数字
                # 尝试下一行
                if i + 1 < len(df):
                    date_row = df.iloc[i + 1]
                else:
                    date_row = row
                for j, val in enumerate(date_row):
                    if pd.notna(val) and str(val).strip() != "":
                        try:
                            # 可能是数字如 20, 21
                            day = int(float(str(val).strip()))
                            dates.append((j, day))
                        except ValueError:
                            pass
                break
            # 也可能是直接有日期数字的行
            date_pattern = re.findall(r"(\d{1,2})[/\.\-](\d{1,2})", row_str)
            if date_pattern:
                date_row_idx = i
                for j, val in enumerate(row):
                    m = re.match(r"(\d{1,2})[/\.\-](\d{1,2})", str(val).strip())
                    if m:
                        dates.append((j, int(m.group(2))))
                break

        if not dates:
            continue

        # 推断月份：从sheet名提取
        month = None
        year = 2026
        m = re.search(r"(\d{1,2})月", sheet_name)
        if m:
            month = int(m.group(1))
        else:
            # 从sheet名中的日期推断
            m2 = re.search(r"(\d{1,2})\.(\d{1,2})", sheet_name)
            if m2:
                month = int(m2.group(1))

        if not month:
            continue

        # 遍历所有单元格，找品类名
        for i in range(len(df)):
            for j in range(len(df.columns)):
                val = df.iloc[i, j]
                if pd.isna(val):
                    continue
                val_str = str(val).strip()
                if not val_str or len(val_str) > 50:
                    continue

                # 尝试匹配品类
                cat = normalize_category(val_str)
                if cat and cat in STANDARD_CATS:
                    # 找对应的日期列
                    date_col = None
                    for col_idx, day in dates:
                        if j == col_idx:
                            date_col = (year, month, day)
                            break
                        # 如果当前列在日期列附近（合并单元格导致偏移）
                        if abs(j - col_idx) <= 2:
                            date_col = (year, month, day)
                            break

                    if date_col:
                        date_str = f"{date_col[0]}-{date_col[1]:02d}-{date_col[2]:02d}"
                        schedule_by_date[date_str].add(cat)

        # 提取曝光量级（简化：找包含"曝光量级"的行，取数字）
        for i in range(len(df)):
            row = df.iloc[i]
            for j, val in enumerate(row):
                if pd.notna(val) and "曝光量级" in str(val):
                    # 找同行的数字
                    for k in range(j + 1, min(j + 10, len(row))):
                        if pd.notna(row.iloc[k]):
                            try:
                                exp = int(float(str(row.iloc[k]).replace(",", "")))
                                # 找对应的日期
                                for col_idx, day in dates:
                                    if k == col_idx:
                                        date_str = f"{year}-{month:02d}-{day:02d}"
                                        exposure_by_date[date_str] += exp
                                        break
                            except ValueError:
                                pass
                    break

    # 按品类+月份统计排期场次（用于排期数差距分析）
    schedule_counts = defaultdict(lambda: defaultdict(int))  # month -> cat -> count
    for date_str, cats in schedule_by_date.items():
        month = int(date_str.split("-")[1])
        month_key = f"{month}月"
        for cat in cats:
            schedule_counts[month_key][cat] += 1

    print(f"   ✅ 解析到 {len(schedule_by_date)} 个日期，{sum(len(v) for v in schedule_by_date.values())} 个品类场次")
    return dict(schedule_by_date), dict(exposure_by_date), dict({k: dict(v) for k, v in schedule_counts.items()})


def analyze_schedule_correlation(df_all, schedule_by_date, exposure_by_date, schedule_counts):
    """排期-线索关联分析（含排期场次对比）"""
    print("\n🔗 排期-线索关联分析 ...")
    cart_df = df_all[df_all["三级团队"] == "直播间购物车"].copy()

    # 按日期+品类汇总线索
    cat_date_leads = defaultdict(int)
    for _, row in cart_df.iterrows():
        date_str = row["例子时间"].strftime("%Y-%m-%d")
        cat = row["品类_norm"]
        if cat:
            cat_date_leads[(date_str, cat)] += 1

    # 分析每个品类在5月的状况
    results = []
    all_cats = set(r["品类_norm"] for _, r in cart_df.iterrows() if pd.notna(r["品类_norm"]))

    for cat in all_cats:
        # 4月线索
        apr_leads = sum(1 for _, r in cart_df.iterrows()
                        if r["品类_norm"] == cat and r["月份"] == "4月" and r["day"] <= CUTOFF_DAY)
        # 5月线索
        may_leads = sum(1 for _, r in cart_df.iterrows()
                        if r["品类_norm"] == cat and r["月份"] == "5月" and r["day"] <= CUTOFF_DAY)

        # 4月排期场次 vs 5月排期场次（从排期表统计）
        apr_schedule_count = schedule_counts.get("4月", {}).get(cat, 0)
        may_schedule_count = schedule_counts.get("5月", {}).get(cat, 0)

        # 5月是否排期
        may_scheduled = any(cat in schedule_by_date.get(d, set())
                            for d in [f"2026-05-{day:02d}" for day in range(1, CUTOFF_DAY + 1)])

        # 曝光（简化：取该品类在5月所有排期的曝光总和）
        may_exposure = sum(exposure_by_date.get(d, 0)
                           for d in [f"2026-05-{day:02d}" for day in range(1, CUTOFF_DAY + 1)]
                           if cat in schedule_by_date.get(d, set()))

        # 转化率
        conversion = round(may_leads / may_exposure * 10000, 1) if may_exposure > 0 else 0
        # 线索/场次（判断是场次少了还是每场线索少了）
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

    # 按4月线索数降序
    results.sort(key=lambda x: x["4月线索"], reverse=True)

    # 统计
    not_scheduled = [r for r in results if not r["5月排期_bool"] and r["4月线索"] >= 20]
    low_conversion = [r for r in results if r["状态"] == "🟡 播了但转化率极低"]
    # 暴跌原因分类（针对暴跌/消失品类）
    drop_reasons = defaultdict(list)
    for r in results:
        if r["暴跌原因"] != "待分析":
            drop_reasons[r["暴跌原因"]].append(r)

    print(f"   高线索品类未排期: {len(not_scheduled)} 个")
    print(f"   播了但转化率极低: {len(low_conversion)} 个")

    return {
        "cat_schedule": results[:30],  # TOP30
        "not_scheduled": not_scheduled[:10],
        "low_conversion": low_conversion[:10],
        "drop_reasons": dict(drop_reasons),
    }


def build_dashboard_data(df_all, cat_analysis, member_analysis, channel_analysis,
                         holiday_analysis, weekday_analysis, schedule_analysis, member_cat_cross):
    """构建增强版 dashboard_data.json"""
    print("\n🏗️ 构建 dashboard_data.json ...")

    # 基础统计（1-15号同期）
    cart_df = df_all[df_all["三级团队"] == "直播间购物车"].copy()
    dm_df = df_all[df_all["三级团队"] == "直播间弹幕"].copy()

    months = ["3月", "4月", "5月"]
    total_stats = {}
    daily_cart = {}
    daily_dm = {}
    team_compare = {}

    for m in months:
        m_cart = cart_df[(cart_df["月份"] == m) & (cart_df["day"] <= CUTOFF_DAY)]
        m_dm = dm_df[(dm_df["月份"] == m) & (dm_df["day"] <= CUTOFF_DAY)]

        total_stats[m] = {
            "购物车": len(m_cart),
            "弹幕": len(m_dm),
        }

        # 日趋势
        daily_cart[m] = {}
        daily_dm[m] = {}
        for d in range(1, CUTOFF_DAY + 1):
            daily_cart[m][str(d)] = len(m_cart[m_cart["day"] == d])
            daily_dm[m][str(d)] = len(m_dm[m_dm["day"] == d])

        # 团队对比
        team_compare[m] = {
            "健康线": len(m_cart[m_cart["二级团队"] == "健康线"]),
            "兴趣变美线": len(m_cart[m_cart["二级团队"] == "兴趣变美线"]),
        }

    # 健康线整体跌幅
    health_4 = team_compare["4月"]["健康线"]
    health_5 = team_compare["5月"]["健康线"]
    health_drop_pct = round((health_5 - health_4) / health_4 * 100, 1) if health_4 > 0 else 0
    interest_4 = team_compare["4月"]["兴趣变美线"]
    interest_5 = team_compare["5月"]["兴趣变美线"]
    interest_drop_pct = round((interest_5 - interest_4) / interest_4 * 100, 1) if interest_4 > 0 else 0
    print(f"   健康线跌幅: {health_drop_pct}%, 兴趣变美线跌幅: {interest_drop_pct}%")

    # 目标达成
    may_cart = total_stats["5月"]["购物车"]
    target = 9500
    achievement = round(may_cart / target * 100, 1)
    gap = target - may_cart
    # 按当前pace预测月底
    daily_avg = may_cart / CUTOFF_DAY
    projected = daily_avg * 31
    projected_pct = round(projected / target * 100, 1)

    # 流水预测（按4月LTV 95倒推）
    projected_gmv = projected * 95

    # 增量更新：先读取已有 dashboard_data.json（保留 generate_data.py 生成的字段）
    existing_data = {}
    if os.path.exists(OUTPUT_JSON):
        try:
            with open(OUTPUT_JSON, "r", encoding="utf-8") as f:
                existing_data = json.load(f)
            print(f"   📖 读取已有 {OUTPUT_JSON}，保留原字段")
        except Exception as e:
            print(f"   ⚠️ 读取已有 JSON 失败: {e}")

    data = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "total_stats": total_stats,
        "daily_cart": daily_cart,
        "daily_dm": daily_dm,
        "team_compare": team_compare,
        "cat_data": cat_analysis["cat_data"],
        "high_value_cats": cat_analysis["high_value_cats"],
        "pareto": cat_analysis["pareto"],
        "findings": cat_analysis["findings"],
        "core_answer": cat_analysis["core_answer"],
        "member_levels": member_analysis,
        "channel_trends": channel_analysis,
        "holiday_effect": holiday_analysis,
        "weekday_pattern": weekday_analysis,
        "schedule_correlation": schedule_analysis,
        "target_tracking": {
            "5月购物车目标": target,
            f"5月当前(1-{CUTOFF_DAY})": may_cart,
            "达成率": achievement,
            "缺口": gap,
            "日均": round(daily_avg, 0),
            "月底预测": round(projected, 0),
            "预测达成率": projected_pct,
            "预估流水(按LTV95)": round(projected_gmv, 0),
        },
        "team_health_analysis": {
            "健康线_4月": health_4,
            "健康线_5月": health_5,
            "健康线跌幅": health_drop_pct,
            "兴趣变美线_4月": interest_4,
            "兴趣变美线_5月": interest_5,
            "兴趣变美线跌幅": interest_drop_pct,
        },
        "member_category_cross": member_cat_cross,
    }

    # 在 core_answer 中补充暴跌品类名称列表
    crashed_cats_names = [c["品类"] for c in cat_analysis["core_answer"].get("crashed_cats_detail", [])]
    data["core_answer"]["crashed_cats_names"] = crashed_cats_names

    # 强制保留 generate_data.py 生成的基础统计字段（避免数据源不一致被覆盖）
    force_preserve_keys = [
        "total_stats", "daily_cart", "daily_dm", "team_compare",
        "cart_stats_by_strategy", "cat_data_by_strategy",
        "schedule_correlation_main", "schedule_compare",
        "daily_stats", "team_stats", "channel_stats",
        "target_month", "current_month_label", "last_month_label",
    ]
    for key in force_preserve_keys:
        if key in existing_data:
            data[key] = existing_data[key]
            print(f"   ♻️ 强制保留已有字段: {key}")

    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"   ✅ 已生成 {OUTPUT_JSON}")
    return data


def main():
    print("=" * 60)
    print("深度归因分析")
    print("=" * 60)

    # 1. 加载数据
    df_all = load_all_data()

    # 2. 品类归因
    cat_analysis = analyze_category_trends(df_all)

    # 3. 会员等级
    member_analysis = analyze_member_levels(df_all)

    # 4. 渠道趋势
    channel_analysis = analyze_channel_trends(df_all)

    # 5. 假期效应
    holiday_analysis = analyze_holiday_effect(df_all)

    # 6. 星期几
    weekday_analysis = analyze_weekday_pattern(df_all)

    # 7. 会员等级×品类交叉
    member_cat_cross = analyze_member_category_cross(df_all)

    # 8. 排期解析
    schedule_by_date, exposure_by_date, schedule_counts = parse_schedule_light()

    # 9. 排期-线索关联
    schedule_analysis = analyze_schedule_correlation(df_all, schedule_by_date, exposure_by_date, schedule_counts)

    # 10. 构建输出
    data = build_dashboard_data(df_all, cat_analysis, member_analysis,
                                channel_analysis, holiday_analysis, weekday_analysis,
                                schedule_analysis, member_cat_cross)

    print("\n" + "=" * 60)
    print("🎉 分析完成！")
    print(f"📎 输出: {OUTPUT_JSON}")
    print("=" * 60)

    # 打印核心结论
    print("\n📋 核心结论:")
    ca = data["core_answer"]
    print(f"   5月较4月同期购物车线索跌 {ca['total_loss']} 条")
    print(f"   消失品类贡献: {ca['disappeared_pct']}%")
    print(f"   暴跌品类贡献: {ca['crashed_pct']}%")
    if ca["uniform_drop"]:
        print("   → 判断：均匀下跌（头部消失不是主因）")
    else:
        print("   → 判断：头部品类塌方导致（消失+暴跌是主因）")

    print(f"\n   5月目标达成率: {data['target_tracking']['达成率']}%")
    print(f"   月底预测达成率: {data['target_tracking']['预测达成率']}%")
    print(f"   渠道趋势: {data['channel_trends']['conclusion']}")
    print(f"   假期影响: {'是' if data['holiday_effect']['holiday_is_main_factor'] else '否'}主要因素")


if __name__ == "__main__":
    main()

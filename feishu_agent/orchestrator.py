"""
直播间线索归因复盘 — 主编排脚本
==============================
串联完整流水线：数据同步 → 深度分析 → 看板生成 → 周报发布

使用方法：
    cd ~/直播间数据分析/feishu_agent
    python3 orchestrator.py --mode full
    python3 orchestrator.py --mode dashboard-only
    python3 orchestrator.py --mode report-only
    python3 orchestrator.py --validate

模式说明：
    full          → 完整流水线（数据 → 看板 → 报告 → 发布）
    dashboard-only→ 只看板（跳过报告生成）
    report-only   → 只报告（基于现有 dashboard_data.json）
    validate      → 数据验证（不生成任何输出）
"""

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

# 加载配置
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    from config_local import (APP_ID, APP_SECRET, BITABLE_APP_TOKEN, BITABLE_TABLE_ID,
                               WEEKLY_DOC_ID, FEISHU_CHAT_ID)
except ImportError:
    from config import (APP_ID, APP_SECRET, BITABLE_APP_TOKEN, BITABLE_TABLE_ID,
                        WEEKLY_DOC_ID, FEISHU_CHAT_ID)

from feishu_client import FeishuClient

# 路径常量
PROJECT_ROOT = Path(__file__).parent.parent
FEISHU_AGENT_DIR = Path(__file__).parent
CHECKPOINT_FILE = FEISHU_AGENT_DIR / ".last_sync_checkpoint.json"
DASHBOARD_DATA_JSON = PROJECT_ROOT / "dashboard_data.json"
DASHBOARD_HTML = PROJECT_ROOT / "dashboard.html"


def log(msg: str):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")


def run_script(cmd: list, cwd: Path = PROJECT_ROOT, env: dict = None) -> bool:
    """运行外部脚本，返回是否成功"""
    log(f"▶️ 运行: {' '.join(cmd)} (cwd={cwd})")
    start = time.time()
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd, env=env)
    elapsed = time.time() - start

    if result.stdout:
        for line in result.stdout.strip().split("\n"):
            print(f"   {line}")
    if result.returncode != 0:
        log(f"❌ 失败 ({elapsed:.1f}s)")
        if result.stderr:
            for line in result.stderr.strip().split("\n"):
                print(f"   [stderr] {line}")
        return False
    log(f"✅ 成功 ({elapsed:.1f}s)")
    return True


def load_checkpoint() -> dict:
    """加载上次同步检查点"""
    if CHECKPOINT_FILE.exists():
        try:
            with open(CHECKPOINT_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def save_checkpoint(data: dict):
    """保存同步检查点"""
    checkpoint = load_checkpoint()
    checkpoint.update(data)
    checkpoint["last_sync"] = datetime.now().isoformat()
    with open(CHECKPOINT_FILE, "w", encoding="utf-8") as f:
        json.dump(checkpoint, f, ensure_ascii=False, indent=2)
    log(f"💾 检查点已保存: {CHECKPOINT_FILE}")


def step_fetch_data() -> bool:
    """步骤1：从 Bitable/Excel 读取数据并生成 dashboard_data.json"""
    log("=" * 50)
    log("步骤 1/5：数据同步（generate_data.py）")
    log("=" * 50)
    return run_script([sys.executable, str(PROJECT_ROOT / "generate_data.py")])


def step_deep_analysis() -> bool:
    """步骤2（可选）：运行深度归因分析"""
    deep_script = PROJECT_ROOT / "deep_dive_analysis.py"
    if not deep_script.exists():
        log("   ℹ️ deep_dive_analysis.py 不存在，跳过深度分析")
        return True

    log("=" * 50)
    log("步骤 2/5：深度归因分析（deep_dive_analysis.py）")
    log("=" * 50)
    # deep_dive_analysis.py 直接输出到 dashboard_data.json
    return run_script([sys.executable, str(deep_script)])


def step_generate_dashboard() -> bool:
    """步骤3：生成看板 HTML"""
    log("=" * 50)
    log("步骤 3/5：看板生成（generate_dashboard.py）")
    log("=" * 50)
    return run_script([sys.executable, str(PROJECT_ROOT / "generate_dashboard.py")])


def step_generate_report() -> bool:
    """步骤4：生成并发布周报"""
    log("=" * 50)
    log("步骤 4/5：周报生成与发布（weekly_report.py）")
    log("=" * 50)
    return run_script([sys.executable, str(FEISHU_AGENT_DIR / "weekly_report.py")])


def step_validate() -> bool:
    """验证模式：核对 dashboard_data.json 核心指标"""
    log("=" * 50)
    log("步骤：数据验证")
    log("=" * 50)

    if not DASHBOARD_DATA_JSON.exists():
        log(f"❌ {DASHBOARD_DATA_JSON} 不存在")
        return False

    with open(DASHBOARD_DATA_JSON, "r", encoding="utf-8") as f:
        data = json.load(f)

    checks = []

    # 检查1：total_stats 存在且非空
    total_stats = data.get("total_stats", {})
    checks.append(("total_stats 存在", bool(total_stats)))
    checks.append(("total_stats 含5月", "5月" in total_stats))

    # 检查2：cat_data 存在且非空
    cat_data = data.get("cat_data", [])
    checks.append(("cat_data 存在", len(cat_data) > 0))

    # 检查3：target_tracking 存在（周报依赖）
    checks.append(("target_tracking 存在", "target_tracking" in data))

    # 检查4：channel_trends 存在（周报依赖）
    checks.append(("channel_trends 存在", "channel_trends" in data))

    # 检查5：holiday_effect 存在（周报依赖）
    checks.append(("holiday_effect 存在", "holiday_effect" in data))

    # 检查6：member_levels 存在（周报依赖）
    checks.append(("member_levels 存在", "member_levels" in data))

    # 检查7：核心指标数值合理
    cart_5 = total_stats.get("5月", {}).get("购物车", 0)
    checks.append(("5月购物车线索 > 0", cart_5 > 0))

    # 输出结果
    all_pass = True
    for name, passed in checks:
        status = "✅" if passed else "❌"
        if not passed:
            all_pass = False
        log(f"   {status} {name}")

    if all_pass:
        log("✅ 所有验证通过")
    else:
        log("❌ 验证未通过，请检查数据源")

    return all_pass


def step_notify(mode: str, success: bool) -> bool:
    """步骤5（可选）：飞书群通知"""
    if not FEISHU_CHAT_ID:
        log("   ℹ️ FEISHU_CHAT_ID 未配置，跳过通知")
        return True

    log("=" * 50)
    log("步骤 5/5：飞书群通知")
    log("=" * 50)

    try:
        client = FeishuClient(APP_ID, APP_SECRET)
        today_str = datetime.now().strftime("%m-%d")
        status = "成功" if success else "失败"
        emoji = "✅" if success else "❌"
        title = f"{emoji} 直播间流水线 {status} ({today_str})"
        content = f"模式: {mode}\n"
        if success:
            content += "看板和周报已自动更新。"
        else:
            content += "部分步骤失败，请查看日志。"

        client.send_rich_message(FEISHU_CHAT_ID, title, content, "")
        log("✅ 通知已发送")
        return True
    except Exception as e:
        log(f"⚠️ 通知发送失败: {e}")
        return False


def run_pipeline(mode: str) -> bool:
    """运行完整或部分流水线"""
    log("\n" + "=" * 60)
    log(f"🚀 启动流水线 | 模式: {mode}")
    log("=" * 60)

    overall_success = True

    if mode == "validate":
        return step_validate()

    # 1. 数据同步（dashboard-only 和 report-only 都需要，但 report-only 可以跳过）
    if mode in ("full", "dashboard-only"):
        if not step_fetch_data():
            overall_success = False
            if mode == "full":
                log("❌ 数据同步失败，终止流水线")
                step_notify(mode, False)
                return False

        # 2. 深度分析（可选）
        if not step_deep_analysis():
            log("   ⚠️ 深度分析失败，继续...")
            # 非致命错误，继续

    # 3. 看板生成（full 和 dashboard-only）
    if mode in ("full", "dashboard-only"):
        if not step_generate_dashboard():
            overall_success = False
            if mode == "dashboard-only":
                step_notify(mode, False)
                return False

    # 4. 周报生成（full 和 report-only）
    if mode in ("full", "report-only"):
        if not step_generate_report():
            overall_success = False

    # 5. 通知
    if mode == "full":
        step_notify(mode, overall_success)

    # 保存检查点
    if overall_success:
        save_checkpoint({"last_mode": mode})

    log("\n" + "=" * 60)
    if overall_success:
        log("🎉 流水线完成")
    else:
        log("⚠️ 流水线部分失败，请查看日志")
    log("=" * 60)
    return overall_success


def main():
    parser = argparse.ArgumentParser(description="直播间线索归因复盘 — 主编排脚本")
    parser.add_argument("--mode", choices=["full", "dashboard-only", "report-only", "validate"],
                        default="full",
                        help="运行模式 (默认: full)")
    parser.add_argument("--force", action="store_true",
                        help="强制运行，跳过变更检测")
    args = parser.parse_args()

    # 检查凭证
    if not APP_ID or APP_ID.startswith("cli_xxxxxxxx") or not APP_SECRET:
        log("❌ 错误：请先配置 config_local.py，填入真实的 APP_ID 和 APP_SECRET")
        sys.exit(1)

    run_pipeline(args.mode)


if __name__ == "__main__":
    main()

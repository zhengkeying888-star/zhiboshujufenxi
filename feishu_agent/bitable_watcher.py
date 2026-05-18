"""
Bitable 变更监听脚本
==================
轮询飞书多维表格记录数，检测到变化时自动触发 orchestrator.py

使用方法：
    # 单次检查
    cd ~/直播间数据分析/feishu_agent
    python3 bitable_watcher.py --once

    # 后台守护模式（每10分钟检查一次）
    python3 bitable_watcher.py --daemon --interval 600

    # 强制触发（不管是否有变化）
    python3 bitable_watcher.py --once --force

    # 只检查，不触发（dry-run）
    python3 bitable_watcher.py --once --dry-run

检查点文件：.last_sync_checkpoint.json
"""

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    from config_local import APP_ID, APP_SECRET, BITABLE_APP_TOKEN, BITABLE_TABLE_ID
except ImportError:
    from config import APP_ID, APP_SECRET, BITABLE_APP_TOKEN, BITABLE_TABLE_ID

from feishu_client import FeishuClient

CHECKPOINT_FILE = Path(__file__).parent / ".last_sync_checkpoint.json"


def log(msg: str):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")


def load_checkpoint() -> dict:
    """加载检查点"""
    if CHECKPOINT_FILE.exists():
        try:
            with open(CHECKPOINT_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            log(f"⚠️ 读取检查点失败: {e}")
    return {}


def save_checkpoint(data: dict):
    """保存检查点"""
    checkpoint = load_checkpoint()
    checkpoint.update(data)
    with open(CHECKPOINT_FILE, "w", encoding="utf-8") as f:
        json.dump(checkpoint, f, ensure_ascii=False, indent=2)


def get_record_count(client: FeishuClient, app_token: str, table_id: str) -> int:
    """获取多维表格当前记录总数"""
    # 使用 _request 直接调用 API，获取 total 字段
    data = client._request(
        "GET",
        f"/bitable/v1/apps/{app_token}/tables/{table_id}/records",
        params={"page_size": 1}
    )
    total = data.get("total", 0)
    return total


def get_last_record_time(client: FeishuClient, app_token: str, table_id: str) -> str:
    """获取最新一条记录的创建/更新时间（作为辅助判断）"""
    try:
        data = client._request(
            "GET",
            f"/bitable/v1/apps/{app_token}/tables/{table_id}/records",
            params={"page_size": 1, "sort": '[{"field_name":"例子时间","desc":true}]'}
        )
        items = data.get("items", [])
        if items:
            # 优先取 updated_time，fallback created_time
            ts = items[0].get("updated_time") or items[0].get("created_time")
            return str(ts) if ts else ""
    except Exception as e:
        log(f"   ⚠️ 获取最新记录时间失败: {e}")
    return ""


def detect_change(client: FeishuClient, app_token: str, table_id: str) -> tuple:
    """
    检测 Bitable 是否有变化
    返回: (has_changed: bool, info: dict)
    """
    checkpoint = load_checkpoint()
    prev_count = checkpoint.get("record_count", 0)
    prev_time = checkpoint.get("last_record_time", "")

    log("📡 正在检测 Bitable 变化 ...")

    try:
        current_count = get_record_count(client, app_token, table_id)
        current_time = get_last_record_time(client, app_token, table_id)
    except Exception as e:
        log(f"❌ 检测失败: {e}")
        return False, {"error": str(e)}

    info = {
        "prev_count": prev_count,
        "current_count": current_count,
        "prev_time": prev_time,
        "current_time": current_time,
    }

    log(f"   上次记录数: {prev_count}")
    log(f"   当前记录数: {current_count}")
    if prev_time:
        log(f"   上次最新记录: {prev_time}")
    if current_time:
        log(f"   当前最新记录: {current_time}")

    if current_count == 0:
        log("⚠️ Bitable 为空，无变化")
        return False, info

    # 判断变化：记录数变化 或 最新记录时间变化
    has_changed = False
    if current_count != prev_count:
        log(f"   📈 记录数变化: {prev_count} → {current_count}")
        has_changed = True
    elif current_time and current_time != prev_time:
        log(f"   🕐 最新记录时间变化: {prev_time} → {current_time}")
        has_changed = True
    else:
        log("   ✅ 无变化")

    return has_changed, info


def trigger_orchestrator(mode: str = "full") -> bool:
    """触发 orchestrator.py"""
    orchestrator = Path(__file__).parent / "orchestrator.py"
    if not orchestrator.exists():
        log(f"❌ orchestrator.py 不存在: {orchestrator}")
        return False

    log(f"🚀 触发 orchestrator.py --mode {mode}")
    result = subprocess.run(
        [sys.executable, str(orchestrator), "--mode", mode],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent
    )

    if result.stdout:
        for line in result.stdout.strip().split("\n"):
            print(f"   {line}")
    if result.returncode != 0:
        log("❌ orchestrator 执行失败")
        if result.stderr:
            for line in result.stderr.strip().split("\n"):
                print(f"   [stderr] {line}")
        return False

    log("✅ orchestrator 执行成功")
    return True


def run_once(force: bool = False, dry_run: bool = False, mode: str = "full") -> bool:
    """单次检查并触发"""
    if not APP_ID or APP_ID.startswith("cli_xxxxxxxx") or not APP_SECRET:
        log("❌ 错误：请先配置 config_local.py")
        return False

    if not BITABLE_APP_TOKEN or not BITABLE_TABLE_ID:
        log("❌ 错误：BITABLE_APP_TOKEN 和 BITABLE_TABLE_ID 未配置")
        return False

    client = FeishuClient(APP_ID, APP_SECRET)

    if force:
        log("🔧 强制模式：跳过变更检测")
        has_changed = True
        info = {}
    else:
        has_changed, info = detect_change(client, BITABLE_APP_TOKEN, BITABLE_TABLE_ID)

    if not has_changed:
        log("   ℹ️ 无变化，跳过执行")
        return True

    if dry_run:
        log("   🧪 Dry-run 模式：检测到变化，但不触发 orchestrator")
        return True

    # 更新检查点（在触发前更新，避免重复触发）
    save_checkpoint({
        "record_count": info.get("current_count", 0),
        "last_record_time": info.get("current_time", ""),
        "last_check": datetime.now().isoformat(),
    })

    # 触发流水线
    success = trigger_orchestrator(mode)

    # 更新检查点状态
    save_checkpoint({
        "last_trigger": datetime.now().isoformat(),
        "last_trigger_success": success,
    })

    return success


def run_daemon(interval: int = 600, mode: str = "full"):
    """后台守护模式"""
    log(f"👁️ 守护模式启动，轮询间隔: {interval}秒")
    log(f"   检查点文件: {CHECKPOINT_FILE}")
    log("   按 Ctrl+C 停止")

    while True:
        try:
            run_once(force=False, dry_run=False, mode=mode)
        except KeyboardInterrupt:
            log("\n🛑 守护模式停止")
            break
        except Exception as e:
            log(f"❌ 异常: {e}")

        log(f"   💤 休眠 {interval}秒 ...")
        time.sleep(interval)


def main():
    parser = argparse.ArgumentParser(description="Bitable 变更监听脚本")
    parser.add_argument("--once", action="store_true", help="单次检查")
    parser.add_argument("--daemon", action="store_true", help="后台守护模式")
    parser.add_argument("--interval", type=int, default=600, help="守护模式轮询间隔（秒，默认600）")
    parser.add_argument("--force", action="store_true", help="强制触发，跳过变更检测")
    parser.add_argument("--dry-run", action="store_true", help="只检测，不触发")
    parser.add_argument("--mode", default="full", help="orchestrator 模式（默认 full）")
    args = parser.parse_args()

    if args.daemon:
        run_daemon(interval=args.interval, mode=args.mode)
    else:
        # 默认单次模式
        run_once(force=args.force, dry_run=args.dry_run, mode=args.mode)


if __name__ == "__main__":
    main()

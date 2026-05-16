"""
飞书智能体配置模板
==================
使用方式：
1. 复制本文件为 config_local.py（config_local.py 已被 .gitignore 忽略，不会提交到git）
2. 在 config_local.py 中填入你的真实凭证
3. 所有脚本会自动从 config_local.py 读取配置

⚠️ 不要把真实凭证填到这个 config.py 文件里！
"""

# ============================================
# 飞书自建应用凭证（必填）
# 获取方式：
#   1. 打开 https://open.feishu.cn/
#   2. 创建企业自建应用
#   3. 在"凭证与基础信息"页面获取 app_id 和 app_secret
#   4. 开通权限：bitable:record:read, bitable:record:write, docx:document:write, im:message:send
# ============================================
APP_ID = "cli_xxxxxxxxxxxxxxxx"           # ← 替换为你的 app_id
APP_SECRET = "xxxxxxxxxxxxxxxxxxxxxxxx"   # ← 替换为你的 app_secret

# ============================================
# 多维表格配置
# ============================================
# 方式A：创建新表格（首次运行）
#   - 留空，运行 setup_bitable.py 后会自动创建并打印 token
#   - 把打印出来的 token 填到这里
# 方式B：使用已有表格
#   - 从表格分享链接中提取 token（链接中 /base/ 后面的字符串）
BITABLE_APP_TOKEN = ""                    # ← 例：YlkPbyxeda8FLQsCcJlcSDhPnTb
BITABLE_TABLE_ID = ""                     # ← 例：tblxxxxxxxxxxxxxx

# ============================================
# 飞书文档配置（周报写入）
# ============================================
# 方式A：创建新文档（首次运行 weekly_report.py 后自动创建）
#   - 留空，运行后会自动创建并打印 document_id
# 方式B：使用已有文档
#   - 从文档链接中提取 document_id（链接中 /docx/ 后面的字符串）
WEEKLY_DOC_ID = ""                        # ← 例：doxxxxxxxxxxxxxxx

# ============================================
# 飞书群通知配置
# ============================================
# 方式A：使用群聊 chat_id（推荐）
#   - 在飞书群中添加你的自建应用机器人
#   - 调用 notify.py 中的 get_chat_id() 获取 chat_id
# 方式B：使用 webhook（简单但不够灵活）
#   - 在飞书群中添加自定义机器人，复制 webhook_url
FEISHU_CHAT_ID = ""                       # ← 例：oc_xxxxxxxxxxxxxxxx
FEISHU_WEBHOOK_URL = ""                   # ← 例：https://open.feishu.cn/open-apis/bot/v2/hook/xxxxxx

# ============================================
# Vercel 部署配置（可选，用于在线看板托管）
# ============================================
VERCEL_TOKEN = ""                         # ← 从 https://vercel.com/account/tokens 获取
VERCEL_PROJECT_ID = ""                    # ← 项目ID

# ============================================
# 数据口径配置
# ============================================
# 历史Excel文件路径（首次导入用）
HISTORY_EXCEL_FILES = [
    "3月直播间数据分析.xlsx",
    "4月直播间数据分析.xlsx",
    "5月直播间数据分析.xlsx",
]

# 明细sheet名称
EXCEL_SHEET_NAME = "明细"

# 看板输出路径
DASHBOARD_OUTPUT = "../dashboard.html"
DASHBOARD_DATA_JSON = "../dashboard_data.json"

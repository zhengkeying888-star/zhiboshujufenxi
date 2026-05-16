# 直播间线索归因智能体

> 基于飞书多维表格 + GitHub Actions 的全自动化数据看板与周报系统。

## 架构概览

```
[飞书多维表格：线索明细]
        ↓ 自动读取（每天/每周）
[GitHub Actions / 本地脚本]
        ↓ 数据处理
[dashboard.html 看板] + [飞书文档：周报]
        ↓ 自动推送
[飞书群通知]
```

## 核心能力

| 能力 | 说明 |
|------|------|
| **数据自动同步** | 从飞书多维表格读取最新数据，自动生成看板 |
| **品类自动归因** | 自动识别消失/暴跌/下滑/扛住的品类 |
| **周报自动生成** | 每周一自动生成复盘周报，写入飞书文档 |
| **群通知** | 看板更新后自动推送到飞书群 |
| **零代码维护** | 日常只需在多维表格追加数据，其余全自动 |

## 文件结构

```
feishu_agent/
├── config.py              # 配置模板（不要填真实凭证）
├── config_local.py        # 本地配置（填入真实凭证，已被.gitignore忽略）
├── feishu_client.py       # 飞书 OpenAPI 封装
├── setup_bitable.py       # 初始化：创建多维表格 + 导入历史数据
├── sync_and_build.py      # 同步数据 + 生成看板
├── weekly_report.py       # 生成周报 + 写入飞书文档
├── .gitignore             # 排除敏感文件
└── README.md              # 本文档

.github/workflows/
└── auto-dashboard.yml     # GitHub Actions 自动化工作流

[dashboard.html]           # 生成的看板（项目根目录）
[dashboard_data.json]      # 看板数据（项目根目录）
```

## 快速开始（3步走）

### 第一步：准备飞书应用（5分钟）

1. 打开 [飞书开放平台](https://open.feishu.cn/)
2. 创建「企业自建应用」
3. 在「凭证与基础信息」页面获取 **app_id** 和 **app_secret**
4. 进入「权限管理」，开通以下权限：
   - `bitable:record:read` —— 读取多维表格
   - `bitable:record:write` —— 写入多维表格
   - `docx:document:write` —— 创建/写入文档
   - `im:message:send` —— 发送群消息（可选）
5. 进入「版本管理与发布」，创建版本并发布（选择「仅自己可见」或「部分员工可见」）

### 第二步：初始化多维表格（1分钟）

```bash
cd feishu_agent

# 1. 复制配置模板
cp config.py config_local.py

# 2. 编辑 config_local.py，填入 app_id 和 app_secret
#    （只填 APP_ID 和 APP_SECRET 即可，其他留空）

# 3. 运行初始化脚本
python setup_bitable.py
```

脚本会自动：
- 在飞书创建「直播间线索数据」多维表格
- 创建「线索明细」数据表
- 添加字段（日期、品类名、二级团队、三级团队、会员等级、线索数）
- 读取历史 Excel（3月/4月/5月），汇总后导入

**运行完成后，控制台会打印：**
```
BITABLE_APP_TOKEN = "YlkPby..."
BITABLE_TABLE_ID  = "tbl..."
```

把这两个值填入 `config_local.py`。

### 第三步：日常维护

以后每天/每周，你只需要在飞书多维表格中**追加新行**即可：

| 日期 | 品类名 | 二级团队 | 三级团队 | 会员等级 | 线索数 |
|------|--------|----------|----------|----------|--------|
| 2026/05/16 | 摄影美学 | 兴趣变美线 | 直播间购物车 | V1 普通岛民 | 50 |
| 2026/05/16 | 摄影美学 | 兴趣变美线 | 直播间弹幕 | V1 普通岛民 | 30 |

> 💡 建议按天+品类+团队+等级汇总后填写，一行代表一个维度组合的线索数量。

## 自动化触发方式（3选1）

### 方式A：GitHub Actions（推荐，零服务器成本）

1. 把代码推送到 GitHub 仓库
2. 在仓库 Settings → Secrets and variables → Actions 中添加以下 Secrets：
   - `FEISHU_APP_ID`
   - `FEISHU_APP_SECRET`
   - `BITABLE_APP_TOKEN`
   - `BITABLE_TABLE_ID`
   - `WEEKLY_DOC_ID`（可选，首次运行 weekly_report.py 后会自动创建）
   - `FEISHU_CHAT_ID`（可选，用于群通知）
   - `VERCEL_TOKEN`（可选，用于在线部署）
3. 工作流会自动：
   - 每周一早上 9:00 生成看板 + 周报
   - 提交更新后的看板到 git
   - 推送飞书群通知

**手动触发**：在 Actions 页面点击「Run workflow」。

### 方式B：本地定时任务（Mac/Linux）

```bash
# 编辑 crontab
crontab -e

# 每天凌晨1点自动同步
0 1 * * * cd /Users/zhengkeying/直播间数据分析/feishu_agent && /usr/bin/python3 sync_and_build.py >> /tmp/dashboard_sync.log 2>&1

# 每周一早上9点生成周报
0 9 * * 1 cd /Users/zhengkeying/直播间数据分析/feishu_agent && /usr/bin/python3 weekly_report.py >> /tmp/weekly_report.log 2>&1
```

### 方式C：手动运行

```bash
cd feishu_agent

# 同步数据并生成看板
python sync_and_build.py

# 生成周报
python weekly_report.py
```

## 周报文档

首次运行 `weekly_report.py` 时，如果 `WEEKLY_DOC_ID` 留空，脚本会自动创建一个新的飞书文档，并打印 document_id。

把 document_id 填入 `config_local.py`，以后周报就会写入同一个文档。

周报链接格式：`https://www.feishu.cn/docx/{document_id}`

## 常见问题

**Q：历史Excel数据量很大，导入会不会很慢？**
A：3个月约1万条明细，汇总后约几千条记录。飞书API批量写入每次500条，通常30秒内完成。

**Q：飞书多维表格的日期字段怎么填？**
A：直接选择日期类型，格式为 `2026/05/16`。脚本会自动转换为时间戳。

**Q：如果我以后想增加新字段（比如"投手名称"）怎么办？**
A：
1. 在飞书多维表格中手动添加新字段
2. 修改 `sync_and_build.py` 中的数据处理逻辑
3. 重新运行 `sync_and_build.py`

**Q：GitHub Actions 运行时提示 Secrets 找不到？**
A：确保在仓库的 **Settings → Secrets and variables → Actions** 中添加了 Secrets，不是在本地环境变量中。

**Q：如何获取飞书群 chat_id？**
A：运行以下代码（填入你的凭证）：
```python
from feishu_client import FeishuClient
client = FeishuClient("your_app_id", "your_app_secret")
for chat in client.get_chat_list():
    print(chat["chat_id"], chat["name"])
```

## 安全提示

- `config_local.py` 包含敏感凭证，**已被 .gitignore 排除**，不会提交到 git
- 不要把 `config_local.py` 的内容截图或发送给他人
- GitHub Secrets 是加密存储的，比本地文件更安全

## 迭代计划

| 版本 | 功能 |
|------|------|
| v1.0 | 基础看板 + 飞书多维表格同步 + 周报自动生成 |
| v1.1 | 到课率/完课率数据接入（后链路数据就绪后） |
| v1.2 | AI 自动归因建议（接入 Claude API 分析异常） |
| v1.3 | 预测模型（基于排期预测下月线索量） |

---

*最后更新：2026-05-15*

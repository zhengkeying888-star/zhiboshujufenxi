# 直播间线索周报/月报自动化技能 PRD

## 一、背景与目标

**业务背景**：直播间线索数据（购物车 + 弹幕）需要定期向上级汇报。汇报核心维度是**同期对比**（如 5月1-17日 vs 4月1-17日），并需回答三个问题：
1. 当月进度离目标差多少？
2. 为什么发生这样的变化？
3. 接下来怎么调整，对下月目标有何启示？

**目标**：一键生成聚焦的可视化周报/月报，自动写入飞书文档，支持 callout 高亮、图表嵌入、富文本表格。

## 二、技能封装清单

| 模块 | 文件 | 职责 |
|------|------|------|
| Chart 技能 | `~/.claude/skills/chart` | ECharts 图表生成 + 截图（1920×900） |
| 飞书客户端 | `feishu_client.py` | Bitable/Docx/Im API 封装（token 自动续期） |
| 富文本写入器 | `write_rich_doc.py` | Markdown + `[CALLOUT]` 语法 → 飞书 block |
| 周报生成器 | `weekly_report.py` | 4模块聚焦框架 + 图表生成 + 飞书写入 |
| 月报生成器 | `monthly_report.py` | （待同步周报框架） |
| 本地配置 | `config_local.py` | 凭证、表格/文档ID、目标口径 |

## 三、调用方式

### 3.1 一键生成周报

```bash
cd ~/直播间数据分析/feishu_agent
python3 weekly_report.py
```

**输出**：
- 飞书文档更新（`WEEKLY_DOC_ID` 配置的文档）
- 本地备份：`weekly_report_YYYYMMDD.md`
- 图表目录：`output/weekly-charts/{crashed-cats,weekly-trend,cat-changes-monthly}/screenshot.png`

### 3.2 生成纯文本报告（不写入飞书）

```python
from weekly_report import generate_weekly_report, fetch_recent_data, load_deep_dive_data
from feishu_client import FeishuClient
from config_local import APP_ID, APP_SECRET, BITABLE_APP_TOKEN, BITABLE_TABLE_ID

client = FeishuClient(APP_ID, APP_SECRET)
records = fetch_recent_data(client, BITABLE_APP_TOKEN, BITABLE_TABLE_ID, days=45)
deep_data = load_deep_dive_data()
report_md = generate_weekly_report(records, deep_data)
print(report_md)
```

### 3.3 单独生成图表

```python
from weekly_report import generate_report_charts
chart_images = generate_report_charts(records, deep_data)
# 返回 [(标题, 图片路径), ...]
```

### 3.4 富文本写入（通用）

```python
import write_rich_doc
from feishu_client import FeishuClient

client = FeishuClient(app_id, app_secret)
content = """
# 标题

[CALLOUT red]
这是红色警示框
[/CALLOUT]

普通文本段落。

---

## 二级标题
"""
write_rich_doc.write_rich_doc(client, document_id, content)
```

**支持的 CALLOUT 类型**：`red` | `yellow` | `green` | `blue`

## 四、数据流

```
飞书 Bitable（线索明细）
    ↓ fetch_recent_data()
Python 内存（recent_records）
    ↓ generate_weekly_report()
Markdown 报告 + [CALLOUT] 标记
    ↓ write_rich_doc.write_rich_doc()
飞书 Docx（富文本 block）
    ↓ lark-cli docs +media-insert
飞书 Docx（图表追加）
```

同期对比数据源：
- **本月同期**：`today.replace(day=1)` ~ `today`
- **上月同期**：`last_month_start` ~ `last_month_start + timedelta(days=today.day - 1)`

## 五、配置清单（config_local.py）

| 配置项 | 说明 | 获取方式 |
|--------|------|----------|
| `APP_ID` / `APP_SECRET` | 飞书自建应用凭证 | 飞书开放平台 → 应用 → 凭证与基础信息 |
| `BITABLE_APP_TOKEN` / `BITABLE_TABLE_ID` | 线索明细多维表 | 首次运行 `setup_bitable.py` 后填入 |
| `WEEKLY_DOC_ID` | 周报飞书文档 ID | 首次运行脚本后自动创建，或手动创建后填入 |
| `SCHEDULE_APP_TOKEN` / `SCHEDULE_TABLE_ID` | 排期明细多维表 | 首次运行 `setup_schedule_bitable.py` 后填入 |

## 六、关键约束与注意事项

1. **路径约束**：执行任何脚本前必须先 `cd ~/直播间数据分析/feishu_agent`，绝不在 `~` 直接运行。
2. **同期对比核心**：周报必须以「本月1-X日 vs 上月1-X日」为核心维度，周度环比仅作辅助。
3. **文档所有权**：飞书文档必须用**用户身份**创建（`lark-cli docs +create --api-version v2`），否则用户无法手动编辑。
4. **图表清晰度**：截图分辨率固定为 `1920×900`，输出约 3840×1800（PR=2），在文档中缩放后仍清晰。
5. **callout 规范**：
   - block_type = **19**（不是 22）
   - emoji_id 必须用字符串 ID（如 `bulb`, `fire`, `done`, `info`），**不能用 Unicode emoji**
   - 颜色枚举：`background_color` 1-15，`border_color`/`text_color` 1-7
6. **lark-cli 图片插入**：必须使用 `--as bot` 参数，且 `--file` 使用相对路径（以 `feishu_agent/` 为基准）。
7. **目标口径**：5月目标 90万流水，6月目标 110万流水；报告中的目标追踪同时展示线索数与预估流水。

## 七、扩展指南

### 新增图表类型
1. 在 `generate_report_charts()` 中新增一段 `body_html` + `chart_js`
2. 调用 `_build_and_screenshot()` 生成 PNG
3. 在 `main()` 的图表插入循环中会自动追加到文档末尾

### 新增 callout 颜色
1. 修改 `write_rich_doc.py` 中 `styles` 字典，增加新的 `bg`/`border`/`text` 枚举组合
2. 在 `weekly_report.py` 的 Markdown 中使用 `[CALLOUT 新颜色]...[/CALLOUT]`

### 月报同步
`monthly_report.py` 需同步为相同的 4模块聚焦框架，核心差异：
- 对比维度变为「本月整月 vs 上月整月」
- 增加「月度品类排行」和「月度线级占比变化」
- 下月启示直接对接「下月目标」（如 7月目标）

## 八、故障排查

| 现象 | 原因 | 修复 |
|------|------|------|
| `unsafe file path` | lark-cli `--file` 用了绝对路径 | 改用 `os.path.relpath()` 生成的相对路径 |
| `forBidden` (1770032) | lark-cli 缺少 `--as bot` | 补加 `--as bot` |
| `field validation failed` (99992402) | callout 颜色用了 RGB 字典 | 改为整数枚举值 |
| `schema mismatch` (1770006) | callout emoji_id 用了 Unicode emoji | 改为字符串 ID（如 `bulb`） |
| `没有编辑权限` | 文档是 bot 创建的 | 用用户身份重新创建文档并更新 `WEEKLY_DOC_ID` |

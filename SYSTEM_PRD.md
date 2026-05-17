# 直播间线索归因复盘系统 PRD（含协作协议）

## 1. 系统定位

**一句话描述**：从原始 Excel/飞书多维表格 → 自动化看板 → 聚焦型周报/月报 → 飞书文档的端到端数据归因与汇报系统。

**目标用户**：直播间运营团队、数据分析师、管理层（向上汇报场景）。

**核心目标**：
1. **诊断**：快速定位线索量波动的业务根因（品类/排期/用户/渠道）
2. **汇报**：生成适合上级阅读的可视化复盘报告
3. **沉淀**：将分析结论与策略建议结构化写入飞书，支持人工补充

---

## 2. 系统架构（四层）

```
┌─────────────────────────────────────────────────────────────┐
│  Layer 4: 汇报层（飞书文档 / 群通知）                          │
│  - 周报：4模块聚焦框架（业绩概览→归因拆解→调整策略→下月启示）   │
│  - 月报：整月维度 + 品类排行 + 线级占比变化                    │
│  - 富文本：callout 高亮、图表嵌入、表格                        │
├─────────────────────────────────────────────────────────────┤
│  Layer 3: 看板层（dashboard.html）                           │
│  - KPI 总览、日趋势折线、品类归因卡片、会员等级结构            │
│  - 数据发现清单、归因输入区                                    │
│  - 技术栈：单 HTML + Tailwind + ECharts                        │
├─────────────────────────────────────────────────────────────┤
│  Layer 2: 数据层（Python 处理）                                │
│  - generate_data.py：Excel → dashboard_data.json              │
│  - generate_dashboard.py：JSON → dashboard.html               │
│  - weekly_report.py：JSON + Bitable → Markdown + 图表        │
│  - feishu_client.py：Bitable/Docx/Im API 封装                │
├─────────────────────────────────────────────────────────────┤
│  Layer 1: 数据源层                                             │
│  - 历史 Excel：3月/4月/5月直播间数据分析.xlsx                 │
│  - 飞书 Bitable：线索明细 + 排期明细（日常追加）              │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. 数据流全景

### 3.1 看板数据流（日常）

```
Excel/Bitable（新数据）
    ↓
generate_data.py 聚合 + 归因计算
    ↓
dashboard_data.json（中间数据）
    ↓
generate_dashboard.py 渲染 ECharts
    ↓
dashboard.html（本地打开或 Vercel 部署）
```

### 3.2 周报数据流（每周一）

```
飞书 Bitable（最近45天数据）
    ↓ fetch_recent_data()
Python 内存（recent_records）
    ↓
dashboard_data.json（深度归因数据）
    ↓ generate_weekly_report()
Markdown + [CALLOUT] 标记
    ↓ write_rich_doc.write_rich_doc()
飞书 Docx（富文本 block）
    ↓ lark-cli docs +media-insert
飞书 Docx（图表追加）
```

### 3.3 排期数据流（月初）

```
Excel 排期表
    ↓ 手动上传 / 脚本导入
飞书 Bitable（排期明细）
    ↓ autoSchedule / 手动调整
排期结果
    ↓ 多维表格关联分析
品类-线索-排期相关性报告
```

---

## 4. 模块职责详述

### 4.1 看板层（PRD 详情见 [PRD-直播间线索归因复盘看板.md](PRD-直播间线索归因复盘看板.md)）

| 模块 | 职责 | 状态 |
|------|------|------|
| KPI 总览 | 3列卡片：购物车线索、弹幕线索、线级占比 | ✅ v1.0 |
| 日趋势折线 | 3-5月购物车/弹幕日趋势对比 | ✅ v1.0 |
| 品类归因卡片 | 健康线/兴趣变美线品类状态标色（消失/暴跌/下滑/扛住） | ✅ v1.0 |
| 会员等级结构 | V0-V10 占比堆叠柱状图 | ✅ v1.0 |
| 数据发现清单 | 自动生成关键发现（可人工补充） | ✅ v1.0 |
| 归因输入区 | Root Cause + Action Plan 文本框 | ✅ v1.0 |
| 到课率/完课率 | 后链路漏斗（需月底完整数据） | ⏳ v1.1 |
| 投手维度下钻 | 辅助参考维度 | ⏳ v1.1 |

### 4.2 飞书 Agent 层（PRD 详情见 [feishu_agent/PRD.md](feishu_agent/PRD.md)）

| 模块 | 职责 | 状态 |
|------|------|------|
| feishu_client.py | Bitable/Docx/Im API 封装，tenant_token 自动续期 | ✅ |
| write_rich_doc.py | Markdown + `[CALLOUT]` → 飞书 block（block_type 19） | ✅ |
| setup_bitable.py | 初始化多维表格 + 导入历史数据 | ✅ |
| weekly_report.py | 4模块聚焦周报 + 图表生成 + 飞书写入 | ✅ |
| monthly_report.py | 月报（待同步4模块框架） | ⏳ |
| sync_and_build.py | 同步数据 + 生成看板 | ✅ |

### 4.3 数据口径与关键指标

| 指标 | 口径 | 用途 |
|------|------|------|
| 购物车线索 | 直播间购物车领取数 | 核心产值指标 |
| 弹幕线索 | 直播间公屏弹幕领取数 | 一并分析 |
| 同期对比 | 本月1-X日 vs 上月1-X日 | 核心汇报维度 |
| 品类状态 | 消失/暴跌/下滑/扛住/新增 | 归因定位 |
| 目标达成率 | 当前线索数 / 月度目标 | 向上汇报 |
| 预估流水 | 线索数 × LTV（按LTV95计算） | 与90万/110万目标对齐 |

---

## 5. Agent-User 协作协议（协作PRD）

### 5.1 角色分工

| 角色 | 职责 | 不做的事 |
|------|------|----------|
| **用户（业务方）** | 提供业务判断、确认归因结论、补充根因分析、审批排期策略 | 不写代码、不调试API |
| **Agent（Claude）** | 数据处理、看板生成、报告撰写、API调用、故障排查、技术方案设计 | 不做业务决策、不替用户做排期取舍 |

### 5.2 任务分级与执行规范

| 任务类型 | 示例 | 执行方式 |
|----------|------|----------|
| **简单任务**（≤3行改动，无歧义） | 改图表分辨率、修 typo、换颜色 | 直接执行，无需plan |
| **中等任务**（3-10行，有明确目标） | 新增一张图表、修改表格列 | 简要说明方案后执行 |
| **复杂任务**（多文件改动、架构决策） | 重构报告框架、新增数据维度、引入新API | **必须先进入 Plan Mode**，用户审批后执行 |

**Plan Mode 触发条件**（满足任一即触发）：
- 涉及 ≥3 个文件的修改
- 改变现有行为或数据结构
- 引入新的外部依赖或API
- 用户明确要求"你先想想"、"做个方案"、"怎么设计"

### 5.3 Memory 使用规范

**Agent 必须记录**：
- 用户角色与偏好（user）
- 用户纠正过的方案（feedback）
- 项目决策与目标（project）
- 外部系统指针（reference）

**Agent 不记录**：
- 代码具体实现（读代码即可）
- 临时任务状态（用 todo list）
- 已废弃的方案（及时删除或更新）

**关键记忆清单（已持久化）**：
- [user-business-analyst](.claude/projects/.../memory/user-business-analyst.md)：用户偏好聚焦汇报、中文为主、目标导向
- [feedback-reporting-focus](.claude/projects/.../memory/feedback-reporting-focus.md)：同期对比为核心、4模块框架、图表高分辨率
- [feedback-feishu-agent-path](.claude/projects/.../memory/feedback-feishu-agent-path-2026-05-17.md)：执行前必须 cd 到 feishu_agent
- [project-livestream-reporting](.claude/projects/.../memory/project-livestream-reporting.md)：端到端流水线、90万/110万目标
- [reference-feishu-docx-blocks](.claude/projects/.../memory/reference-feishu-docx-blocks.md)：block_type枚举、callout颜色/emoji_id

### 5.4 反馈循环机制

```
Agent 输出 → 用户审阅 → 用户纠偏（"不对，应该是..."）
    ↑                                      ↓
    └──── 下次自动应用 ← 更新 memory ──────┘
```

**用户纠偏优先级**（从高到低）：
1. **数据口径错误**：立即修正并检查同源代码
2. **框架/结构不符**：更新生成模板并重新运行
3. **样式/可视化问题**：调整配置参数（分辨率、颜色等）
4. **文案/措辞偏好**：更新 prompt 模板

### 5.5 关键决策留痕

以下决策必须留痕到 project memory 或 PRD：
- 目标口径变更（如5月目标从线索数改为流水）
- 归因框架调整（如新增/删除归因维度）
- 技术栈变更（如引入新的图表库或部署方式）
- 协作规则调整（如plan触发条件变化）

---

## 6. 配置与凭证管理

| 文件 | 用途 | 安全级别 |
|------|------|----------|
| `config.py` | 配置模板（空值） | 可提交git |
| `config_local.py` | 真实凭证（已被.gitignore排除） | **绝不提交git** |
| GitHub Secrets | CI/CD 运行时的凭证注入 | 加密存储 |

**已配置的飞书资源**：
- Bitable：线索明细（`MsXxbsKlOa4U88sZo5Xcn4penQf` / `tblEGfahdrbX36sq`）
- Bitable：排期明细（`WJjlbgLXLap2arsLLnmcchjsnIc` / `tbl16X2dCTdKCGAL`）
- Docx：周报文档（`Ha74d4aSzoyGVlxONAbcmgNBnMb`）

---

## 7. 扩展路线图

### Phase 1：基础闭环（已完成 ✅）
- [x] 看板生成（dashboard.html）
- [x] 飞书多维表格同步（Bitable）
- [x] 周报自动生成（4模块聚焦框架 + callout + 图表）
- [x] 数据口径对齐（线索数 + 预估流水）

### Phase 2：质量提升（当前 🔨）
- [ ] 月报同步4模块框架
- [ ] 图表类型扩展（KPI仪表盘、品类变化热力图）
- [ ] 飞书文档 grid 布局（KPI卡片并排）
- [ ] 后链路数据接入（到课率/完课率）

### Phase 3：智能化（待规划 ⏳）
- [ ] 异常自动检测（偏离均值2σ自动标红）
- [ ] 策略推荐引擎（基于暴跌品类自动推荐排期调整）
- [ ] 预测模型（基于排期预测下月线索量）
- [ ] 自然语言查询（"为什么5月气血品类跌了？"）

---

## 8. 附录：相关文档索引

| 文档 | 位置 | 内容 |
|------|------|------|
| 看板设计PRD | [PRD-直播间线索归因复盘看板.md](PRD-直播间线索归因复盘看板.md) | UI模块、视觉规范、数据口径、迭代计划 |
| 技能调用PRD | [feishu_agent/PRD.md](feishu_agent/PRD.md) | 技能封装、调用方式、故障排查 |
| 用户上手文档 | [feishu_agent/README.md](feishu_agent/README.md) | 快速开始、配置指南、常见问题 |
| 本地周报样例 | [weekly_report_20260517.md](weekly_report_20260517.md) | 最新生成的周报Markdown备份 |

---

*文档版本：v1.0*
*最后更新：2026-05-17*
*范围：系统架构 + 数据流 + Agent-User协作协议*

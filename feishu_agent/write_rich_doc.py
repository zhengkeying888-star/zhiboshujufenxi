"""
富文本文档写入器
==================
在 Markdown 基础上扩展 callout、divider 等富文本 block，写入飞书文档。

Markdown 扩展语法：
- [CALLOUT red]...[/CALLOUT]    → 红色警示框
- [CALLOUT yellow]...[/CALLOUT] → 黄色提示框
- [CALLOUT green]...[/CALLOUT]  → 绿色正向框
- [CALLOUT blue]...[/CALLOUT]   → 蓝色信息框
- --- 或 ━━━━                   → 分割线

使用方法：
    from write_rich_doc import write_rich_doc
    write_rich_doc(client, doc_id, markdown_content)
"""

import re
from feishu_client import FeishuClient


def parse_markdown_to_blocks(content: str) -> list:
    """解析 Markdown + 扩展语法，返回飞书 block JSON 列表"""
    lines = content.split("\n")
    blocks = []
    i = 0

    callout_pattern = re.compile(r"\[CALLOUT\s+(\w+)\]")

    while i < len(lines):
        line = lines[i]

        # 检测 callout 开始
        m = callout_pattern.match(line)
        if m:
            style = m.group(1)
            callout_lines = []
            i += 1
            while i < len(lines) and lines[i].strip() != "[/CALLOUT]":
                callout_lines.append(lines[i])
                i += 1
            i += 1  # 跳过 [/CALLOUT]

            callout_text = "\n".join(callout_lines).strip()
            blocks.append(_build_callout_block(callout_text, style))
            continue

        # 标题
        if line.startswith("# "):
            blocks.append({
                "block_type": 3,
                "heading1": {"elements": [{"text_run": {"content": line[2:]}}]}
            })
        elif line.startswith("## "):
            blocks.append({
                "block_type": 4,
                "heading2": {"elements": [{"text_run": {"content": line[3:]}}]}
            })
        elif line.startswith("### "):
            blocks.append({
                "block_type": 5,
                "heading3": {"elements": [{"text_run": {"content": line[4:]}}]}
            })
        # 引用
        elif line.startswith("> "):
            blocks.append({
                "block_type": 15,
                "quote": {"elements": [{"text_run": {"content": line[2:]}}]}
            })
        # 空行
        elif line.strip() == "":
            pass
        # 分割线
        elif line.startswith("---") or line.startswith("━━"):
            blocks.append({
                "block_type": 2,
                "text": {"elements": [{"text_run": {"content": "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"}}]}
            })
        # 普通文本
        else:
            blocks.append({
                "block_type": 2,
                "text": {"elements": [{"text_run": {"content": line}}]}
            })
        i += 1

    return blocks


def _build_callout_block(text: str, style: str) -> dict:
    """构建 callout block（颜色使用飞书预设枚举值）"""
    # background_color: 1-15, border_color/text_color: 1-7
    styles = {
        "red": {
            "emoji": "warning",
            "bg": 1,
            "border": 1,
            "text": 1,
        },
        "yellow": {
            "emoji": "bulb",
            "bg": 3,
            "border": 3,
            "text": 3,
        },
        "green": {
            "emoji": "done",
            "bg": 4,
            "border": 4,
            "text": 4,
        },
        "blue": {
            "emoji": "info",
            "bg": 5,
            "border": 5,
            "text": 5,
        },
    }
    s = styles.get(style, styles["yellow"])

    # 把 text 按行拆分 elements
    elements = []
    for t in text.split("\n"):
        if t.strip():
            elements.append({"text_run": {"content": t}})

    return {
        "block_type": 19,
        "callout": {
            "emoji_id": s["emoji"],
            "background_color": s["bg"],
            "border_color": s["border"],
            "text_color": s["text"],
            "elements": elements
        }
    }


def write_rich_doc(client: FeishuClient, document_id: str, content: str) -> None:
    """把富文本内容写入飞书文档（分批，每批最多50个块）"""
    doc_blocks = client.get_doc_blocks(document_id)
    if not doc_blocks:
        raise RuntimeError("无法获取文档块")
    root_block_id = doc_blocks[0]["block_id"]

    blocks = parse_markdown_to_blocks(content)

    batch_size = 50
    for i in range(0, len(blocks), batch_size):
        batch = blocks[i:i + batch_size]
        client.append_doc_blocks(document_id, root_block_id, batch)
        print(f"   已写入块 {i+1}-{min(i+batch_size, len(blocks))} / {len(blocks)}")

    print(f"✅ 已写入 {len(blocks)} 个富文本块到飞书文档")

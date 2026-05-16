"""
飞书 OpenAPI 封装客户端
支持：Bitable、Docx、Im 三大模块
"""

import requests
import time
from typing import List, Dict, Any, Optional

FEISHU_API_BASE = "https://open.feishu.cn/open-apis"


class FeishuClient:
    def __init__(self, app_id: str, app_secret: str):
        self.app_id = app_id
        self.app_secret = app_secret
        self._tenant_token = None
        self._token_expire = 0

    # --------------------------- 认证 ---------------------------

    def _get_tenant_token(self) -> str:
        """获取 tenant_access_token，带缓存"""
        if self._tenant_token and time.time() < self._token_expire - 60:
            return self._tenant_token

        url = f"{FEISHU_API_BASE}/auth/v3/tenant_access_token/internal"
        resp = requests.post(url, json={"app_id": self.app_id, "app_secret": self.app_secret})
        resp.raise_for_status()
        data = resp.json()
        if data.get("code") != 0:
            raise RuntimeError(f"获取 tenant_token 失败: {data}")

        self._tenant_token = data["tenant_access_token"]
        self._token_expire = time.time() + data["expire"]
        return self._tenant_token

    def _headers(self) -> Dict[str, str]:
        return {"Authorization": f"Bearer {self._get_tenant_token()}", "Content-Type": "application/json"}

    def _request(self, method: str, path: str, **kwargs) -> Dict[str, Any]:
        """通用请求封装"""
        url = f"{FEISHU_API_BASE}{path}"
        headers = kwargs.pop("headers", {})
        headers.update(self._headers())
        resp = requests.request(method, url, headers=headers, **kwargs)
        resp.raise_for_status()
        result = resp.json()
        if result.get("code") != 0:
            raise RuntimeError(f"飞书API错误 [{path}]: {result}")
        return result.get("data", result)

    # --------------------------- Bitable ---------------------------

    def create_bitable(self, name: str, folder_token: Optional[str] = None) -> str:
        """创建多维表格，返回 app_token"""
        payload = {"name": name}
        if folder_token:
            payload["folder_token"] = folder_token
        data = self._request("POST", "/bitable/v1/apps", json=payload)
        return data["app"]["app_token"]

    def create_table(self, app_token: str, name: str, description: str = "") -> str:
        """在多维表格中创建数据表，返回 table_id"""
        payload = {"table": {"name": name, "description": description}}
        data = self._request("POST", f"/bitable/v1/apps/{app_token}/tables", json=payload)
        return data["table_id"]

    def create_field(self, app_token: str, table_id: str, field_name: str, field_type: int,
                     property: Optional[Dict] = None) -> str:
        """
        创建字段
        field_type 常用值：
          1=文本, 2=数字, 3=单选, 4=多选, 5=日期, 7=复选框, 11=人员, 13=电话, 15=超链接, 17=附件, 20=公式, 22=地理位置, 23=群组
        """
        payload = {"field_name": field_name, "type": field_type}
        if property:
            payload["property"] = property
        data = self._request("POST", f"/bitable/v1/apps/{app_token}/tables/{table_id}/fields", json=payload)
        return data["field"]["field_id"]

    def batch_create_records(self, app_token: str, table_id: str, records: List[Dict]) -> List[str]:
        """批量创建记录（每次最多500条），返回 record_id 列表"""
        record_ids = []
        batch_size = 500
        for i in range(0, len(records), batch_size):
            batch = records[i:i + batch_size]
            payload = {"records": [{"fields": r} for r in batch]}
            data = self._request("POST", f"/bitable/v1/apps/{app_token}/tables/{table_id}/records/batch_create", json=payload)
            record_ids.extend([r["record_id"] for r in data.get("records", [])])
        return record_ids

    def query_records(self, app_token: str, table_id: str, filter_str: Optional[str] = None,
                      page_size: int = 500) -> List[Dict]:
        """查询所有记录（自动分页）"""
        all_records = []
        page_token = None
        while True:
            params = {"page_size": page_size}
            if page_token:
                params["page_token"] = page_token
            if filter_str:
                params["filter"] = filter_str
            data = self._request("GET", f"/bitable/v1/apps/{app_token}/tables/{table_id}/records", params=params)
            items = data.get("items", [])
            all_records.extend(items)
            if not data.get("has_more"):
                break
            page_token = data.get("page_token")
        return all_records

    def update_records(self, app_token: str, table_id: str, records: List[Dict[str, Any]]) -> None:
        """批量更新记录（每次最多500条）"""
        batch_size = 500
        for i in range(0, len(records), batch_size):
            batch = records[i:i + batch_size]
            payload = {"records": batch}
            self._request("POST", f"/bitable/v1/apps/{app_token}/tables/{table_id}/records/batch_update", json=payload)

    def delete_records(self, app_token: str, table_id: str, record_ids: List[str]) -> None:
        """批量删除记录（每次最多500条）"""
        batch_size = 500
        for i in range(0, len(record_ids), batch_size):
            batch = record_ids[i:i + batch_size]
            payload = {"records": batch}
            self._request("POST", f"/bitable/v1/apps/{app_token}/tables/{table_id}/records/batch_delete", json=payload)

    def get_tables(self, app_token: str) -> List[Dict]:
        """获取多维表格下的所有数据表"""
        data = self._request("GET", f"/bitable/v1/apps/{app_token}/tables")
        return data.get("items", [])

    def get_fields(self, app_token: str, table_id: str) -> List[Dict]:
        """获取数据表的所有字段"""
        data = self._request("GET", f"/bitable/v1/apps/{app_token}/tables/{table_id}/fields")
        return data.get("items", [])

    # --------------------------- Docx ---------------------------

    def create_doc(self, title: str, folder_token: Optional[str] = None) -> str:
        """创建文档，返回 document_id"""
        payload = {"title": title}
        if folder_token:
            payload["folder_token"] = folder_token
        data = self._request("POST", "/docx/v1/documents", json=payload)
        return data["document"]["document_id"]

    def get_doc_blocks(self, document_id: str) -> List[Dict]:
        """获取文档的所有块（用于找到根块ID）"""
        data = self._request("GET", f"/docx/v1/documents/{document_id}/blocks")
        return data.get("items", [])

    def append_doc_blocks(self, document_id: str, block_id: str, blocks: List[Dict]) -> None:
        """在指定块后面追加内容块"""
        payload = {"children": blocks}
        self._request("POST", f"/docx/v1/documents/{document_id}/blocks/{block_id}/children", json=payload)

    # --------------------------- Im ---------------------------

    def send_text_message(self, chat_id: str, text: str) -> None:
        """发送文本消息到群聊"""
        payload = {
            "receive_id": chat_id,
            "msg_type": "text",
            "content": json.dumps({"text": text})
        }
        self._request("POST", "/im/v1/messages", json=payload)

    def send_rich_message(self, chat_id: str, title: str, content: str, url: Optional[str] = None) -> None:
        """发送富文本卡片消息"""
        card = {
            "config": {"wide_screen_mode": True},
            "header": {"title": {"tag": "plain_text", "content": title}, "template": "blue"},
            "elements": [
                {"tag": "div", "text": {"tag": "lark_md", "content": content}}
            ]
        }
        if url:
            card["elements"].append({
                "tag": "action",
                "actions": [{"tag": "button", "text": {"tag": "plain_text", "content": "点击查看"}, "type": "primary", "url": url}]
            })
        payload = {
            "receive_id": chat_id,
            "msg_type": "interactive",
            "content": json.dumps(card)
        }
        self._request("POST", "/im/v1/messages", json=payload)

    def get_chat_list(self) -> List[Dict]:
        """获取机器人所在的群聊列表"""
        data = self._request("GET", "/im/v1/chats", params={"page_size": 100})
        return data.get("items", [])


import json

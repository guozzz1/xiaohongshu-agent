"""
飞书客户端模块 - 用于数据存储到飞书多维表格
"""
from typing import Any, Dict, Optional, Set
from urllib.parse import quote

import requests

from config import FEISHU_APP_ID, FEISHU_APP_SECRET, FEISHU_APP_TOKEN, FEISHU_TABLE_ID
from models import Note


class FeishuClient:
    """飞书多维表格客户端"""

    def __init__(self, app_id: str = None, app_secret: str = None, app_token: str = None, table_id: str = None):
        self.app_id = app_id or FEISHU_APP_ID
        self.app_secret = app_secret or FEISHU_APP_SECRET
        self.app_token = app_token or FEISHU_APP_TOKEN
        self.table_id = table_id or FEISHU_TABLE_ID
        self.tenant_access_token: Optional[str] = None
        self._table_fields: Optional[Set[str]] = None

    def _auth(self) -> str:
        """获取租户访问令牌"""
        if self.tenant_access_token:
            return self.tenant_access_token
        url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
        resp = requests.post(url, json={"app_id": self.app_id, "app_secret": self.app_secret}, timeout=20)
        resp.raise_for_status()
        data = resp.json()
        if data.get("code", -1) != 0:
            raise RuntimeError(f"飞书鉴权失败: {data}")
        self.tenant_access_token = data["tenant_access_token"]
        return self.tenant_access_token

    def _headers(self) -> Dict[str, str]:
        """获取请求头"""
        token = self._auth()
        return {"Authorization": f"Bearer {token}", "Content-Type": "application/json; charset=utf-8"}

    def _fields(self, note: Note) -> Dict[str, Any]:
        """将Note对象转换为飞书字段"""
        return {
            "采集日期": note.collect_date,
            "采集方式": note.collect_method,
            "来源关键词": note.source_keyword,
            "原笔记链接": note.note_url,
            "原笔记发布时间": note.publish_time,
            "原笔记点赞数": note.likes,
            "原笔记收藏数": note.favorites,
            "原笔记评论数": note.comments,
            "原笔记标题": note.title,
            "原笔记正文": note.content,
            "原笔记标签": note.original_tags,
            "原笔记图片（截图/有效链接）": note.image_urls,
            "可二创方向": note.direction,
            "内容分析": note.analysis,
            "二创标题": note.rewritten_title,
            "二创正文": note.rewritten_content,
            "二创封面": note.rewritten_cover,
        }

    def _fetch_table_fields(self) -> Set[str]:
        """获取表格字段列表"""
        if self._table_fields is not None:
            return self._table_fields
        url = (
            f"https://open.feishu.cn/open-apis/bitable/v1/apps/{self.app_token}/tables/"
            f"{self.table_id}/fields?page_size=500"
        )
        resp = requests.get(url, headers=self._headers(), timeout=30)
        resp.raise_for_status()
        data = resp.json()
        if data.get("code", -1) != 0:
            raise RuntimeError(f"飞书字段读取失败: {data}")
        items = data.get("data", {}).get("items", [])
        self._table_fields = {str(i.get("field_name", "")).strip() for i in items if i.get("field_name")}
        return self._table_fields

    def _sanitize_fields(self, fields: Dict[str, Any]) -> Dict[str, Any]:
        """过滤字段，只保留表格中存在的字段"""
        existing = self._fetch_table_fields()
        sanitized: Dict[str, Any] = {}
        for k, v in fields.items():
            if k not in existing:
                continue
            sanitized[k] = self._normalize_field_value(v)
        return sanitized

    def _normalize_field_value(self, v: Any) -> Any:
        """规范化字段值"""
        if v is None:
            return ""
        if isinstance(v, (int, float, bool)):
            return str(v)
        return v

    def find_record_by_url(self, note_url: str) -> Optional[str]:
        """根据笔记URL查找记录ID"""
        query = quote(f'CurrentValue.[原笔记链接] = "{note_url}"')
        url = (
            f"https://open.feishu.cn/open-apis/bitable/v1/apps/{self.app_token}/tables/"
            f"{self.table_id}/records?filter={query}&page_size=1"
        )
        resp = requests.get(url, headers=self._headers(), timeout=30)
        resp.raise_for_status()
        data = resp.json()
        if data.get("code", -1) != 0:
            raise RuntimeError(f"飞书查询失败: {data}")
        items = data.get("data", {}).get("items", [])
        return items[0]["record_id"] if items else None

    def upsert_record(self, note: Note) -> str:
        """更新或插入记录"""
        fields = self._sanitize_fields(self._fields(note))
        if not fields:
            raise RuntimeError("飞书表没有匹配字段，无法写入")
        record_id = self.find_record_by_url(note.note_url)
        if record_id:
            url = (
                f"https://open.feishu.cn/open-apis/bitable/v1/apps/{self.app_token}/tables/"
                f"{self.table_id}/records/{record_id}"
            )
            resp = requests.put(url, headers=self._headers(), json={"fields": fields}, timeout=30)
            resp.raise_for_status()
            return record_id
        url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{self.app_token}/tables/{self.table_id}/records"
        resp = requests.post(url, headers=self._headers(), json={"fields": fields}, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        if data.get("code", -1) != 0:
            raise RuntimeError(f"飞书新增失败: {data}")
        return data["data"]["record"]["record_id"]

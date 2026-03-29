"""
数据模型模块 - 定义所有数据结构
"""
from dataclasses import dataclass
from typing import Optional


@dataclass
class Note:
    """笔记数据模型"""
    collect_date: str
    collect_method: str
    source_keyword: str
    note_url: str
    publish_time: str
    likes: int
    favorites: int
    comments: int
    title: str
    content: str
    original_tags: str
    image_urls: str
    direction: str = ""
    analysis: str = ""
    rewritten_title: str = ""
    rewritten_content: str = ""
    rewritten_cover: str = ""
    rewritten_tags: str = ""

    def to_dict(self) -> dict:
        """转换为字典格式"""
        return {
            "采集日期": self.collect_date,
            "采集方式": self.collect_method,
            "来源关键词": self.source_keyword,
            "原笔记链接": self.note_url,
            "原笔记发布时间": self.publish_time,
            "原笔记点赞数": self.likes,
            "原笔记收藏数": self.favorites,
            "原笔记评论数": self.comments,
            "原笔记标题": self.title,
            "原笔记正文": self.content,
            "原笔记标签": self.original_tags,
            "原笔记图片（截图/有效链接）": self.image_urls,
            "可二创方向": self.direction,
            "内容分析": self.analysis,
            "二创标题": self.rewritten_title,
            "二创正文": self.rewritten_content,
            "二创封面": self.rewritten_cover,
        }

    def is_valid(self, strict_comment_filter: bool = False, min_comments: int = 200) -> bool:
        """验证笔记是否有效"""
        if not self.note_url or not self.note_url.startswith("http"):
            return False
        if strict_comment_filter and self.comments < min_comments:
            return False
        # 检查主题相关性
        from config import TOPIC_REQUIRED
        text = f"{self.title} {self.content}"
        if not any(k in text for k in TOPIC_REQUIRED):
            return False
        return True

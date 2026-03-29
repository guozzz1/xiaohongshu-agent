"""
大模型客户端模块 - 支持多种AI模型进行智能二创
"""
import json
import re
from typing import Dict

import requests

from config import (
    LLM_API_TYPE,
    LLM_API_KEY,
    LLM_API_BASE_URL,
    LLM_MODEL,
    LLM_TEMPERATURE,
    LLM_MAX_TOKENS,
)
from models import Note


class LLMClient:
    """大模型API客户端，支持多种AI模型进行智能二创"""

    def __init__(self):
        self.api_type = LLM_API_TYPE
        self.api_key = LLM_API_KEY
        self.api_base_url = LLM_API_BASE_URL
        self.model = LLM_MODEL
        self.temperature = LLM_TEMPERATURE
        self.max_tokens = LLM_MAX_TOKENS

        if not self.api_key:
            raise RuntimeError("未配置 LLM_API_KEY，无法使用大模型二创功能")

    def _get_headers(self) -> Dict[str, str]:
        """获取API请求头"""
        if self.api_type == "azure":
            return {"api-key": self.api_key, "Content-Type": "application/json"}
        else:
            return {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

    def _build_prompt(self, note: Note) -> str:
        """构建二创提示词"""
        return f"""你是一个专业的新媒体内容创作者，擅长分析和改写招聘类笔记。

原始笔记信息：
标题：{note.title}
内容：{note.content}
标签：{note.original_tags}
点赞数：{note.likes}
评论数：{note.comments}
收藏数：{note.favorites}

请根据原始笔记的内容和风格，进行智能二创：
1. 分析原始笔记的核心卖点和风格特点
2. 生成一个全新的标题（20字以内），必须保留原标题的核心关键词和风格，不要偏离主题
3. 生成全新的正文内容（保持相似风格但内容不同）
4. 生成相关的标签（不超过10个）

要求：
- 标题必须基于原标题改写，保留城市/岗位/薪资等核心词，风格与原标题相似
- 保持原始笔记的招聘主题和风格
- 内容要有吸引力和转化率
- 符合小红书平台的调性
- 标题要抓眼球，正文要有层次感

请按以下JSON格式返回：
{{
    "title": "新标题",
    "content": "新正文内容",
    "tags": "#标签1 #标签2 #标签3",
    "analysis": "内容分析",
    "direction": "二创方向建议"
}}"""

    def generate_rewrite(self, note: Note) -> Dict[str, str]:
        """调用大模型API生成二创内容"""
        prompt = self._build_prompt(note)

        if self.api_type == "openai":
            return self._call_openai(prompt)
        elif self.api_type == "azure":
            return self._call_azure(prompt)
        elif self.api_type == "qwen":
            return self._call_qwen(prompt)
        elif self.api_type == "deepseek":
            return self._call_deepseek(prompt)
        elif self.api_type == "moonshot":
            return self._call_moonshot(prompt)
        else:
            raise RuntimeError(f"不支持的API类型: {self.api_type}")

    def _call_openai(self, prompt: str) -> Dict[str, str]:
        """调用OpenAI API"""
        url = f"{self.api_base_url}/chat/completions"
        data = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "你是一个专业的新媒体内容创作者"},
                {"role": "user", "content": prompt}
            ],
            "temperature": self.temperature,
            "max_tokens": self.max_tokens
        }

        response = requests.post(url, headers=self._get_headers(), json=data, timeout=30)
        response.raise_for_status()
        result = response.json()

        content = result["choices"][0]["message"]["content"]
        return self._parse_response(content)

    def _call_azure(self, prompt: str) -> Dict[str, str]:
        """调用Azure OpenAI API"""
        url = f"{self.api_base_url}/chat/completions?api-version=2023-05-15"
        data = {
            "messages": [
                {"role": "system", "content": "你是一个专业的新媒体内容创作者"},
                {"role": "user", "content": prompt}
            ],
            "temperature": self.temperature,
            "max_tokens": self.max_tokens
        }

        response = requests.post(url, headers=self._get_headers(), json=data, timeout=30)
        response.raise_for_status()
        result = response.json()

        content = result["choices"][0]["message"]["content"]
        return self._parse_response(content)

    def _call_qwen(self, prompt: str) -> Dict[str, str]:
        """调用通义千问API"""
        url = f"{self.api_base_url}/v1/chat/completions"
        data = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "你是一个专业的新媒体内容创作者"},
                {"role": "user", "content": prompt}
            ],
            "temperature": self.temperature,
            "max_tokens": self.max_tokens
        }

        response = requests.post(url, headers=self._get_headers(), json=data, timeout=30)
        response.raise_for_status()
        result = response.json()

        content = result["output"]["text"]
        return self._parse_response(content)

    def _call_deepseek(self, prompt: str) -> Dict[str, str]:
        """调用DeepSeek API"""
        url = f"{self.api_base_url}/chat/completions"
        data = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "你是一个专业的新媒体内容创作者"},
                {"role": "user", "content": prompt}
            ],
            "temperature": self.temperature,
            "max_tokens": self.max_tokens
        }

        response = requests.post(url, headers=self._get_headers(), json=data, timeout=30)
        response.raise_for_status()
        result = response.json()

        content = result["choices"][0]["message"]["content"]
        return self._parse_response(content)

    def _call_moonshot(self, prompt: str) -> Dict[str, str]:
        """调用Moonshot AI API"""
        url = f"{self.api_base_url}/chat/completions"
        data = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "你是一个专业的新媒体内容创作者"},
                {"role": "user", "content": prompt}
            ],
            "temperature": self.temperature,
            "max_tokens": self.max_tokens
        }

        response = requests.post(url, headers=self._get_headers(), json=data, timeout=30)
        response.raise_for_status()
        result = response.json()

        content = result["choices"][0]["message"]["content"]
        return self._parse_response(content)

    def _parse_response(self, content: str) -> Dict[str, str]:
        """解析API返回的JSON内容"""
        def _extract(raw: str) -> Dict[str, str]:
            result = json.loads(raw)
            return {
                "title": result.get("title", ""),
                "content": result.get("content", ""),
                "tags": result.get("tags", ""),
                "analysis": result.get("analysis", ""),
                "direction": result.get("direction", "")
            }

        # 1. 直接解析
        try:
            return _extract(content)
        except (json.JSONDecodeError, ValueError):
            pass

        # 2. 去掉 markdown 代码块后解析
        stripped = re.sub(r'^```[a-z]*\s*|\s*```$', '', content.strip(), flags=re.MULTILINE).strip()
        try:
            return _extract(stripped)
        except (json.JSONDecodeError, ValueError):
            pass

        # 3. 从文本中提取第一个 {...} 块
        json_match = re.search(r'\{.*\}', content, re.DOTALL)
        if json_match:
            try:
                return _extract(json_match.group())
            except (json.JSONDecodeError, ValueError):
                pass

        # 4. 兜底：尝试从原文按行提取各字段
        title = ""
        title_match = re.search(r'["\u2018\u2019]?title["\u2018\u2019]?\s*[::\uff1a]\s*["\u2018\u2019]?([^"\u2018\u2019\n,}]{1,20})', content)
        if title_match:
            title = title_match.group(1).strip().rstrip('"\',')
        return {
            "title": title,
            "content": content,
            "tags": "",
            "analysis": "",
            "direction": ""
        }

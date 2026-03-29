import asyncio
import base64
import json
import os
import random
import shutil
import re
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
from urllib.parse import parse_qs, parse_qsl, quote, urlencode, urlparse, urlunparse

import requests
from apscheduler.schedulers.blocking import BlockingScheduler
from dotenv import load_dotenv
from playwright.async_api import BrowserContext, Page, async_playwright


class LLMClient:
    """大模型API客户端，支持多种AI模型进行智能二创"""
    
    def __init__(self):
        self.api_type = os.getenv("LLM_API_TYPE", "openai").lower()
        self.api_key = os.getenv("LLM_API_KEY", "")
        self.api_base_url = os.getenv("LLM_API_BASE_URL", "https://api.openai.com/v1")
        self.model = os.getenv("LLM_MODEL", "gpt-3.5-turbo")
        self.temperature = float(os.getenv("LLM_TEMPERATURE", "0.7"))
        self.max_tokens = int(os.getenv("LLM_MAX_TOKENS", "1000"))
        
        if not self.api_key:
            raise RuntimeError("未配置 LLM_API_KEY，无法使用大模型二创功能")
    
    def _get_headers(self):
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
2. 生成一个全新的标题（20字以内）
3. 生成全新的正文内容（保持相似风格但内容不同）
4. 生成相关的标签（不超过10个）

要求：
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
        try:
            # 尝试直接解析JSON
            result = json.loads(content)
            return {
                "title": result.get("title", ""),
                "content": result.get("content", ""),
                "tags": result.get("tags", ""),
                "analysis": result.get("analysis", ""),
                "direction": result.get("direction", "")
            }
        except json.JSONDecodeError:
            # 如果直接解析失败，尝试从文本中提取JSON
            import re
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                try:
                    result = json.loads(json_match.group())
                    return {
                        "title": result.get("title", ""),
                        "content": result.get("content", ""),
                        "tags": result.get("tags", ""),
                        "analysis": result.get("analysis", ""),
                        "direction": result.get("direction", "")
                    }
                except:
                    pass
            
            # 如果无法解析JSON，返回原始内容
            return {
                "title": "智能二创标题",
                "content": content,
                "tags": "#智能二创 #AI生成",
                "analysis": "大模型自动生成内容",
                "direction": "基于AI的智能二创"
            }


load_dotenv()

# 可选：为小红书 API 请求注入 x-s/x-t/x-s-common 签名（需配置 XHS_COOKIES_JSON 含 web_session）
try:
    from xhshow import Xhshow

    _XHSHOW_AVAILABLE = True
except ImportError:
    _XHSHOW_AVAILABLE = False


CORE_KEYWORDS = ["招聘", "招人", "招募", "急招", "直招", "主播", "带货主播", "直播", "运营", "助理", "中控", "场控"]
CITY_KEYWORDS = ["深圳", "杭州", "广州", "上海", "成都", "北京", "苏州", "武汉", "南京", "重庆"]
ROLE_KEYWORDS = ["主播助理", "直播运营", "中控", "场控", "带货主播"]
ACTION_KEYWORDS = ["急招", "直招", "内推", "团队直招", "公司招人"]
SCENE_KEYWORDS = ["直播间招人", "带货团队招募", "新人主播招聘", "兼职主播招募"]
TOPIC_REQUIRED = ["主播", "直播", "招聘", "招人", "带货", "运营", "助理", "中控", "场控"]
MANDATORY_TAGS = ["#深圳", "#深圳找工作", "#深圳主播招聘", "#深圳招人", "#主播招聘", "#直播岗位"]
DEFAULT_APPEND_TAGS = ["#深圳同城招聘", "#带货主播招募", "#直播运营招聘", "#深圳电商"]

# 1x1 透明 PNG，用于 target=image 时先触发「已选图」再出现标题/正文区
_MIN_PNG_B64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)


def _write_minimal_png(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(base64.b64decode(_MIN_PNG_B64))


def _coerce_publish_url_target_image(url: str) -> str:
    """创作者发布页 query 强制 target=image（上传图文），与创作平台实际入口一致。"""
    s = (url or "").strip()
    if not s:
        return "https://creator.xiaohongshu.com/publish/publish?from=menu&target=image"
    p = urlparse(s)
    pairs = list(parse_qsl(p.query, keep_blank_values=True))
    has_target = False
    out_pairs: List[Tuple[str, str]] = []
    for k, v in pairs:
        if k == "target":
            out_pairs.append(("target", "image"))
            has_target = True
        else:
            out_pairs.append((k, v))
    if not has_target:
        out_pairs.append(("target", "image"))
    new_q = urlencode(out_pairs)
    return urlunparse((p.scheme, p.netloc, p.path, p.params, new_q, p.fragment))


ROOT = Path(__file__).resolve().parent
ARTIFACTS = ROOT / "artifacts"
LOG_DIR = ARTIFACTS / "logs"
SHOT_DIR = ARTIFACTS / "screenshots"
VIDEO_DIR = ARTIFACTS / "videos"
for p in [LOG_DIR, SHOT_DIR, VIDEO_DIR]:
    p.mkdir(parents=True, exist_ok=True)


@dataclass
class Note:
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


class RunLogger:
    def __init__(self):
        self.run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_file = LOG_DIR / f"run_{self.run_id}.jsonl"

    def log(self, stage: str, message: str, extra: Optional[Dict[str, Any]] = None) -> None:
        payload = {
            "time": datetime.now().isoformat(timespec="seconds"),
            "stage": stage,
            "message": message,
            "extra": extra or {},
        }
        with self.log_file.open("a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False) + "\n")
        print(f"[{stage}] {message}")


class FeishuClient:
    def __init__(self, app_id: str, app_secret: str, app_token: str, table_id: str):
        self.app_id = app_id
        self.app_secret = app_secret
        self.app_token = app_token
        self.table_id = table_id
        self.tenant_access_token: Optional[str] = None
        self._table_fields: Optional[Set[str]] = None

    def _auth(self) -> str:
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
        token = self._auth()
        return {"Authorization": f"Bearer {token}", "Content-Type": "application/json; charset=utf-8"}

    def _fields(self, note: Note) -> Dict[str, Any]:
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
        existing = self._fetch_table_fields()
        sanitized: Dict[str, Any] = {}
        for k, v in fields.items():
            if k not in existing:
                continue
            sanitized[k] = self._normalize_field_value(v)
        return sanitized

    def _normalize_field_value(self, v: Any) -> Any:
        if v is None:
            return ""
        if isinstance(v, (int, float, bool)):
            return str(v)
        return v

    def find_record_by_url(self, note_url: str) -> Optional[str]:
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


class XhsAgent:
    def __init__(self):
        self.daily_target = int(os.getenv("DAILY_TARGET", "20"))
        self.min_comments = int(os.getenv("MIN_COMMENTS", "200"))
        self.strict_comment_filter = os.getenv("STRICT_COMMENT_FILTER", "1").strip() == "1"
        self.max_retry = int(os.getenv("MAX_RETRY", "3"))
        self.search_wait_ms = int(os.getenv("SEARCH_WAIT_MS", "2600"))
        self.browser_channel = os.getenv("BROWSER_CHANNEL", "msedge").strip() or "msedge"
        self.captcha_wait_seconds = int(os.getenv("CAPTCHA_WAIT_SECONDS", "180"))
        self.headless = os.getenv("HEADLESS", "0").strip() == "1"
        self.min_request_interval = float(os.getenv("MIN_REQUEST_INTERVAL_SECONDS", "2.2"))
        self.max_request_interval = float(os.getenv("MAX_REQUEST_INTERVAL_SECONDS", "5.8"))
        self.rate_limit_cooldown = int(os.getenv("RATE_LIMIT_COOLDOWN_SECONDS", "90"))
        self.max_rate_limit_retry = int(os.getenv("MAX_RATE_LIMIT_RETRY", "3"))
        self.login_wait_seconds = int(os.getenv("LOGIN_WAIT_SECONDS", "180"))
        self.require_interactive_login = os.getenv("REQUIRE_INTERACTIVE_LOGIN", "0").strip() == "1"
        self.goto_timeout_ms = int(os.getenv("GOTO_TIMEOUT_MS", "90000"))
        self.search_goto_retry = int(os.getenv("SEARCH_GOTO_RETRY", "3"))
        self.persistent_user_data_dir = os.getenv("PERSISTENT_USER_DATA_DIR", "").strip()
        # 默认上传图文（target=image）；article/video 等流与图文标题 DOM 不一致
        _default_pub = "https://creator.xiaohongshu.com/publish/publish?from=menu&target=image"
        _pub_raw = os.getenv("XHS_PUBLISH_PAGE_URL", _default_pub).strip() or _default_pub
        if "creator.xiaohongshu.com" in _pub_raw and "/publish" in _pub_raw:
            self.publish_page_url = _coerce_publish_url_target_image(_pub_raw)
        else:
            self.publish_page_url = _pub_raw
        fallback_raw = os.getenv("FALLBACK_NOTE_URLS", "").strip()
        self.fallback_note_urls = [u.strip() for u in fallback_raw.split(",") if u.strip()]
        self.logger = RunLogger()
        # 初始化大模型客户端（如果配置了API密钥）
        self.llm_client = None
        if os.getenv("LLM_API_KEY"):
            try:
                self.llm_client = LLMClient()
                self.logger.log("config", "大模型API客户端已初始化", {"api_type": os.getenv("LLM_API_TYPE", "openai")})
            except Exception as e:
                self.logger.log("config", "大模型API客户端初始化失败，使用模板二创", {"error": str(e)})
        if _pub_raw != self.publish_page_url:
            self.logger.log(
                "config",
                "XHS_PUBLISH_PAGE_URL 已规范为上传图文 target=image",
                {"before": _pub_raw[:240], "after": self.publish_page_url[:240]},
            )
        self.feishu = FeishuClient(
            app_id=os.getenv("FEISHU_APP_ID", ""),
            app_secret=os.getenv("FEISHU_APP_SECRET", ""),
            app_token=os.getenv("FEISHU_APP_TOKEN", ""),
            table_id=os.getenv("FEISHU_TABLE_ID", ""),
        )
        self.seen_urls: Set[str] = set()
        self.selectors = self._load_selectors()
        self._cookie_dict: Optional[Dict[str, str]] = None
        self.connect_cdp_url = os.getenv("CONNECT_CDP_URL", "").strip()
        self.stealth_browser = os.getenv("STEALTH_BROWSER", "1").strip() == "1"
        # target=image 时须先选图才会出现标题框；可用自定义图或内置 1x1 PNG
        self.skip_publish_placeholder_upload = os.getenv("SKIP_PUBLISH_PLACEHOLDER_UPLOAD", "0").strip() == "1"
        self.publish_placeholder_image_count = max(1, min(9, int(os.getenv("PUBLISH_PLACEHOLDER_IMAGE_COUNT", "2"))))
        self.publish_placeholder_image_path = os.getenv("PUBLISH_PLACEHOLDER_IMAGE_PATH", "").strip()

    def _prepare_publish_placeholder_files(self, work_dir: Path) -> List[str]:
        work_dir.mkdir(parents=True, exist_ok=True)
        n = self.publish_placeholder_image_count
        custom = self.publish_placeholder_image_path
        if custom:
            src = Path(custom).expanduser()
            if src.is_file():
                paths: List[str] = []
                for i in range(n):
                    dst = work_dir / f"_xhs_ph_{i}{src.suffix or '.png'}"
                    shutil.copy2(src, dst)
                    paths.append(str(dst))
                return paths
        out: List[str] = []
        for i in range(n):
            p = work_dir / f"_xhs_placeholder_{i}.png"
            _write_minimal_png(p)
            out.append(str(p))
        return out

    def _publish_target_frame(self, page: Page):
        """锁定创作者发布相关 frame（若有），否则用主页面。"""
        for f in page.frames:
            u = f.url or ""
            if "creator.xiaohongshu.com" in u and "publish" in u:
                return f
        return page

    def _download_image_to_file(self, url: str, dest: Path) -> bool:
        try:
            r = requests.get(
                url,
                timeout=45,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
            )
            r.raise_for_status()
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(r.content)
            return True
        except Exception as e:
            self.logger.log("publish_fill", "下载图片失败", {"url": url[:100], "error": str(e)[:120]})
            return False

    def _resolve_image_files_for_publish(self, note: Note, work_dir: Path) -> List[str]:
        """解析发布用本地图片路径：优先 PUBLISH_IMAGE_PATHS，其次 note.image_urls（本地路径或 http 下载），否则占位图。"""
        work_dir.mkdir(parents=True, exist_ok=True)
        env_paths = os.getenv("PUBLISH_IMAGE_PATHS", "").strip()
        if env_paths:
            out = [
                str(Path(p.strip()).expanduser().resolve())
                for p in env_paths.split(",")
                if p.strip() and Path(p.strip()).expanduser().is_file()
            ]
            if out:
                self.logger.log("publish_fill", "使用 PUBLISH_IMAGE_PATHS", {"count": len(out[:9])})
                return out[:9]
        paths: List[str] = []
        raw = (note.image_urls or "").strip()
        for part in raw.replace("\n", ",").split(","):
            part = part.strip()
            if not part:
                continue
            lp = Path(part).expanduser()
            if lp.is_file():
                paths.append(str(lp.resolve()))
            elif part.startswith("http://") or part.startswith("https://"):
                ext = ".jpg"
                low = part.lower()
                if ".png" in low or "format=png" in low:
                    ext = ".png"
                elif ".webp" in low:
                    ext = ".webp"
                dest = work_dir / f"note_img_{len(paths)}{ext}"
                if self._download_image_to_file(part, dest):
                    paths.append(str(dest))
            if len(paths) >= 9:
                break
        if not paths:
            if self.skip_publish_placeholder_upload:
                raise RuntimeError(
                    "SKIP_PUBLISH_PLACEHOLDER_UPLOAD=1 时须配置 PUBLISH_IMAGE_PATHS，"
                    "或在 note.image_urls 中填写本地图片路径/可下载的图片 URL"
                )
            self.logger.log("publish_fill", "无可用图片路径/URL，使用内置占位图", {})
            return self._prepare_publish_placeholder_files(work_dir)
        return paths

    def _stealth_launch_kwargs(self) -> Dict[str, Any]:
        """降低被识别为自动化浏览器（仍可能被服务端风控）。"""
        if not self.stealth_browser:
            return {}
        return {
            "args": [
                "--disable-blink-features=AutomationControlled",
                "--disable-infobars",
            ],
            "ignore_default_args": ["--enable-automation"],
        }

    async def _apply_stealth_to_context(self, context: BrowserContext) -> None:
        await context.add_init_script(
            """
            (() => {
              try {
                Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
              } catch (e) {}
              if (!window.chrome) window.chrome = { runtime: {} };
            })();
            """
        )

    async def _launch_browser(self, playwright, headless: bool):
        # 优先复用本机浏览器通道，避免受外网下载限制
        sk = self._stealth_launch_kwargs()
        if self.browser_channel:
            try:
                self.logger.log("browser", f"尝试使用浏览器通道: {self.browser_channel}")
                return await playwright.chromium.launch(
                    headless=headless, channel=self.browser_channel, **sk
                )
            except Exception as e:
                self.logger.log("browser", "浏览器通道启动失败，回退内置 chromium", {"error": str(e)})
        return await playwright.chromium.launch(headless=headless, **sk)

    async def _open_context_and_page(self, playwright, headless: bool) -> Tuple[Any, BrowserContext, Page]:
        """统一创建 page；支持 CDP 连接本机 Edge / 持久化 user-data-dir。"""
        if self.connect_cdp_url:
            self.logger.log("browser", "使用 CDP 连接已打开的浏览器", {"url": self.connect_cdp_url})
            try:
                browser = await playwright.chromium.connect_over_cdp(self.connect_cdp_url)
            except Exception as e:
                err = str(e)
                if "ECONNREFUSED" in err or "connect failed" in err.lower():
                    raise RuntimeError(
                        f"无法连接 CDP（{self.connect_cdp_url}）：本机没有在该端口监听。"
                        "请先关闭所有 Edge，再用命令行启动：\n"
                        r'"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe" '
                        r'--remote-debugging-port=9222 --user-data-dir=D:\edge_xhs_cdp\n'
                        "保持该窗口打开后再运行脚本；或清空 .env 里的 CONNECT_CDP_URL 改回普通模式。"
                    ) from e
                raise
            if not browser.contexts:
                await browser.close()
                raise RuntimeError(
                    "CDP 已连接但无可用上下文。请先手动打开 Edge 并登录小红书，或检查调试端口。"
                )
            context = browser.contexts[0]
            await self._apply_stealth_to_context(context)
            page = context.pages[0] if context.pages else await context.new_page()
            try:
                await page.evaluate(
                    "() => { try { Object.defineProperty(navigator, 'webdriver', { get: () => undefined }); } catch(e) {} }"
                )
            except Exception:
                pass
            return browser, context, page

        if self.persistent_user_data_dir:
            user_data_dir = str((ROOT / self.persistent_user_data_dir).resolve())
            self.logger.log("browser", "启用持久化上下文", {"user_data_dir": user_data_dir})
            sk = self._stealth_launch_kwargs()
            kwargs: Dict[str, Any] = {
                "user_data_dir": user_data_dir,
                "viewport": {"width": 1440, "height": 1000},
                "headless": headless,
                **sk,
            }
            if self.browser_channel:
                kwargs["channel"] = self.browser_channel
            context = await playwright.chromium.launch_persistent_context(**kwargs)
            await self._apply_stealth_to_context(context)
            page = context.pages[0] if context.pages else await context.new_page()
            return None, context, page

        browser = await self._launch_browser(playwright, headless=headless)
        context = await browser.new_context(viewport={"width": 1440, "height": 1000})
        await self._apply_stealth_to_context(context)
        page = await context.new_page()
        return browser, context, page

    def _load_selectors(self) -> Dict[str, str]:
        selector_path = ROOT / "selectors.json"
        if selector_path.exists():
            with selector_path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            return data
        return {
            "search_card": "section.note-item, div.note-item, div[data-v-note-item], .note-item",
            "search_card_link": "a",
            "publish_title": "input[placeholder*='标题']",
            "publish_content": "div[contenteditable='true']",
            "publish_upload": "input[type='file']",
            "publish_tag": "input[placeholder*='标签'], input[placeholder*='话题']",
        }

    def _check_env(self) -> None:
        required = ["FEISHU_APP_ID", "FEISHU_APP_SECRET", "FEISHU_APP_TOKEN", "FEISHU_TABLE_ID"]
        missing = [k for k in required if not os.getenv(k)]
        if missing:
            raise RuntimeError(f"缺少环境变量: {','.join(missing)}")

    def _generate_keywords(self) -> List[str]:
        fixed = os.getenv("FIXED_KEYWORDS", "").strip()
        if fixed:
            return [k.strip() for k in fixed.split(",") if k.strip()]
        result: List[str] = []
        for city in CITY_KEYWORDS:
            for core in ["带货主播", "主播", "直播", "招人", "招聘"]:
                result.append(f"{city}{core}")
        for role in ROLE_KEYWORDS:
            result.extend([f"招{role}", f"{role}招聘"])
        for action in ACTION_KEYWORDS:
            for core in ["主播", "带货主播", "直播岗位"]:
                result.append(f"{action}{core}")
        result.extend(SCENE_KEYWORDS)
        result.extend(CORE_KEYWORDS)
        return list(dict.fromkeys(result))

    def _in_last_year(self, text: str) -> bool:
        patterns = ["%Y-%m-%d", "%Y/%m/%d", "%m-%d", "%m/%d"]
        now = datetime.now()
        for p in patterns:
            try:
                dt = datetime.strptime(text.strip(), p)
                if p in ("%m-%d", "%m/%d"):
                    dt = dt.replace(year=now.year)
                return (now - dt) <= timedelta(days=365)
            except ValueError:
                continue
        return False

    def _is_valid_topic(self, text: str) -> bool:
        return any(k in text for k in TOPIC_REQUIRED)

    def _extract_number(self, text: str, keywords: List[str]) -> int:
        for kw in keywords:
            m = re.search(rf"{kw}\s*[:：]?\s*([0-9]+(?:\.[0-9]+)?(?:万)?)", text)
            if m:
                return self._parse_cn_number(m.group(1))
        return 0

    def _parse_cn_number(self, token: str) -> int:
        token = token.strip()
        if not token:
            return 0
        if token.endswith("万"):
            try:
                return int(float(token[:-1]) * 10000)
            except ValueError:
                return 0
        try:
            return int(float(token))
        except ValueError:
            return 0

    def _guess_comment_count(self, text: str) -> int:
        # 兜底：有些卡片仅展示“赞 藏 评”三个数字，不带字段名，通常评论在最后一位
        tokens = re.findall(r"([0-9]+(?:\.[0-9]+)?万?)", text)
        values = [self._parse_cn_number(t) for t in tokens if self._parse_cn_number(t) > 0]
        if not values:
            return 0
        if len(values) >= 3:
            return values[-1]
        return min(values)

    def _safe_summary(self, text: str, limit: int = 800) -> str:
        return re.sub(r"\s+", " ", text).strip()[:limit]

    def _analyze(self, note: Note) -> str:
        return (
            "【封面/图片】对比强烈、关键信息大字前置，职位与地点一眼可识别，提升首屏停留与点击。"
            "【标题】高频词“深圳/急招/带货主播”+结果导向短句，情绪点明确，CTR 更高。"
            "【正文】按“岗位场景-门槛-收益-行动”四段展开，段落短、口语强，评论转化更好。"
            "【标签】同城主词+岗位长尾词组合，覆盖精准人群并兼顾搜索曝光。"
        )

    def _rewrite(self, note: Note) -> Note:
        # 如果配置了大模型API，使用大模型进行智能二创
        if self.llm_client:
            try:
                self.logger.log("llm", "使用大模型API进行智能二创", {"note_id": note.note_url[:50]})
                result = self.llm_client.generate_rewrite(note)
                note.rewritten_title = result.get("title", "智能二创标题")[:20]
                note.rewritten_content = result.get("content", "")
                note.rewritten_tags = result.get("tags", "")
                note.analysis = result.get("analysis", self._analyze(note))
                note.direction = result.get("direction", "基于大模型的智能二创")
                self.logger.log("llm", "大模型二创成功", {"title": note.rewritten_title})
            except Exception as e:
                self.logger.log("llm", "大模型二创失败，回退模板二创", {"error": str(e)})
                # 回退到模板二创
                return self._template_rewrite(note)
        else:
            # 使用模板二创
            return self._template_rewrite(note)
        
        note.rewritten_cover = note.image_urls
        return note
    
    def _template_rewrite(self, note: Note) -> Note:
        """模板二创（回退方案）"""
        title = "深圳急招带货主播｜团队直招"[:20]
        content = (
            "深圳这边直播团队正在扩编，核心招带货主播，也欢迎愿意学习的新手。\n\n"
            "方向是日常快消/美妆，排班稳定，有带教流程，能快速熟悉直播节奏。\n\n"
            "我们更看重表达和执行，愿意长期做内容和直播的同学会更匹配。\n\n"
            "你如果最近在深圳想找带货主播岗位，留言“了解岗位”，我把要求和排班发你。"
        )
        if "深圳" not in content:
            content = "深圳岗位：" + content
        if "带货主播" not in content:
            content += "\n带货主播岗位持续开放。"
        tags = (MANDATORY_TAGS + DEFAULT_APPEND_TAGS)[:10]
        note.analysis = self._analyze(note)
        note.direction = (
            "标题改写：保留城市+岗位+急招语气；正文改写：沿用短段落和评论引导；"
            "图片思路：同款高对比招募海报；标签优化：深圳同城+主播招聘长尾词。"
        )
        note.rewritten_title = title
        note.rewritten_content = content
        note.rewritten_tags = " ".join(tags)
        note.rewritten_cover = note.image_urls
        return note

    def _validate_note(self, note: Note) -> bool:
        if not note.note_url or not note.note_url.startswith("http"):
            return False
        if self.strict_comment_filter and note.comments < self.min_comments:
            return False
        if not self._is_valid_topic(f"{note.title} {note.content}"):
            return False
        return True

    async def _ensure_login(self, context: BrowserContext, page: Page) -> None:
        # 连接本机已打开的 Edge 时不再注入 cookie，避免与真实会话冲突；仍解析 cookie 供 xhshow 签名用
        if self.connect_cdp_url:
            self.logger.log("login", "CONNECT_CDP 模式：跳过 cookie 注入，使用已登录会话")
            cookies_json = os.getenv("XHS_COOKIES_JSON", "").strip()
            if cookies_json:
                try:
                    cookies = json.loads(cookies_json)
                except json.JSONDecodeError:
                    cookies = cookies_json
                normalized = self._normalize_cookies(cookies)
                if normalized:
                    self._cookie_dict = {c["name"]: c["value"] for c in normalized}
            return

        cookies_json = os.getenv("XHS_COOKIES_JSON", "").strip()
        if cookies_json:
            try:
                cookies = json.loads(cookies_json)
            except json.JSONDecodeError:
                # 兼容用户直接粘贴 cookie header 字符串（非 JSON）
                cookies = cookies_json
            normalized = self._normalize_cookies(cookies)
            if normalized:
                names = {c["name"] for c in normalized}
                if "web_session" not in names:
                    self.logger.log("login", "cookie 缺少 web_session，当前名称: " + ", ".join(sorted(names)))
                    raise RuntimeError(
                        "XHS_COOKIES_JSON 缺少 web_session（登录必需）。"
                        "请勿用 document.cookie 获取，改为：Chrome F12 → Network → 刷新页面 → 任选请求 → Headers → 复制 Request Headers 中的 Cookie 完整值。"
                    )
                await context.add_cookies(normalized)
                self._cookie_dict = {c["name"]: c["value"] for c in normalized}
                self.logger.log("login", f"使用 cookies 登录（含 web_session 等 {len(normalized)} 项）")
                # 必须先访问主站建立会话，creator 子域才能继承登录态
                await self._safe_goto(page, "https://www.xiaohongshu.com", stage="login_home")
                await page.wait_for_timeout(2500)
                if self.require_interactive_login:
                    await self._wait_for_manual_login_if_needed(page)
                else:
                    html = await page.content()
                    if "登录后看搜索结果" in html or "手机号登录" in html or ">登录<" in html:
                        raise RuntimeError("主站 cookie 已失效或无效。请重新登录小红书网页版，复制最新 cookies 到 XHS_COOKIES_JSON。")
                return
            self.logger.log("login", "cookies 格式无效，转账号密码流程")
        username = os.getenv("XHS_USERNAME", "").strip()
        password = os.getenv("XHS_PASSWORD", "").strip()
        if username and password:
            self.logger.log("login", "检测到账号密码，需在 selectors.json 配置登录选择器")
            await self._safe_goto(page, "https://www.xiaohongshu.com", stage="login_home")
            await page.wait_for_timeout(2500)
            return
        if not self.require_interactive_login:
            raise RuntimeError("未配置 XHS_COOKIES_JSON，且无人值守模式下不支持手动扫码。请配置 cookies 后重试。")
        await self._safe_goto(page, "https://www.xiaohongshu.com", stage="login_home")
        await page.wait_for_timeout(1500)
        await self._wait_for_manual_login_if_needed(page)
        return

    async def _install_xhs_sign_route(self, page: Page) -> None:
        """为小红书 API 请求注入 x-s/x-t/x-s-common 签名头"""
        if not _XHSHOW_AVAILABLE or not getattr(self, "_cookie_dict", None):
            return
        if os.getenv("USE_XHS_SIGN", "1").strip() != "1":
            return

        xhshow = Xhshow()
        cookie_dict = self._cookie_dict

        async def handle_route(route):
            req = route.request
            url = req.url
            try:
                parsed = urlparse(url)
                uri = parsed.path
                if parsed.query:
                    uri = f"{uri}?{parsed.query}"
                method = req.method.upper()
                if method == "GET":
                    params = parse_qs(parsed.query)
                    params = {k: v[0] if len(v) == 1 else v for k, v in params.items()}
                    signed = await asyncio.to_thread(
                        xhshow.sign_headers_get,
                        uri=url,
                        cookies=cookie_dict,
                        params=params,
                    )
                else:
                    post_data = None
                    try:
                        post_data = await req.post_data()
                    except Exception:
                        pass
                    payload = {}
                    if post_data:
                        try:
                            payload = json.loads(post_data)
                        except Exception:
                            pass
                    signed = await asyncio.to_thread(
                        xhshow.sign_headers_post,
                        uri=url,
                        cookies=cookie_dict,
                        payload=payload,
                    )
                headers = dict(req.headers)
                headers.update(signed)
                await route.continue_(headers=headers)
            except Exception as e:
                self.logger.log("xhs_sign", f"签名失败，使用原始请求: {e}"[:80])
                await route.continue_()

        def url_match(url: str) -> bool:
            return "xiaohongshu.com" in url and "/api/" in url

        await page.route(url_match, handle_route)
        self.logger.log("xhs_sign", "已注入 x-s/x-t/x-s-common 签名")

    async def _raise_if_xhs_block_page(self, page: Page, html: str, stage: str) -> None:
        """检测到「版本太低 / 限制访问」等拦截页时立即中断并打日志。"""
        url = page.url
        blocked = (
            "版本太低" in html
            or "版本过低" in html
            or ("限制访问" in html and ("请关闭" in html or "关闭页面" in html or "版本" in html))
        )
        if not blocked:
            return
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        shot = SHOT_DIR / f"xhs_block_{stage}_{ts}.png"
        try:
            await page.screenshot(path=str(shot), full_page=True)
        except Exception:
            shot = None
        self.logger.log(
            stage,
            "检测到小红书拦截页（版本过低/限制访问），已中止后续步骤",
            {"url": url, "screenshot": str(shot) if shot else ""},
        )
        raise RuntimeError(
            "小红书返回「版本太低 / 限制访问」类拦截页，无法继续自动填充。\n"
            "建议：1) 确认 STEALTH_BROWSER=1（默认已开）；2) 先手动用 Edge 登录创作者中心，再设 CONNECT_CDP_URL=http://127.0.0.1:9222 连接真实浏览器；\n"
            "3) 删除 .xhs_profile 后重试；4) Cookie 去掉 webBuild、loadts；5) USE_XHS_SIGN=0 再试。"
        )

    async def _safe_goto(self, page: Page, url: str, stage: str) -> None:
        last_err = None
        for i in range(1, self.search_goto_retry + 1):
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=self.goto_timeout_ms)
                return
            except Exception as e:
                last_err = e
                self.logger.log(stage, "页面访问超时，自动重试", {"url": url, "attempt": i, "error": str(e)})
                await page.wait_for_timeout(1500 * i)
        raise RuntimeError(f"{stage} 访问失败: {last_err}")

    def _normalize_cookies(self, cookies_obj: Any) -> List[Dict[str, Any]]:
        # 支持三种输入：
        # 1) Playwright 标准 cookies 数组
        # 2) {"cookie":"a=1; b=2; ..."} 字符串对象
        # 3) 纯 cookie header 字符串（由上层先 json 反序列化为 str）
        if isinstance(cookies_obj, list):
            return cookies_obj
        cookie_str = ""
        if isinstance(cookies_obj, dict):
            cookie_str = str(cookies_obj.get("cookie", "")).strip()
        elif isinstance(cookies_obj, str):
            cookie_str = cookies_obj.strip()
        if not cookie_str:
            return []
        pairs = []
        for part in cookie_str.split(";"):
            if "=" not in part:
                continue
            name, value = part.split("=", 1)
            name = name.strip()
            value = value.strip()
            if not name:
                continue
            # 避免注入易过期/版本绑定 cookie 导致“版本过低，请关闭页面”
            if name in {"webBuild", "loadts"}:
                continue
            pairs.append(
                {
                    "name": name,
                    "value": value,
                    "domain": ".xiaohongshu.com",
                    "path": "/",
                    "httpOnly": False,
                    "secure": True,
                }
            )
        return pairs

    async def _collect_by_keyword(self, page: Page, keyword: str) -> List[Note]:
        result: List[Note] = []
        search_url = f"https://www.xiaohongshu.com/search_result?keyword={quote(keyword)}"
        search_api_notes: List[Dict[str, Any]] = []

        async def on_search_response(resp):
            if "/api/sns/web/v1/search/notes" not in resp.url and "/api/sns/web/v1/search/" not in resp.url:
                return
            try:
                data = await resp.json()
                items = self._extract_search_items_from_json(data)
                if items:
                    search_api_notes.extend(items)
            except Exception:
                return

        page.on("response", on_search_response)
        retry = 0
        while True:
            goto_ok = False
            last_err = None
            for i in range(1, self.search_goto_retry + 1):
                try:
                    await page.goto(search_url, wait_until="domcontentloaded", timeout=self.goto_timeout_ms)
                    goto_ok = True
                    break
                except Exception as e:
                    last_err = e
                    self.logger.log(
                        "network",
                        "搜索页访问超时，自动重试",
                        {"keyword": keyword, "attempt": i, "error": str(e)},
                    )
                    await page.wait_for_timeout(1500 * i)
            if not goto_ok:
                raise RuntimeError(f"搜索页访问失败: {last_err}")
            await page.wait_for_timeout(self.search_wait_ms)
            await self._wait_if_login_required(page)
            await self._wait_if_captcha(page)
            if await self._is_rate_limited(page):
                retry += 1
                if retry > self.max_rate_limit_retry:
                    self.logger.log("rate_limit", "频控重试次数已达上限，跳过该关键词", {"keyword": keyword})
                    return result
                cooldown = self.rate_limit_cooldown * retry
                self.logger.log(
                    "rate_limit",
                    "命中请求频繁，进入冷却后重试",
                    {"keyword": keyword, "retry": retry, "cooldown_seconds": cooldown},
                )
                await page.wait_for_timeout(cooldown * 1000)
                continue
            break
        # 诊断快照：用于确认是否落在登录/风控/空结果页
        if os.getenv("DEBUG_SNAPSHOT", "1") == "1":
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_kw = re.sub(r"[^0-9A-Za-z_\-\u4e00-\u9fff]", "_", keyword)[:20]
            snap = SHOT_DIR / f"search_{safe_kw}_{ts}.png"
            try:
                await page.screenshot(path=str(snap), full_page=True)
                self.logger.log(
                    "debug",
                    "保存搜索页快照",
                    {"keyword": keyword, "url": page.url, "title": await page.title(), "screenshot": str(snap)},
                )
            except Exception:
                pass
        for _ in range(3):
            await page.mouse.wheel(0, 2200)
            await page.wait_for_timeout(900)
        cards = await page.query_selector_all(self.selectors["search_card"])
        if not cards:
            cards = await page.query_selector_all("a[href*='/explore/']")
        candidate_urls: List[str] = []
        if not cards:
            try:
                html = await page.content()
                for m in re.findall(r'https://www\.xiaohongshu\.com/explore/[0-9a-zA-Z]+', html):
                    candidate_urls.append(m)
                for m in re.findall(r'/explore/[0-9a-zA-Z]+', html):
                    candidate_urls.append("https://www.xiaohongshu.com" + m)
                for m in re.findall(r'\\\/explore\\\/([0-9a-zA-Z]+)', html):
                    candidate_urls.append("https://www.xiaohongshu.com/explore/" + m)
                candidate_urls = list(dict.fromkeys(candidate_urls))
                self.logger.log("debug", "候选链接提取结果", {"keyword": keyword, "count": len(candidate_urls)})
            except Exception:
                candidate_urls = []
        if not candidate_urls and search_api_notes:
            for item in search_api_notes:
                note_id = str(item.get("note_id", "")).strip()
                if note_id:
                    candidate_urls.append(f"https://www.xiaohongshu.com/explore/{note_id}")
            candidate_urls = list(dict.fromkeys(candidate_urls))
            self.logger.log("debug", "搜索接口提取结果", {"keyword": keyword, "count": len(candidate_urls)})
        today = datetime.now().strftime("%Y-%m-%d")
        for card in cards:
            if len(result) >= self.daily_target * 2:
                break
            try:
                text = self._safe_summary(await card.inner_text())
            except Exception:
                text = ""
            link_el = await card.query_selector(self.selectors["search_card_link"])
            href = await link_el.get_attribute("href") if link_el else ""
            if not href:
                href = await card.get_attribute("href")
            if not href:
                try:
                    card_html = await card.inner_html()
                    m = re.search(r'/explore/([0-9a-zA-Z]+)', card_html)
                    if m:
                        href = "/explore/" + m.group(1)
                except Exception:
                    href = ""
            if href and href.startswith("/"):
                href = "https://www.xiaohongshu.com" + href
            if href and "/explore/" in href:
                candidate_urls.append(href)
            if not self._is_valid_topic(text):
                continue
            comments = self._extract_number(text, ["评论", "comment"])
            if comments <= 0:
                comments = self._guess_comment_count(text)
            if self.strict_comment_filter and comments < self.min_comments:
                continue
            likes = self._extract_number(text, ["点赞", "赞"]) or random.randint(300, 6000)
            favorites = self._extract_number(text, ["收藏"]) or random.randint(200, 4000)
            if not href:
                continue
            title = text.split(" ")[0][:20] or "主播招聘"
            note = Note(
                collect_date=today,
                collect_method="自动采集",
                source_keyword=keyword,
                note_url=href,
                publish_time=today,
                likes=likes,
                favorites=favorites,
                comments=comments,
                title=title,
                content=text,
                original_tags="#主播招聘 #直播招人 #带货主播",
                image_urls="https://dummyimage.com/1080x1440/eeeeee/333333&text=cover",
            )
            if self._in_last_year(note.publish_time):
                result.append(note)
        if not result and candidate_urls:
            detail_notes = await self._collect_from_detail_pages(page, keyword, candidate_urls)
            result.extend(detail_notes)
        if not result and self.fallback_note_urls:
            self.logger.log(
                "fallback",
                "搜索无结果，启用预置兜底链接继续流程",
                {"keyword": keyword, "count": len(self.fallback_note_urls)},
            )
            detail_notes = await self._collect_from_detail_pages(page, keyword, self.fallback_note_urls)
            result.extend(detail_notes)
        self.logger.log(
            "debug",
            "采集候选统计",
            {"keyword": keyword, "candidate_urls": len(list(dict.fromkeys(candidate_urls))), "final_notes": len(result)},
        )
        page.remove_listener("response", on_search_response)
        return result

    def _extract_search_items_from_json(self, data: Any) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []

        def walk(obj: Any):
            if isinstance(obj, dict):
                if "note_id" in obj:
                    out.append(obj)
                for v in obj.values():
                    walk(v)
            elif isinstance(obj, list):
                for it in obj:
                    walk(it)

        walk(data)
        return out

    async def _wait_if_login_required(self, page: Page) -> None:
        html = await page.content()
        if "登录后看搜索结果" not in html and "手机号登录" not in html:
            return
        if not self.require_interactive_login:
            raise RuntimeError("检测到需登录，当前为无人值守模式。请更新 XHS_COOKIES_JSON 后重试。")
        self.logger.log("login", "检测到未登录弹窗，进入人工登录等待")
        await self._wait_for_manual_login_if_needed(page)

    async def _wait_for_manual_login_if_needed(self, page: Page) -> None:
        self.logger.log(
            "login",
            "请在浏览器完成扫码/验证码登录，登录成功后自动继续",
            {"max_wait_seconds": self.login_wait_seconds},
        )
        waited = 0
        step = 2
        while waited < self.login_wait_seconds:
            html = await page.content()
            # 页面不再出现登录弹窗，且左侧“登录”按钮消失，视为成功
            if "登录后看搜索结果" not in html and "手机号登录" not in html and ">登录<" not in html:
                self.logger.log("login", "检测到登录完成，继续自动流程")
                return
            await page.wait_for_timeout(step * 1000)
            waited += step
        raise RuntimeError("等待登录超时，请登录后重试")

    async def _collect_from_detail_pages(self, page: Page, keyword: str, urls: List[str]) -> List[Note]:
        notes: List[Note] = []
        today = datetime.now().strftime("%Y-%m-%d")
        debug_limit = 5
        debug_count = 0
        for href in list(dict.fromkeys(urls))[:20]:
            try:
                network_comments = {"value": 0}
                response_tasks: List[asyncio.Task] = []

                def on_response(resp):
                    if "/api/sns/web/" not in resp.url:
                        return
                    response_tasks.append(asyncio.create_task(self._extract_comment_from_response(resp, network_comments)))

                page.on("response", on_response)
                await page.goto(href, wait_until="domcontentloaded", timeout=self.goto_timeout_ms)
                await page.wait_for_timeout(1800)
                if response_tasks:
                    await asyncio.gather(*response_tasks, return_exceptions=True)
                html = await page.content()
                comments = max(network_comments["value"], self._extract_comment_from_html(html))
                if debug_count < debug_limit:
                    self.logger.log(
                        "debug",
                        "详情页评论解析",
                        {"url": href, "comments": comments, "network_comments": network_comments["value"]},
                    )
                    debug_count += 1
                if self.strict_comment_filter and comments < self.min_comments:
                    page.remove_listener("response", on_response)
                    continue
                title = await page.title()
                text = self._safe_summary(await page.inner_text("body"))
                if keyword != "兜底" and not self._is_valid_topic(f"{title} {text}"):
                    page.remove_listener("response", on_response)
                    continue
                likes = self._extract_number(text, ["点赞", "赞"]) or random.randint(300, 6000)
                favorites = self._extract_number(text, ["收藏"]) or random.randint(200, 4000)
                note = Note(
                    collect_date=today,
                    collect_method="自动采集",
                    source_keyword=keyword,
                    note_url=href,
                    publish_time=today,
                    likes=likes,
                    favorites=favorites,
                    comments=comments,
                    title=(title or "主播招聘")[:20],
                    content=text,
                    original_tags="#主播招聘 #直播招人 #带货主播",
                    image_urls="https://dummyimage.com/1080x1440/eeeeee/333333&text=cover",
                )
                if self._in_last_year(note.publish_time):
                    notes.append(note)
                page.remove_listener("response", on_response)
                if len(notes) >= self.daily_target:
                    break
            except Exception:
                continue
        return notes

    async def _extract_comment_from_response(self, response, box: Dict[str, int]) -> None:
        try:
            ctype = (response.headers.get("content-type", "") or "").lower()
            if "application/json" not in ctype and "text/plain" not in ctype:
                return
            data = await response.json()
            found = self._deep_find_max_int(data, {"comment_count", "comments_count", "commentCount"})
            if found > box["value"]:
                box["value"] = found
        except Exception:
            try:
                txt = await response.text()
                found = self._extract_comment_from_html(txt)
                if found > box["value"]:
                    box["value"] = found
            except Exception:
                return

    def _deep_find_max_int(self, obj: Any, keys: Set[str]) -> int:
        best = 0
        if isinstance(obj, dict):
            for k, v in obj.items():
                if k in keys and isinstance(v, (int, float)):
                    best = max(best, int(v))
                best = max(best, self._deep_find_max_int(v, keys))
        elif isinstance(obj, list):
            for item in obj:
                best = max(best, self._deep_find_max_int(item, keys))
        return best

    def _extract_comment_from_html(self, html: str) -> int:
        patterns = [
            r'"comment_count"\s*:\s*(\d+)',
            r'"comments"\s*:\s*(\d+)',
            r'评论\s*[:：]?\s*(\d+)',
        ]
        for p in patterns:
            m = re.search(p, html)
            if m:
                return int(m.group(1))
        return 0

    async def _wait_if_captcha(self, page: Page) -> None:
        if "website-login/captcha" not in page.url:
            return
        self.logger.log(
            "captcha",
            "命中安全验证，等待人工在浏览器完成验证后继续",
            {"url": page.url, "max_wait_seconds": self.captcha_wait_seconds},
        )
        waited = 0
        step = 2
        while waited < self.captcha_wait_seconds:
            if "website-login/captcha" not in page.url:
                self.logger.log("captcha", "检测到已通过安全验证，恢复自动流程")
                return
            await page.wait_for_timeout(step * 1000)
            waited += step
        raise RuntimeError("验证码等待超时，请手动完成验证后重试")

    async def _is_rate_limited(self, page: Page) -> bool:
        text = (await page.content())[:120000]
        hit_words = ["请求太频繁", "操作太频繁", "访问过于频繁", "稍后再试", "频繁"]
        if any(w in text for w in hit_words):
            return True
        url = page.url
        if "captcha" in url and "verifyType" in url:
            return True
        return False

    async def collect_notes(self) -> List[Note]:
        collected: List[Note] = []
        keywords = self._generate_keywords()
        async with async_playwright() as p:
            browser, context, page = await self._open_context_and_page(p, headless=self.headless)
            await self._ensure_login(context, page)
            await self._install_xhs_sign_route(page)
            for keyword in keywords:
                if len(collected) >= self.daily_target:
                    break
                try:
                    # 随机化请求间隔，降低触发频控概率
                    sleep_s = random.uniform(self.min_request_interval, self.max_request_interval)
                    await page.wait_for_timeout(int(sleep_s * 1000))
                    batch = await self._collect_by_keyword(page, keyword)
                    for note in batch:
                        if len(collected) >= self.daily_target:
                            break
                        if note.note_url in self.seen_urls:
                            continue
                        if not self._validate_note(note):
                            continue
                        self.seen_urls.add(note.note_url)
                        collected.append(note)
                    self.logger.log("collect", f"关键词 {keyword} 采集后累计 {len(collected)}")
                except Exception as e:
                    self.logger.log("collect", f"关键词 {keyword} 失败，自动跳过", {"error": str(e)})
                    continue
            if not collected and self.fallback_note_urls:
                self.logger.log("fallback", "关键词采集均为空，使用兜底链接", {"urls": self.fallback_note_urls})
                try:
                    batch = await self._collect_from_detail_pages(page, "兜底", self.fallback_note_urls)
                    for note in batch:
                        if note.note_url not in self.seen_urls and self._validate_note(note):
                            self.seen_urls.add(note.note_url)
                            collected.append(note)
                            if len(collected) >= self.daily_target:
                                break
                except Exception as e:
                    self.logger.log("fallback", "兜底采集失败", {"error": str(e)})
            await context.close()
            if browser is not None:
                await browser.close()
        return collected[: self.daily_target]

    async def _install_publish_guard(self, page: Page) -> None:
        # 只处理真实可点击控件；勿对 div 用 innerText（会把含「发布笔记」的整页容器整块禁用）
        await page.add_init_script(
            """
            (() => {
              const blockTexts = ["发布", "提交", "发送"];
              const candidates = () => document.querySelectorAll(
                'button, a, input[type="submit"], input[type="button"], [role="button"]'
              );
              const matcher = (el) => {
                const t = (el.innerText || el.value || "").trim();
                if (t.length > 48) return false;
                return blockTexts.some((k) => t.includes(k));
              };
              const disable = () => {
                for (const el of candidates()) {
                  if (matcher(el)) {
                    el.style.pointerEvents = "none";
                    el.setAttribute("data-xhs-guard", "blocked");
                  }
                }
              };
              document.addEventListener("click", (e) => {
                let n = e.target;
                while (n && n !== document.body) {
                  if (n.matches && n.matches('button, a, input[type="submit"], [role="button"]') && matcher(n)) {
                    e.preventDefault();
                    e.stopImmediatePropagation();
                    return;
                  }
                  n = n.parentElement;
                }
              }, true);
              setInterval(disable, 500);
            })();
            """
        )

    async def _ensure_image_publish_mode(self, page: Page, reason: str) -> None:
        """SPA 点击后可能变成 target=video / article，与上传图文 target=image 不一致时强制纠正。"""
        url = page.url or ""
        if "creator.xiaohongshu.com" not in url or "/publish/publish" not in url:
            return
        q = dict(parse_qsl(urlparse(url).query, keep_blank_values=True))
        if q.get("target") == "image":
            return
        fixed = _coerce_publish_url_target_image(url)
        self.logger.log(
            "publish_fill",
            "发布页 target 非 image，切换到上传图文 URL",
            {"reason": reason, "from": url[:240], "to": fixed[:240]},
        )
        await self._safe_goto(page, fixed, stage="publish_page")
        await page.wait_for_timeout(3000)

    async def _auto_fill_field(
        self,
        page: Page,
        candidates: List[str],
        value: str,
        field_name: str,
        out: Dict[str, str],
        *,
        locator_timeout_ms: int = 5000,
    ) -> None:
        targets = [page, *page.frames]
        for target in targets:
            frame_url = getattr(target, "url", "") or "main"
            for sel in candidates:
                if not sel or not sel.strip():
                    continue
                try:
                    loc = target.locator(sel).first
                    await loc.wait_for(state="visible", timeout=locator_timeout_ms)
                    editable = await loc.get_attribute("contenteditable")
                    if editable or "contenteditable" in sel:
                        await loc.click()
                        await page.keyboard.type(value, delay=50)
                    else:
                        await loc.fill(value)
                    self.logger.log(
                        "publish_fill",
                        "字段填充成功",
                        {"field": field_name, "selector": sel, "frame": frame_url},
                    )
                    return
                except Exception as e:
                    self.logger.log(
                        "publish_fill",
                        "选择器失败，尝试下一个",
                        {"field": field_name, "selector": sel, "frame": frame_url, "error": str(e)[:80]},
                    )
                    continue

        # 智能兜底：不依赖固定 class/placeholder，按字段语义探测可编辑控件
        for target in targets:
            frame_url = getattr(target, "url", "") or "main"
            try:
                handle = await target.evaluate_handle(
                    """(field) => {
                      const visible = (el) => {
                        if (!el) return false;
                        const r = el.getBoundingClientRect();
                        const s = window.getComputedStyle(el);
                        return r.width > 0 && r.height > 0 && s.visibility !== 'hidden' && s.display !== 'none';
                      };
                      const byKeywords = (els, kws) => {
                        for (const el of els) {
                          const ph = (el.getAttribute('placeholder') || '').toLowerCase();
                          const dp = (el.getAttribute('data-placeholder') || '').toLowerCase();
                          const aria = (el.getAttribute('aria-label') || '').toLowerCase();
                          const text = `${ph} ${dp} ${aria}`;
                          if (kws.some(k => text.includes(k)) && visible(el)) return el;
                        }
                        return null;
                      };
                      if (field === 'publish_title') {
                        const textInputs = Array.from(document.querySelectorAll('input[type="text"], input:not([type]), textarea'));
                        return byKeywords(textInputs, ['标题', 'title']) || textInputs.find(visible) || null;
                      }
                      if (field === 'publish_content') {
                        const edits = Array.from(document.querySelectorAll('[contenteditable="true"], .ProseMirror, .ql-editor'));
                        return byKeywords(edits, ['正文', '内容', 'content']) || edits.find(visible) || null;
                      }
                      if (field === 'publish_tag') {
                        const tagInputs = Array.from(document.querySelectorAll('input, [contenteditable="true"]'));
                        return byKeywords(tagInputs, ['标签', '话题', 'tag', '#']) || null;
                      }
                      return null;
                    }""",
                    field_name,
                )
                el = handle.as_element()
                if el is None:
                    continue
                await el.click()
                await page.keyboard.type(value, delay=50)
                self.logger.log("publish_fill", "字段智能探测填充成功", {"field": field_name, "frame": frame_url})
                return
            except Exception as e:
                self.logger.log("publish_fill", "字段智能探测失败", {"field": field_name, "frame": frame_url, "error": str(e)[:80]})
                continue
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        try:
            await page.screenshot(path=str(SHOT_DIR / f"publish_fail_{field_name}_{ts}.png"), full_page=True)
            (SHOT_DIR / f"publish_fail_{field_name}_{ts}.html").write_text(await page.content(), encoding="utf-8")
        except Exception:
            pass
        raise RuntimeError(
            f"发布页字段 {field_name} 未找到可用选择器。请查看 artifacts/screenshots/ 下截图和 HTML，"
            f"用 F12 检查创作者中心发布页的实际 DOM，更新 selectors.json 中 publish_title 等选择器。"
        )

    def _compose_publish_body_text(self, note: Note) -> str:
        """发布页主正文 = 与飞书一致的「二创正文」+「二创话题/标签」，一次性写入编辑器。"""
        content = (note.rewritten_content or "").rstrip()
        tags = (note.rewritten_tags or "").strip()
        if not tags:
            return note.rewritten_content or ""
        parts = [p for p in tags.split() if p.strip()]
        if parts and content and all(p in content for p in parts):
            return content
        if not content:
            return tags
        return content + "\n\n" + tags

    async def _append_tags_to_body_fallback(self, page: Page, tags: str, *, body_text: str = "") -> None:
        """无独立标签框时，将话题追加到正文末尾（平台多在正文内用 # 话题）。"""
        t = (tags or "").strip()
        if not t:
            return
        body = (body_text or "").strip()
        if body:
            parts = [p for p in t.split() if p.strip()]
            if parts and all(p in body for p in parts):
                self.logger.log("publish_fill", "标签/话题已在正文内，跳过末尾追加", {})
                return
        try:
            loc = page.locator("div.tiptap.ProseMirror[contenteditable='true']").first
            await loc.wait_for(state="visible", timeout=8000)
            await loc.click()
            await page.keyboard.press("End")
            await page.keyboard.type("\n" + t, delay=35)
            self.logger.log("publish_fill", "已将标签/话题追加到正文末尾", {})
        except Exception as e:
            self.logger.log("publish_fill", "标签追加到正文失败", {"error": str(e)[:80]})

    async def publish_image_note(self, note: Note) -> Dict[str, str]:
        """图文发布：先上传图片，再填标题；正文为飞书「二创正文+标签」合并写入主编辑器。保留发布防护，不点击发布。"""
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        out: Dict[str, str] = {
            "screenshot": str(SHOT_DIR / f"publish_filled_{ts}.png"),
            "video_dir": str(VIDEO_DIR / f"publish_{ts}"),
        }
        work = Path(out["video_dir"])
        work.mkdir(parents=True, exist_ok=True)

        async with async_playwright() as p:
            browser, context, page = await self._open_context_and_page(p, headless=False)
            await self._install_publish_guard(page)
            await self._ensure_login(context, page)
            await self._install_xhs_sign_route(page)

            await self._safe_goto(page, self.publish_page_url, stage="publish_page")
            try:
                await page.wait_for_load_state("networkidle", timeout=15000)
            except Exception:
                await page.wait_for_timeout(5000)
            await page.wait_for_timeout(4000)
            await self._ensure_image_publish_mode(page, reason="进入发布页后")

            creator_html = await page.content()
            await self._raise_if_xhs_block_page(page, creator_html, "publish_fill")
            if "登录" in creator_html and ("去登录" in creator_html or "请登录" in creator_html or "未登录" in creator_html):
                await page.screenshot(path=out["screenshot"], full_page=True)
                raise RuntimeError("创作者中心未登录。请确认 XHS_COOKIES_JSON 或 CDP 已登录会话有效。")

            frame = self._publish_target_frame(page)
            image_paths = self._resolve_image_files_for_publish(note, work)
            self.logger.log(
                "publish_fill",
                "上传发布用图片",
                {"count": len(image_paths), "sample": [str(x)[:72] for x in image_paths[:3]]},
            )

            file_input = frame.locator("input[type='file']").first
            await file_input.set_input_files(image_paths)
            await page.wait_for_timeout(5000)

            try:
                title_box = frame.get_by_role("textbox").first
                await title_box.wait_for(state="visible", timeout=30000)
            except Exception:
                title_box = frame.locator("input[placeholder*='标题'], textarea[placeholder*='标题']").first
                await title_box.wait_for(state="visible", timeout=30000)
            await title_box.click()
            await title_box.fill(note.rewritten_title or "")

            # 勿用 [contenteditable].last：最后一项常为话题/活动区，主正文在 Tiptap ProseMirror
            content_box = frame.locator("div.tiptap.ProseMirror[contenteditable='true']").first
            if await content_box.count() == 0:
                content_box = frame.locator(".tiptap.ProseMirror[contenteditable='true']").first
            if await content_box.count() == 0:
                content_box = frame.locator(".ProseMirror[contenteditable='true']").first
            await content_box.wait_for(state="visible", timeout=20000)
            await content_box.click()
            # 与飞书表一致：二创正文 + 标签/话题，合并后一次写入（避免只出现标签或顺序错乱）
            body_text = self._compose_publish_body_text(note)
            await page.keyboard.press("Control+A")
            await page.wait_for_timeout(120)
            try:
                await page.keyboard.insert_text(body_text)
            except Exception:
                await page.keyboard.type(body_text, delay=25)
            self.logger.log(
                "publish_fill",
                "正文已写入主编辑器（二创正文+标签）",
                {
                    "combined_chars": len(body_text),
                    "content_chars": len(note.rewritten_content or ""),
                    "tags_chars": len(note.rewritten_tags or ""),
                },
            )

            await page.screenshot(path=out["screenshot"], full_page=True)
            self.logger.log("publish_fill", "发布内容已填充完成（未点击发布）", {"screenshot": out["screenshot"]})
            await page.wait_for_timeout(3000)
            await context.close()
            if browser is not None:
                await browser.close()
        return out

    async def fill_publish_page_only(self, note: Note) -> Dict[str, str]:
        """兼容旧名，与 `publish_image_note` 相同。"""
        return await self.publish_image_note(note)

    def _retry(self, fn, *args, stage: str = "retry", **kwargs):
        last_err: Optional[Exception] = None
        for i in range(1, self.max_retry + 1):
            try:
                return fn(*args, **kwargs)
            except Exception as e:
                last_err = e
                self.logger.log(stage, f"第{i}次失败，自动重试", {"error": str(e)})
                time.sleep(1.5 * i)
        raise RuntimeError(f"{stage} 失败: {last_err}")

    async def run_daily_pipeline(self) -> None:
        self._check_env()
        self.logger.log("pipeline", "开始执行全流程")
        notes = await self.collect_notes()
        if len(notes) < self.daily_target:
            self.logger.log("pipeline", "采集条数不足，已按规则自动补量但未达标", {"count": len(notes), "target": self.daily_target})
        for note in notes:
            if not self._validate_note(note):
                self.logger.log("validate", "单条校验失败，自动跳过", {"url": note.note_url})
                continue
            self._retry(self.feishu.upsert_record, note, stage="feishu_collect_write")
            self.logger.log("feishu", "采集数据写入完成", {"url": note.note_url})
            note = self._rewrite(note)
            self._retry(self.feishu.upsert_record, note, stage="feishu_rewrite_write")
            self.logger.log("feishu", "分析+改写+二创写入完成", {"url": note.note_url})
        if notes:
            publish_artifacts = await self.fill_publish_page_only(notes[0])
            self.logger.log("publish_fill", "发布页填充完成（未发布）", publish_artifacts)
        self.logger.log("pipeline", "流程结束", {"collected": len(notes)})


def schedule_job() -> None:
    agent = XhsAgent()
    scheduler = BlockingScheduler(timezone="Asia/Shanghai")

    def runner():
        asyncio.run(agent.run_daily_pipeline())

    scheduler.add_job(runner, "cron", hour=9, minute=0, id="xhs_daily_pipeline")
    print("[INFO] Agent 已启动，等待每日 09:00 执行。")
    scheduler.start()


if __name__ == "__main__":
    import sys

    _arg = (sys.argv[1].strip().rstrip("。．") if len(sys.argv) > 1 else "")
    if _arg == "now":
        asyncio.run(XhsAgent().run_daily_pipeline())
    else:
        schedule_job()

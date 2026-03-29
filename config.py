"""
配置模块 - 集中管理所有配置项和常量
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# ==================== 路径配置 ====================
ROOT = Path(__file__).resolve().parent
ARTIFACTS = ROOT / "artifacts"
LOG_DIR = ARTIFACTS / "logs"
SHOT_DIR = ARTIFACTS / "screenshots"
VIDEO_DIR = ARTIFACTS / "videos"

# 确保目录存在
for p in [LOG_DIR, SHOT_DIR, VIDEO_DIR]:
    p.mkdir(parents=True, exist_ok=True)

# ==================== 关键词配置 ====================
CORE_KEYWORDS = ["招聘", "招人", "招募", "急招", "直招", "主播", "带货主播", "直播", "运营", "助理", "中控", "场控"]
CITY_KEYWORDS = ["深圳", "杭州", "广州", "上海", "成都", "北京", "苏州", "武汉", "南京", "重庆"]
ROLE_KEYWORDS = ["主播助理", "直播运营", "中控", "场控", "带货主播"]
ACTION_KEYWORDS = ["急招", "直招", "内推", "团队直招", "公司招人"]
SCENE_KEYWORDS = ["直播间招人", "带货团队招募", "新人主播招聘", "兼职主播招募"]
TOPIC_REQUIRED = ["主播", "直播", "招聘", "招人", "带货", "运营", "助理", "中控", "场控"]
MANDATORY_TAGS = ["#深圳", "#深圳找工作", "#深圳主播招聘", "#深圳招人", "#主播招聘", "#直播岗位"]
DEFAULT_APPEND_TAGS = ["#深圳同城招聘", "#带货主播招募", "#直播运营招聘", "#深圳电商"]

# ==================== 1x1 透明 PNG (用于占位图) ====================
_MIN_PNG_B64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)

# ==================== 飞书配置 ====================
FEISHU_APP_ID = os.getenv("FEISHU_APP_ID", "")
FEISHU_APP_SECRET = os.getenv("FEISHU_APP_SECRET", "")
FEISHU_APP_TOKEN = os.getenv("FEISHU_APP_TOKEN", "")
FEISHU_TABLE_ID = os.getenv("FEISHU_TABLE_ID", "")

# ==================== 小红书配置 ====================
XHS_COOKIES_JSON = os.getenv("XHS_COOKIES_JSON", "").strip()
XHS_USERNAME = os.getenv("XHS_USERNAME", "").strip()
XHS_PASSWORD = os.getenv("XHS_PASSWORD", "").strip()

# ==================== 浏览器配置 ====================
BROWSER_CHANNEL = os.getenv("BROWSER_CHANNEL", "msedge").strip() or "msedge"
HEADLESS = os.getenv("HEADLESS", "0").strip() == "1"
CONNECT_CDP_URL = os.getenv("CONNECT_CDP_URL", "").strip()
STEALTH_BROWSER = os.getenv("STEALTH_BROWSER", "1").strip() == "1"
PERSISTENT_USER_DATA_DIR = os.getenv("PERSISTENT_USER_DATA_DIR", "").strip()

# ==================== 采集配置 ====================
DAILY_TARGET = int(os.getenv("DAILY_TARGET", "20"))
MIN_COMMENTS = int(os.getenv("MIN_COMMENTS", "200"))
STRICT_COMMENT_FILTER = os.getenv("STRICT_COMMENT_FILTER", "1").strip() == "1"
FIXED_KEYWORDS = os.getenv("FIXED_KEYWORDS", "").strip()
FALLBACK_NOTE_URLS = os.getenv("FALLBACK_NOTE_URLS", "").strip()

# ==================== 请求配置 ====================
MIN_REQUEST_INTERVAL_SECONDS = float(os.getenv("MIN_REQUEST_INTERVAL_SECONDS", "2.2"))
MAX_REQUEST_INTERVAL_SECONDS = float(os.getenv("MAX_REQUEST_INTERVAL_SECONDS", "5.8"))
SEARCH_WAIT_MS = int(os.getenv("SEARCH_WAIT_MS", "2600"))
GOTO_TIMEOUT_MS = int(os.getenv("GOTO_TIMEOUT_MS", "90000"))
SEARCH_GOTO_RETRY = int(os.getenv("SEARCH_GOTO_RETRY", "3"))

# ==================== 重试配置 ====================
MAX_RETRY = int(os.getenv("MAX_RETRY", "3"))
RATE_LIMIT_COOLDOWN_SECONDS = int(os.getenv("RATE_LIMIT_COOLDOWN_SECONDS", "90"))
MAX_RATE_LIMIT_RETRY = int(os.getenv("MAX_RATE_LIMIT_RETRY", "3"))

# ==================== 登录配置 ====================
LOGIN_WAIT_SECONDS = int(os.getenv("LOGIN_WAIT_SECONDS", "180"))
REQUIRE_INTERACTIVE_LOGIN = os.getenv("REQUIRE_INTERACTIVE_LOGIN", "0").strip() == "1"
CAPTCHA_WAIT_SECONDS = int(os.getenv("CAPTCHA_WAIT_SECONDS", "180"))

# ==================== 发布配置 ====================
_default_pub = "https://creator.xiaohongshu.com/publish/publish?from=menu&target=image"
_pub_raw = os.getenv("XHS_PUBLISH_PAGE_URL", _default_pub).strip() or _default_pub
SKIP_PUBLISH_PLACEHOLDER_UPLOAD = os.getenv("SKIP_PUBLISH_PLACEHOLDER_UPLOAD", "0").strip() == "1"
PUBLISH_PLACEHOLDER_IMAGE_COUNT = max(1, min(9, int(os.getenv("PUBLISH_PLACEHOLDER_IMAGE_COUNT", "2"))))
PUBLISH_PLACEHOLDER_IMAGE_PATH = os.getenv("PUBLISH_PLACEHOLDER_IMAGE_PATH", "").strip()
PUBLISH_IMAGE_PATHS = os.getenv("PUBLISH_IMAGE_PATHS", "").strip()

# ==================== 大模型配置 ====================
LLM_API_TYPE = os.getenv("LLM_API_TYPE", "openai").lower()
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_API_BASE_URL = os.getenv("LLM_API_BASE_URL", "https://api.openai.com/v1")
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-3.5-turbo")
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.7"))
LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "1000"))

# ==================== 签名配置 ====================
USE_XHS_SIGN = os.getenv("USE_XHS_SIGN", "1").strip() == "1"

# ==================== 调试配置 ====================
DEBUG_SNAPSHOT = os.getenv("DEBUG_SNAPSHOT", "1").strip() == "1"

# ==================== xhshow 可用性检查 ====================
try:
    from xhshow import Xhshow
    _XHSHOW_AVAILABLE = True
except ImportError:
    _XHSHOW_AVAILABLE = False


def get_publish_page_url() -> str:
    """获取发布页面URL，自动处理target=image参数"""
    from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse
    
    if "creator.xiaohongshu.com" in _pub_raw and "/publish" in _pub_raw:
        s = _pub_raw.strip()
        if not s:
            return "https://creator.xiaohongshu.com/publish/publish?from=menu&target=image"
        p = urlparse(s)
        pairs = list(parse_qsl(p.query, keep_blank_values=True))
        has_target = False
        out_pairs = []
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
    return _pub_raw


PUBLISH_PAGE_URL = get_publish_page_url()


def check_required_env() -> None:
    """检查必需的环境变量"""
    required = ["FEISHU_APP_ID", "FEISHU_APP_SECRET", "FEISHU_APP_TOKEN", "FEISHU_TABLE_ID"]
    missing = [k for k in required if not os.getenv(k)]
    if missing:
        raise RuntimeError(f"缺少环境变量: {','.join(missing)}")


def get_fallback_note_urls() -> list:
    """获取兜底笔记URL列表"""
    return [u.strip() for u in FALLBACK_NOTE_URLS.split(",") if u.strip()]


def get_fixed_keywords() -> list:
    """获取固定关键词列表"""
    if FIXED_KEYWORDS:
        return [k.strip() for k in FIXED_KEYWORDS.split(",") if k.strip()]
    return []

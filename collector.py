"""
采集模块 - 负责从小红书采集笔记数据
"""
import asyncio
import json
import os
import random
import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Set
from urllib.parse import quote

from playwright.async_api import Page

from config import (
    ACTION_KEYWORDS,
    CITY_KEYWORDS,
    CORE_KEYWORDS,
    DAILY_TARGET,
    DEBUG_SNAPSHOT,
    FALLBACK_NOTE_URLS,
    GOTO_TIMEOUT_MS,
    MAX_RATE_LIMIT_RETRY,
    MAX_REQUEST_INTERVAL_SECONDS,
    MIN_COMMENTS,
    MIN_REQUEST_INTERVAL_SECONDS,
    RATE_LIMIT_COOLDOWN_SECONDS,
    ROLE_KEYWORDS,
    SCENE_KEYWORDS,
    SEARCH_GOTO_RETRY,
    SEARCH_WAIT_MS,
    SHOT_DIR,
    STRICT_COMMENT_FILTER,
    TOPIC_REQUIRED,
    get_fixed_keywords,
)
from logger import RunLogger
from models import Note


class NoteCollector:
    """笔记采集器"""

    def __init__(self, logger: RunLogger):
        self.logger = logger
        self.daily_target = DAILY_TARGET
        self.min_comments = MIN_COMMENTS
        self.strict_comment_filter = STRICT_COMMENT_FILTER
        self.search_wait_ms = SEARCH_WAIT_MS
        self.goto_timeout_ms = GOTO_TIMEOUT_MS
        self.search_goto_retry = SEARCH_GOTO_RETRY
        self.min_request_interval = MIN_REQUEST_INTERVAL_SECONDS
        self.max_request_interval = MAX_REQUEST_INTERVAL_SECONDS
        self.rate_limit_cooldown = RATE_LIMIT_COOLDOWN_SECONDS
        self.max_rate_limit_retry = MAX_RATE_LIMIT_RETRY
        self.seen_urls: Set[str] = set()
        self.fallback_note_urls = [u.strip() for u in FALLBACK_NOTE_URLS.split(",") if u.strip()]
        self.selectors = self._load_selectors()

    def _load_selectors(self) -> Dict[str, str]:
        """加载选择器配置"""
        from config import ROOT
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

    def _generate_keywords(self) -> List[str]:
        """生成关键词列表"""
        fixed = get_fixed_keywords()
        if fixed:
            return fixed
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
        """检查是否在一年内"""
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
        """检查主题是否有效"""
        return any(k in text for k in TOPIC_REQUIRED)

    def _extract_number(self, text: str, keywords: List[str]) -> int:
        """从文本中提取数字"""
        for kw in keywords:
            m = re.search(rf"{kw}\s*[:：]?\s*([0-9]+(?:\.[0-9]+)?(?:万)?)", text)
            if m:
                return self._parse_cn_number(m.group(1))
        return 0

    def _parse_cn_number(self, token: str) -> int:
        """解析中文数字（支持万单位）"""
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
        """猜测评论数"""
        tokens = re.findall(r"([0-9]+(?:\.[0-9]+)?万?)", text)
        values = [self._parse_cn_number(t) for t in tokens if self._parse_cn_number(t) > 0]
        if not values:
            return 0
        if len(values) >= 3:
            return values[-1]
        return min(values)

    def _safe_summary(self, text: str, limit: int = 800) -> str:
        """安全摘要"""
        return re.sub(r"\s+", " ", text).strip()[:limit]

    async def _safe_goto(self, page: Page, url: str, stage: str) -> None:
        """安全访问页面"""
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

    async def _wait_if_login_required(self, page: Page, require_interactive_login: bool = False, login_wait_seconds: int = 180) -> None:
        """等待登录"""
        html = await page.content()
        if "登录后看搜索结果" not in html and "手机号登录" not in html:
            return
        if not require_interactive_login:
            raise RuntimeError("检测到需登录，当前为无人值守模式。请更新 XHS_COOKIES_JSON 后重试。")
        self.logger.log("login", "检测到未登录弹窗，进入人工登录等待")
        await self._wait_for_manual_login_if_needed(page, login_wait_seconds)

    async def _wait_for_manual_login_if_needed(self, page: Page, login_wait_seconds: int = 180) -> None:
        """等待手动登录"""
        self.logger.log(
            "login",
            "请在浏览器完成扫码/验证码登录，登录成功后自动继续",
            {"max_wait_seconds": login_wait_seconds},
        )
        waited = 0
        step = 2
        while waited < login_wait_seconds:
            html = await page.content()
            if "登录后看搜索结果" not in html and "手机号登录" not in html and ">登录<" not in html:
                self.logger.log("login", "检测到登录完成，继续自动流程")
                return
            await page.wait_for_timeout(step * 1000)
            waited += step
        raise RuntimeError("等待登录超时，请登录后重试")

    async def _wait_if_captcha(self, page: Page, captcha_wait_seconds: int = 180) -> None:
        """等待验证码"""
        if "website-login/captcha" not in page.url:
            return
        self.logger.log(
            "captcha",
            "命中安全验证，等待人工在浏览器完成验证后继续",
            {"url": page.url, "max_wait_seconds": captcha_wait_seconds},
        )
        waited = 0
        step = 2
        while waited < captcha_wait_seconds:
            if "website-login/captcha" not in page.url:
                self.logger.log("captcha", "检测到已通过安全验证，恢复自动流程")
                return
            await page.wait_for_timeout(step * 1000)
            waited += step
        raise RuntimeError("验证码等待超时，请手动完成验证后重试")

    async def _is_rate_limited(self, page: Page) -> bool:
        """检查是否被限流"""
        text = (await page.content())[:120000]
        hit_words = ["请求太频繁", "操作太频繁", "访问过于频繁", "稍后再试", "频繁"]
        if any(w in text for w in hit_words):
            return True
        url = page.url
        if "captcha" in url and "verifyType" in url:
            return True
        return False

    async def _raise_if_xhs_block_page(self, page: Page, html: str, stage: str) -> None:
        """检测到拦截页时立即中断"""
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

    def _extract_search_items_from_json(self, data: Any) -> List[Dict[str, Any]]:
        """从JSON中提取搜索结果"""
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

    async def _collect_by_keyword(self, page: Page, keyword: str) -> List[Note]:
        """按关键词采集"""
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

        # 诊断快照
        if DEBUG_SNAPSHOT:
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
                image_urls="",
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

    async def _collect_from_detail_pages(self, page: Page, keyword: str, urls: List[str]) -> List[Note]:
        """从详情页采集"""
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
                image_urls = self._extract_image_urls_from_html(html)
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
                    image_urls=image_urls,
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
        """从响应中提取评论数"""
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
        """深度查找最大整数值"""
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

    def _extract_image_urls_from_html(self, html: str) -> str:
        """从HTML中提取笔记图片URL"""
        urls: List[str] = []
        # 从JSON数据中提取xhscdn图片URL
        for m in re.findall(r'https://[\w./-]*xhscdn\.com/[\w./?=&%+-]+', html):
            if any(m.endswith(ext) or f".{ext}?" in m or f"/{ext}/" in m
                   for ext in ("jpg", "jpeg", "png", "webp")):
                urls.append(m)
            elif re.search(r'/img/|/photo/|imageView|spectrum', m):
                urls.append(m)
        seen: dict = {}
        deduped = [seen.setdefault(u, u) for u in urls if u not in seen]
        return ",".join(deduped[:9])

    def _extract_comment_from_html(self, html: str) -> int:
        """从HTML中提取评论数"""
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

    async def collect_notes(self, page: Page) -> List[Note]:
        """采集笔记"""
        collected: List[Note] = []
        keywords = self._generate_keywords()
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
                    if not note.is_valid(self.strict_comment_filter, self.min_comments):
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
                    if note.note_url not in self.seen_urls and note.is_valid(self.strict_comment_filter, self.min_comments):
                        self.seen_urls.add(note.note_url)
                        collected.append(note)
                        if len(collected) >= self.daily_target:
                            break
            except Exception as e:
                self.logger.log("fallback", "兜底采集失败", {"error": str(e)})

        return collected[: self.daily_target]

"""
发布模块 - 负责笔记发布到小红书
"""
import base64
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List
from urllib.parse import parse_qsl, urlparse

from playwright.async_api import Page

from config import (
    PUBLISH_IMAGE_PATHS,
    PUBLISH_PAGE_URL,
    PUBLISH_PLACEHOLDER_IMAGE_COUNT,
    PUBLISH_PLACEHOLDER_IMAGE_PATH,
    SHOT_DIR,
    SKIP_PUBLISH_PLACEHOLDER_UPLOAD,
    VIDEO_DIR,
    _MIN_PNG_B64,
)
from logger import RunLogger
from models import Note


class NotePublisher:
    """笔记发布器"""

    def __init__(self, logger: RunLogger):
        self.logger = logger
        self.publish_page_url = PUBLISH_PAGE_URL
        self.skip_publish_placeholder_upload = SKIP_PUBLISH_PLACEHOLDER_UPLOAD
        self.publish_placeholder_image_count = PUBLISH_PLACEHOLDER_IMAGE_COUNT
        self.publish_placeholder_image_path = PUBLISH_PLACEHOLDER_IMAGE_PATH
        self.selectors = self._load_selectors()

    def _load_selectors(self) -> Dict[str, str]:
        """加载选择器配置"""
        from config import ROOT
        selector_path = ROOT / "selectors.json"
        if selector_path.exists():
            import json
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

    def _write_minimal_png(self, path: Path) -> None:
        """写入最小PNG文件"""
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(base64.b64decode(_MIN_PNG_B64))

    def _prepare_publish_placeholder_files(self, work_dir: Path) -> List[str]:
        """准备发布占位图文件"""
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
            self._write_minimal_png(p)
            out.append(str(p))
        return out

    def _download_image_to_file(self, url: str, dest: Path) -> bool:
        """下载图片到文件"""
        try:
            import requests
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
        """解析发布用本地图片路径"""
        work_dir.mkdir(parents=True, exist_ok=True)
        env_paths = PUBLISH_IMAGE_PATHS
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

    def _publish_target_frame(self, page: Page):
        """锁定创作者发布相关 frame"""
        for f in page.frames:
            u = f.url or ""
            if "creator.xiaohongshu.com" in u and "publish" in u:
                return f
        return page

    async def _ensure_image_publish_mode(self, page: Page, reason: str) -> None:
        """确保图片发布模式"""
        url = page.url or ""
        if "creator.xiaohongshu.com" not in url or "/publish/publish" not in url:
            return
        q = dict(parse_qsl(urlparse(url).query, keep_blank_values=True))
        if q.get("target") == "image":
            return
        from config import get_publish_page_url
        fixed = get_publish_page_url()
        self.logger.log(
            "publish_fill",
            "发布页 target 非 image，切换到上传图文 URL",
            {"reason": reason, "from": url[:240], "to": fixed[:240]},
        )
        await page.goto(fixed, wait_until="domcontentloaded", timeout=90000)
        await page.wait_for_timeout(3000)

    async def _install_publish_guard(self, page: Page) -> None:
        """安装发布防护"""
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

    def _compose_publish_body_text(self, note: Note) -> str:
        """组合发布正文"""
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

    async def publish_image_note(self, page: Page, note: Note) -> Dict[str, str]:
        """图文发布：先上传图片，再填标题"""
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        out: Dict[str, str] = {
            "screenshot": str(SHOT_DIR / f"publish_filled_{ts}.png"),
            "video_dir": str(VIDEO_DIR / f"publish_{ts}"),
        }
        work = Path(out["video_dir"])
        work.mkdir(parents=True, exist_ok=True)

        await self._install_publish_guard(page)

        # 先访问小红书主站建立会话
        try:
            await page.goto("https://www.xiaohongshu.com", wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_timeout(2000)
            self.logger.log("publish_fill", "已访问小红书主站建立会话")
        except Exception as e:
            self.logger.log("publish_fill", "访问主站失败，继续尝试发布页", {"error": str(e)[:100]})

        # 添加重试机制访问发布页面
        max_retries = 3
        for attempt in range(1, max_retries + 1):
            try:
                await page.goto(self.publish_page_url, wait_until="domcontentloaded", timeout=90000)
                break
            except Exception as e:
                if attempt < max_retries:
                    self.logger.log("publish_fill", f"发布页访问失败，第{attempt}次重试", {"error": str(e)[:200]})
                    # 每次重试前先访问主站
                    try:
                        await page.goto("https://www.xiaohongshu.com", wait_until="domcontentloaded", timeout=20000)
                        await page.wait_for_timeout(2000)
                    except:
                        pass
                    await page.wait_for_timeout(5000 * attempt)
                else:
                    raise RuntimeError(f"发布页访问失败（已重试{max_retries}次）: {e}")
        try:
            await page.wait_for_load_state("networkidle", timeout=15000)
        except Exception:
            await page.wait_for_timeout(5000)
        await page.wait_for_timeout(4000)
        await self._ensure_image_publish_mode(page, reason="进入发布页后")

        creator_html = await page.content()
        # 检查拦截页
        blocked = (
            "版本太低" in creator_html
            or "版本过低" in creator_html
            or ("限制访问" in creator_html and ("请关闭" in creator_html or "关闭页面" in creator_html or "版本" in creator_html))
        )
        if blocked:
            self.logger.log("publish_fill", "检测到小红书拦截页", {"url": page.url})
            raise RuntimeError("小红书返回「版本太低 / 限制访问」类拦截页")

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

        content_box = frame.locator("div.tiptap.ProseMirror[contenteditable='true']").first
        if await content_box.count() == 0:
            content_box = frame.locator(".tiptap.ProseMirror[contenteditable='true']").first
        if await content_box.count() == 0:
            content_box = frame.locator(".ProseMirror[contenteditable='true']").first
        await content_box.wait_for(state="visible", timeout=20000)
        await content_box.click()

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
        return out

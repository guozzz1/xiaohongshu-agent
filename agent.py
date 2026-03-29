"""
主代理类 - 协调各个模块完成整个流程
"""
import asyncio
import time
from typing import List, Optional

from playwright.async_api import async_playwright

from browser_manager import BrowserManager
from collector import NoteCollector
from config import (
    DAILY_TARGET,
    LOGIN_WAIT_SECONDS,
    REQUIRE_INTERACTIVE_LOGIN,
    check_required_env,
)
from feishu_client import FeishuClient
from logger import RunLogger
from models import Note
from publisher import NotePublisher
from rewriter import NoteRewriter


class XhsAgent:
    """小红书自动化代理"""

    def __init__(self):
        self.daily_target = DAILY_TARGET
        self.logger = RunLogger()
        self.browser_manager = BrowserManager(self.logger)
        self.collector = NoteCollector(self.logger)
        self.rewriter = NoteRewriter(self.logger)
        self.publisher = NotePublisher(self.logger)
        self.feishu = FeishuClient()

    def _retry(self, fn, *args, stage: str = "retry", **kwargs):
        """重试机制"""
        last_err: Optional[Exception] = None
        for i in range(1, 4):  # 默认最多重试3次
            try:
                return fn(*args, **kwargs)
            except Exception as e:
                last_err = e
                self.logger.log(stage, f"第{i}次失败，自动重试", {"error": str(e)})
                time.sleep(1.5 * i)
        raise RuntimeError(f"{stage} 失败: {last_err}")

    async def collect_notes(self) -> List[Note]:
        """采集笔记"""
        collected: List[Note] = []
        async with async_playwright() as p:
            browser, context, page = await self.browser_manager.open_context_and_page(p)
            await self.browser_manager.ensure_login(
                context, page,
                require_interactive_login=REQUIRE_INTERACTIVE_LOGIN,
                login_wait_seconds=LOGIN_WAIT_SECONDS
            )
            await self.browser_manager.install_xhs_sign_route(page)
            collected = await self.collector.collect_notes(page)
            await context.close()
            if browser is not None:
                await browser.close()
        return collected

    async def run_daily_pipeline(self) -> None:
        """执行每日流程"""
        check_required_env()
        self.logger.log("pipeline", "开始执行全流程")

        # 1. 采集笔记
        notes = await self.collect_notes()
        if len(notes) < self.daily_target:
            self.logger.log("pipeline", "采集条数不足，已按规则自动补量但未达标", {"count": len(notes), "target": self.daily_target})

        # 2. 处理每条笔记
        for note in notes:
            if not note.is_valid():
                self.logger.log("validate", "单条校验失败，自动跳过", {"url": note.note_url})
                continue

            # 写入采集数据到飞书
            self._retry(self.feishu.upsert_record, note, stage="feishu_collect_write")
            self.logger.log("feishu", "采集数据写入完成", {"url": note.note_url})

            # 二创
            note = self.rewriter.rewrite(note)

            # 写入二创数据到飞书
            self._retry(self.feishu.upsert_record, note, stage="feishu_rewrite_write")
            self.logger.log("feishu", "分析+改写+二创写入完成", {"url": note.note_url})

        # 3. 发布（如果有笔记）
        if notes:
            async with async_playwright() as p:
                browser, context, page = await self.browser_manager.open_context_and_page(p, headless=False)
                await self.browser_manager.ensure_login(
                    context, page,
                    require_interactive_login=REQUIRE_INTERACTIVE_LOGIN,
                    login_wait_seconds=LOGIN_WAIT_SECONDS
                )
                await self.browser_manager.install_xhs_sign_route(page)
                publish_artifacts = await self.publisher.publish_image_note(page, notes[0])
                self.logger.log("publish_fill", "发布页填充完成（未发布）", publish_artifacts)
                await context.close()
                if browser is not None:
                    await browser.close()

        self.logger.log("pipeline", "流程结束", {"collected": len(notes)})

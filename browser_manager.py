"""
浏览器管理模块 - 管理Playwright浏览器实例
"""
import asyncio
import json
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import parse_qs, urlparse

from playwright.async_api import BrowserContext, Page, async_playwright

from config import (
    BROWSER_CHANNEL,
    CONNECT_CDP_URL,
    HEADLESS,
    PERSISTENT_USER_DATA_DIR,
    ROOT,
    STEALTH_BROWSER,
    USE_XHS_SIGN,
    XHS_COOKIES_JSON,
    _XHSHOW_AVAILABLE,
)
from logger import RunLogger


class BrowserManager:
    """浏览器管理器"""

    def __init__(self, logger: RunLogger):
        self.logger = logger
        self.browser_channel = BROWSER_CHANNEL
        self.headless = HEADLESS
        self.connect_cdp_url = CONNECT_CDP_URL
        self.persistent_user_data_dir = PERSISTENT_USER_DATA_DIR
        self.stealth_browser = STEALTH_BROWSER
        self._cookie_dict: Optional[Dict[str, str]] = None

    def _stealth_launch_kwargs(self) -> Dict[str, Any]:
        """降低被识别为自动化浏览器（仍可能被服务端风控）"""
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
        """应用隐身脚本到浏览器上下文"""
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
        """启动浏览器"""
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

    async def open_context_and_page(self, playwright, headless: bool = None) -> Tuple[Any, BrowserContext, Page]:
        """统一创建 page；支持 CDP 连接本机 Edge / 持久化 user-data-dir"""
        if headless is None:
            headless = self.headless

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

    def _normalize_cookies(self, cookies_obj: Any) -> List[Dict[str, Any]]:
        """规范化Cookie格式"""
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
            # 避免注入易过期/版本绑定 cookie 导致"版本过低，请关闭页面"
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

    async def ensure_login(self, context: BrowserContext, page: Page, require_interactive_login: bool = False, login_wait_seconds: int = 180) -> None:
        """确保登录状态"""
        # 连接本机已打开的 Edge 时不再注入 cookie，避免与真实会话冲突；仍解析 cookie 供 xhshow 签名用
        if self.connect_cdp_url:
            self.logger.log("login", "CONNECT_CDP 模式：跳过 cookie 注入，使用已登录会话")
            cookies_json = XHS_COOKIES_JSON
            if cookies_json:
                try:
                    cookies = json.loads(cookies_json)
                except json.JSONDecodeError:
                    cookies = cookies_json
                normalized = self._normalize_cookies(cookies)
                if normalized:
                    self._cookie_dict = {c["name"]: c["value"] for c in normalized}
            return

        cookies_json = XHS_COOKIES_JSON
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
                if require_interactive_login:
                    await self._wait_for_manual_login_if_needed(page, login_wait_seconds)
                else:
                    html = await page.content()
                    if "登录后看搜索结果" in html or "手机号登录" in html or ">登录<" in html:
                        raise RuntimeError("主站 cookie 已失效或无效。请重新登录小红书网页版，复制最新 cookies 到 XHS_COOKIES_JSON。")
                return
            self.logger.log("login", "cookies 格式无效，转账号密码流程")

        if not require_interactive_login:
            raise RuntimeError("未配置 XHS_COOKIES_JSON，且无人值守模式下不支持手动扫码。请配置 cookies 后重试。")
        await self._safe_goto(page, "https://www.xiaohongshu.com", stage="login_home")
        await page.wait_for_timeout(1500)
        await self._wait_for_manual_login_if_needed(page, login_wait_seconds)
        return

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
            # 页面不再出现登录弹窗，且左侧"登录"按钮消失，视为成功
            if "登录后看搜索结果" not in html and "手机号登录" not in html and ">登录<" not in html:
                self.logger.log("login", "检测到登录完成，继续自动流程")
                return
            await page.wait_for_timeout(step * 1000)
            waited += step
        raise RuntimeError("等待登录超时，请登录后重试")

    async def _safe_goto(self, page: Page, url: str, stage: str, goto_timeout_ms: int = 90000, search_goto_retry: int = 3) -> None:
        """安全访问页面"""
        last_err = None
        for i in range(1, search_goto_retry + 1):
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=goto_timeout_ms)
                return
            except Exception as e:
                last_err = e
                self.logger.log(stage, "页面访问超时，自动重试", {"url": url, "attempt": i, "error": str(e)})
                await page.wait_for_timeout(1500 * i)
        raise RuntimeError(f"{stage} 访问失败: {last_err}")

    async def install_xhs_sign_route(self, page: Page) -> None:
        """为小红书 API 请求注入 x-s/x-t/x-s-common 签名头"""
        if not _XHSHOW_AVAILABLE or not self._cookie_dict:
            return
        if not USE_XHS_SIGN:
            return

        from xhshow import Xhshow

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

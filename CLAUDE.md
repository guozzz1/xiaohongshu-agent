# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目简介

基于 **Python + Playwright** 的小红书内容采集与二创自动化流水线：按关键词采集笔记 → 写入飞书多维表格 → LLM 二创分析改写 → 预填小红书创作者发布页（不自动发布，仅填充表单供人工审核后点击发布）。

## 运行命令

```bash
# 安装依赖
pip install -r requirements.txt
python -m playwright install chromium

# 立即执行一次完整流程（采集 → 飞书 → 二创 → 预填发布页）
python main.py
# 或使用原始单文件版本
python xhs_agent.py now
```

## 配置

所有配置通过 `.env` 文件管理（参考 `.env.example`）。

**必需变量：**
- `FEISHU_APP_ID` / `FEISHU_APP_SECRET` / `FEISHU_APP_TOKEN` / `FEISHU_TABLE_ID`
- `XHS_COOKIES_JSON`（含 `web_session`，支持 JSON 对象格式或原始 cookie 字符串）

**常用可选变量：**
- `LLM_API_KEY` / `LLM_API_TYPE` / `LLM_MODEL` — 启用智能二创（支持 openai/azure/qwen/deepseek/moonshot）
- `CONNECT_CDP_URL` — 连接已打开的 Edge 调试端口（`http://127.0.0.1:9222`），避免反自动化检测
- `PERSISTENT_USER_DATA_DIR` — 持久化浏览器上下文目录，复用登录态（推荐设为 `.xhs_profile`）
- `HEADLESS=1` — 无头模式
- `DAILY_TARGET` / `MIN_COMMENTS` — 采集数量与评论数过滤阈值

## 架构

### 模块依赖关系

```
main.py
  └── agent.py (XhsAgent)
        ├── browser_manager.py  # Playwright 浏览器生命周期、登录态、xhshow 签名注入
        ├── collector.py        # 关键词搜索 + 详情页采集，频控检测与重试
        ├── rewriter.py         # LLM 智能二创 / 模板二创
        │     └── llm_client.py # 多厂商 LLM API 统一封装
        ├── publisher.py        # 上传图片、填充标题/正文/标签，防止自动提交
        ├── feishu_client.py    # 飞书多维表格 upsert（按「原笔记链接」去重）
        ├── logger.py           # 结构化 JSONL 日志（输出到 artifacts/logs/）
        ├── config.py           # 所有配置项从 .env 读取，集中管理
        └── models.py           # Note 数据类，含 to_dict() 和 is_valid() 方法
```

### 数据流

1. **采集**：`collector.py` 通过 Playwright 在搜索页抓卡片、进详情页取完整数据，按 `MIN_COMMENTS` 过滤
2. **飞书写入**：`feishu_client.py` 将 `Note.to_dict()` upsert 到多维表格，字段名为中文（见 `models.py`）
3. **二创**：`rewriter.py` 调用 `llm_client.py` 生成「二创标题/正文/标签」，回写飞书
4. **预填发布**：`publisher.py` 打开创作者中心图文页（`target=image`），上传占位图后填充内容

### 关键设计细节

- **发布安全拦截**：`publisher.py` 通过 `page.route()` 拦截「发布/提交」类请求，防止意外自动发布
- **选择器外置**：`selectors.json` 存放页面 CSS/XPath 选择器，页面改版时只需修改此文件
- **签名注入**：`USE_XHS_SIGN=1` 时通过 `xhshow` 库为小红书 API 请求注入 `x-s/x-t/x-s-common`
- **产出目录**：`artifacts/logs/`（JSONL 日志）、`artifacts/screenshots/`（关键步骤截图）
- **关键词配置**：`config.py` 中 `CORE_KEYWORDS` 等列表控制采集搜索词；`MANDATORY_TAGS` 控制发布时强制附加的标签

### xhs_agent.py

根目录的 `xhs_agent.py` 是原始单文件版本（约 80KB），功能与模块化版本相同，可独立运行（`python xhs_agent.py now`）。模块化版本（`main.py` + 各模块）为当前主线。

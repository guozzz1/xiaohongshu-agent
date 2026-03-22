# 小红书内容采集与二创工作流 Agent

基于 **Python + Playwright** 的自动化流水线：在小红书侧按关键词采集笔记，将结构化数据写入 **飞书多维表格**，完成内容分析与二创字段更新后，自动打开 **创作者中心图文发布页** 并**预填标题与正文（含标签）**。

> **不自动发布**：脚本仅填充表单，并通过页面注入拦截「发布 / 提交」类操作；最终发布须人工审核后手动点击。

---

## 功能概览

| 模块 | 说明 |
|------|------|
| 采集 | 搜索页 / 详情页抓取候选笔记，按评论数等规则过滤 |
| 飞书 | 多维表 **upsert**（按「原笔记链接」去重更新） |
| 二创 | 分析 + 改写标题 / 正文等，回写表格 |
| 预填发布 | `target=image` 图文流：上传配图 → 填标题 → 主编辑器写入「二创正文 + 标签」 |
| 可运维 | JSONL 运行日志、关键步骤截图；选择器外置 `selectors.json` |

---

## 技术栈

- Python 3.10+（推荐）
- [Playwright](https://playwright.dev/python/)（Chromium / 本机 Edge 通道）
- [飞书开放平台](https://open.feishu.cn/) 多维表格 API
- 可选：[xhshow](https://pypi.org/project/xhshow/)（小红书接口签名，`USE_XHS_SIGN=1`）
- 定时：[APScheduler](https://apscheduler.readthedocs.io/)

---

## 快速开始

### 1. 克隆与依赖

```bash
git clone <你的仓库地址>
cd agent_project
python -m venv .venv

# Windows
.venv\Scripts\activate
# macOS/Linux
# source .venv/bin/activate

pip install -r requirements.txt
python -m playwright install chromium
```

### 2. 配置环境变量

```bash
copy .env.example .env
# 或: cp .env.example .env
```

编辑 `.env`：至少配置 **飞书** 与 **小红书登录**（见下表）。**切勿将 `.env` 提交到 Git**（仓库已提供 `.gitignore`）。

| 变量 | 说明 |
|------|------|
| `FEISHU_APP_ID` / `FEISHU_APP_SECRET` / `FEISHU_APP_TOKEN` / `FEISHU_TABLE_ID` | 飞书应用与目标数据表 |
| `XHS_COOKIES_JSON` | 小红书 Cookie（需含 `web_session` 等），单行 JSON 或 cookie 字符串 |
| `DAILY_TARGET` | 每日目标采集条数（默认 20） |
| `MIN_COMMENTS` | 最低评论数过滤（默认 200） |
| `XHS_PUBLISH_PAGE_URL` | 创作者发布页，默认已规范为 `target=image` 图文流 |

更多可选项见 `.env.example`（如 `CONNECT_CDP_URL` 连接已打开的 Edge、`PERSISTENT_USER_DATA_DIR` 持久化登录目录、`PUBLISH_IMAGE_PATHS` 发布用本地图片等）。

### 3. 选择器（必看）

页面改版后需调整根目录 **`selectors.json`**（搜索卡片、发布页标题/正文等）。图文发布以 **`target=image`** 为准；须**先上传图片**再出现完整编辑区。

### 4. 运行

```bash
# 立即跑一轮全流程（采集 → 飞书 → 改写 → 预填发布页）
python xhs_agent.py now
```

注意：命令为 **`now`**，不要打成中文句号 **`now。`**。

```bash
# 仅启动定时调度（默认每日 09:00 执行）
python xhs_agent.py
```

---

## 飞书多维表字段

表中需包含以下**列名**（与代码写入一致）：

| 序号 | 字段名 |
|------|--------|
| 1 | 采集日期 |
| 2 | 采集方式 |
| 3 | 来源关键词 |
| 4 | 原笔记链接 |
| 5 | 原笔记发布时间 |
| 6 | 原笔记点赞数 |
| 7 | 原笔记收藏数 |
| 8 | 原笔记评论数 |
| 9 | 原笔记标题 |
| 10 | 原笔记正文 |
| 11 | 原笔记标签 |
| 12 | 原笔记图片（截图/有效链接） |
| 13 | 可二创方向 |
| 14 | 内容分析 |
| 15 | 二创标题 |
| 16 | 二创正文 |
| 17 | 二创封面 |

---

## 产出目录（默认 `artifacts/`）

| 路径 | 内容 |
|------|------|
| `artifacts/logs/run_*.jsonl` | 结构化运行日志 |
| `artifacts/screenshots/` | 发布页填充结果截图等 |
| `artifacts/videos/` | 发布流程临时文件（如从 URL 下载的配图） |

运行后日志与截图可用于排查；**不要将含隐私的 `artifacts/` 整体提交到公开仓库**。

---

## 安全与合规

- 本项目用于**学习与内部效率场景**；请遵守小红书、飞书等平台服务条款与适用法律法规。
- **不得**将自动化用于垃圾营销、侵权或违反平台规则的行为。
- 密钥与 Cookie 仅保存在本地 `.env`，**勿泄露、勿入库**。

---

## 常见问题

- **一直等定时、不执行**：确认使用 `python xhs_agent.py now`（无中文标点）。
- **创作者页提示未登录**：更新 `XHS_COOKIES_JSON`，或使用 CDP 连接已登录的浏览器。
- **发布页找不到标题框**：确认 URL 为图文流 `target=image`，并已先上传图片（脚本会按配置使用占位图或下载图）。

---

## 许可证

若公开仓库，请自行添加 `LICENSE` 文件（如 MIT）。未添加前，默认保留所有权利。

# 小红书内容采集与二创自动化流水线

基于 **Python + Playwright** 的自动化流水线：按关键词采集小红书笔记 → 写入**飞书多维表格** → LLM 二创分析改写 → 预填**创作者中心图文发布页**（不自动发布，仅填充表单供人工审核后点击发布）。

---

## 功能概览

| 模块 | 说明 |
|------|------|
| 采集 | 搜索页 + 详情页抓取候选笔记，按评论数等规则过滤 |
| 飞书 | 多维表 **upsert**（按「原笔记链接」去重更新） |
| 二创 | LLM 分析改写标题 / 正文 / 标签，回写飞书表格 |
| 预填发布 | `target=image` 图文流：上传配图 → 填标题 → 写入二创正文与标签 |
| 安全拦截 | `page.route()` 拦截发布请求，防止意外自动提交 |
| 可运维 | JSONL 结构化日志、关键步骤截图；选择器外置 `selectors.json` |

---

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
python -m playwright install chromium
```

### 2. 配置环境变量

```bash
cp .env.example .env   # Windows: copy .env.example .env
```

编辑 `.env`，至少填入飞书与小红书登录配置（**勿将 `.env` 提交到 Git**）。

### 3. 运行

```bash
# 执行完整流程（采集 → 飞书 → 二创 → 预填发布页）
python main.py

# 或使用原始单文件版本
python xhs_agent.py now
```

---

## 配置说明

### 必需变量

| 变量 | 说明 |
|------|------|
| `FEISHU_APP_ID` / `FEISHU_APP_SECRET` | 飞书应用凭证 |
| `FEISHU_APP_TOKEN` / `FEISHU_TABLE_ID` | 目标多维表格地址 |
| `XHS_COOKIES_JSON` | 小红书 Cookie（需含 `web_session`，支持 JSON 对象或原始字符串） |

### 常用可选变量

| 变量 | 说明 |
|------|------|
| `LLM_API_KEY` / `LLM_API_TYPE` / `LLM_MODEL` | 启用智能二创（支持 openai / azure / qwen / deepseek / moonshot） |
| `CONNECT_CDP_URL` | 连接已打开的 Edge 调试端口（如 `http://127.0.0.1:9222`），降低反自动化风险 |
| `PERSISTENT_USER_DATA_DIR` | 持久化浏览器上下文目录，复用登录态（推荐设为 `.xhs_profile`） |
| `HEADLESS` | 设为 `1` 开启无头模式 |
| `DAILY_TARGET` | 每日目标采集条数（默认 20） |
| `MIN_COMMENTS` | 最低评论数过滤阈值（默认 200） |

完整配置项见 `.env.example` 与 `CONFIG_GUIDE.md`。

---

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
        ├── feishu_client.py    # 飞书多维表格 upsert（按原笔记链接去重）
        ├── logger.py           # 结构化 JSONL 日志（输出到 artifacts/logs/）
        ├── config.py           # 所有配置项从 .env 读取，集中管理
        └── models.py           # Note 数据类，含 to_dict() 和 is_valid() 方法
```

### 数据流

```
采集 (collector.py)
  → 飞书写入 (feishu_client.py)
  → LLM 二创 (rewriter.py + llm_client.py)
  → 回写飞书
  → 预填发布页 (publisher.py)
```

---

## 飞书多维表字段

数据表需包含以下列名（与代码写入字段一致）：

| 序号 | 字段名 | 序号 | 字段名 |
|------|--------| ------|--------|
| 1 | 采集日期 | 10 | 原笔记正文 |
| 2 | 采集方式 | 11 | 原笔记标签 |
| 3 | 来源关键词 | 12 | 原笔记图片 |
| 4 | 原笔记链接 | 13 | 可二创方向 |
| 5 | 原笔记发布时间 | 14 | 内容分析 |
| 6 | 原笔记点赞数 | 15 | 二创标题 |
| 7 | 原笔记收藏数 | 16 | 二创正文 |
| 8 | 原笔记评论数 | 17 | 二创封面 |
| 9 | 原笔记标题 | | |

---

## 产出目录

| 路径 | 内容 |
|------|------|
| `artifacts/logs/` | 结构化 JSONL 运行日志 |
| `artifacts/screenshots/` | 关键步骤截图 |

---

## 关键设计细节

- **发布安全拦截**：`publisher.py` 通过 `page.route()` 拦截发布/提交类请求，防止意外自动发布
- **选择器外置**：`selectors.json` 存放页面 CSS/XPath 选择器，页面改版时只需修改此文件
- **签名注入**：`USE_XHS_SIGN=1` 时通过 `xhshow` 库为小红书 API 请求注入 `x-s/x-t/x-s-common`
- **关键词配置**：`config.py` 中 `CORE_KEYWORDS` 列表控制采集搜索词；`MANDATORY_TAGS` 控制发布时强制附加的标签
- **单文件备选**：`xhs_agent.py` 为原始单文件版本（约 80KB），功能与模块化版本相同，可独立运行

---

## 安全与合规

- 本项目用于**学习与内部效率场景**，请遵守小红书、飞书等平台服务条款与适用法律法规
- **不得**将自动化用于垃圾营销、侵权或违反平台规则的行为
- 密钥与 Cookie 仅保存在本地 `.env`，**勿泄露、勿入库**

---

## 常见问题

- **不执行只等待**：确认使用 `python xhs_agent.py now`（注意无中文标点）
- **创作者页提示未登录**：更新 `XHS_COOKIES_JSON`，或使用 CDP 连接已登录的浏览器
- **发布页找不到标题框**：确认 URL 为图文流 `target=image`，脚本会先上传占位图再填充内容

---

如有问题，请提交 Issue 或联系作者。

<p align="left">
  <img src="https://github.com/user-attachments/assets/f1277176-0b3b-4149-a463-d8cefc74bd54" alt="contact" width="400">
</p>

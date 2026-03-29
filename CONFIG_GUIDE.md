# 配置指南 - 执行程序前的准备

## ✅ 当前已配置

你的 `.env` 文件已经配置了以下必需项：

| 配置项 | 状态 | 说明 |
|--------|------|------|
| XHS_COOKIES_JSON | ✅ 已配置 | 包含 web_session，有效 |
| FEISHU_APP_ID | ✅ 已配置 | cli_a934e0f7e9f89bef |
| FEISHU_APP_SECRET | ✅ 已配置 | 78eaee7PwchV64tYYvuFJhid7noHW1Tl |
| FEISHU_APP_TOKEN | ✅ 已配置 | Lv7ibXCiValnMOs3SULcZnWLnJf |
| FEISHU_TABLE_ID | ✅ 已配置 | tblsZfsj8CsYxaYm |
| CONNECT_CDP_URL | ✅ 已配置 | http://127.0.0.1:9222 |
| USE_XHS_SIGN | ✅ 已配置 | 0（禁用签名） |
| REQUIRE_INTERACTIVE_LOGIN | ✅ 已配置 | 0（无人值守模式） |
| PERSISTENT_USER_DATA_DIR | ✅ 已配置 | .xhs_profile |

## 📋 执行前需要完成的步骤

### 步骤 1：安装依赖包

```bash
pip install -r requirements.txt
playwright install
```

### 步骤 2：启动 Edge 浏览器（必需）

由于你配置了 `CONNECT_CDP_URL=http://127.0.0.1:9222`，需要先启动 Edge 浏览器并开启调试端口：

**Windows 命令：**
```cmd
"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe" --remote-debugging-port=9222 --user-data-dir=D:\edge_xhs_cdp
```

**或者创建快捷方式：**
1. 右键桌面 → 新建 → 快捷方式
2. 输入位置：
   ```
   "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe" --remote-debugging-port=9222 --user-data-dir=D:\edge_xhs_cdp
   ```
3. 命名为 "Edge调试模式"
4. 双击启动

**启动后：**
- 会打开一个新的 Edge 窗口
- 在这个窗口中手动登录小红书创作者中心：https://creator.xiaohongshu.com
- 保持这个窗口不要关闭

### 步骤 3：验证浏览器连接

启动 Edge 后，访问 http://127.0.0.1:9222/json/version 确认调试端口已开启。

应该看到类似这样的 JSON 响应：
```json
{
  "Browser": "Edge/120.0.0.0",
  "Protocol-Version": "1.0",
  ...
}
```

## 🚀 执行程序

### 立即执行
```bash
python main.py now
```

### 定时任务（每日 09:00）
```bash
python main.py
```

## ⚙️ 可选配置

### 1. 启用智能二创（大模型）

如果你想使用 AI 智能改写内容，添加以下配置到 `.env`：

```env
# 大模型API配置
LLM_API_TYPE=openai  # 可选: openai, azure, qwen, deepseek, moonshot
LLM_API_KEY=你的API密钥
LLM_API_BASE_URL=https://api.openai.com/v1
LLM_MODEL=gpt-3.5-turbo
LLM_TEMPERATURE=0.7
LLM_MAX_TOKENS=1000
```

**支持的模型：**
- OpenAI (GPT-3.5/4)
- Azure OpenAI
- 通义千问 (qwen)
- DeepSeek
- Moonshot

### 2. 启用小红书签名

如果你想启用 API 签名（降低被检测风险），需要：

1. 安装 xhshow 库：
   ```bash
   pip install xhshow
   ```

2. 修改 `.env`：
   ```env
   USE_XHS_SIGN=1
   ```

### 3. 自定义发布图片

如果你想使用自定义图片发布，添加：

```env
# 发布页实际上传图片（逗号分隔本地路径）
PUBLISH_IMAGE_PATHS=D:\path\to\image1.jpg,D:\path\to\image2.jpg
```

### 4. 调整采集参数

```env
# 每日采集目标数量
DAILY_TARGET=20

# 最小评论数过滤
MIN_COMMENTS=200

# 是否严格过滤评论数
STRICT_COMMENT_FILTER=1

# 请求间隔（秒）
MIN_REQUEST_INTERVAL_SECONDS=2.2
MAX_REQUEST_INTERVAL_SECONDS=5.8
```

## 🔍 常见问题

### Q1: 提示"无法连接 CDP"
**原因：** Edge 浏览器未启动或调试端口未开启

**解决：**
1. 确保已按步骤 2 启动 Edge
2. 访问 http://127.0.0.1:9222/json/version 验证
3. 如果不行，尝试关闭所有 Edge 窗口后重新启动

### Q2: 提示"创作者中心未登录"
**原因：** 在调试模式的 Edge 中未登录小红书

**解决：**
1. 在调试模式的 Edge 窗口中访问 https://creator.xiaohongshu.com
2. 完成登录
3. 保持窗口打开

### Q3: 提示"版本太低/限制访问"
**原因：** 被小红书风控检测

**解决：**
1. 确保 `STEALTH_BROWSER=1`（默认已开启）
2. 使用真实的 Edge 浏览器（CDP 模式）
3. 清除 `.xhs_profile` 目录后重试
4. Cookie 中去掉 `webBuild`、`loadts` 字段

### Q4: 飞书写入失败
**原因：** 飞书应用权限不足或表格字段不匹配

**解决：**
1. 检查飞书应用是否有 bitable 权限
2. 确认表格字段名称与代码中一致
3. 查看飞书开放平台的应用权限设置

## 📊 执行流程

程序执行时会按以下流程运行：

```
1. 检查环境变量
   ↓
2. 启动浏览器（连接已打开的 Edge）
   ↓
3. 采集小红书笔记
   ↓
4. 写入采集数据到飞书
   ↓
5. 智能二创（如果配置了大模型）
   ↓
6. 写入二创数据到飞书
   ↓
7. 填充发布页面（不实际发布）
   ↓
8. 完成
```

## 🎯 快速开始

```bash
# 1. 安装依赖
pip install -r requirements.txt
playwright install

# 2. 启动 Edge 调试模式
"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe" --remote-debugging-port=9222 --user-data-dir=D:\edge_xhs_cdp

# 3. 在调试模式的 Edge 中登录小红书创作者中心

# 4. 执行程序
python main.py now
```

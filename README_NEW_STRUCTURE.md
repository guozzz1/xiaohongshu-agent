# 小红书自动化代理 - 模块化结构

## 项目结构

```
xhs_agent/
├── config.py              # 配置和常量
├── models.py              # 数据模型
├── llm_client.py          # 大模型客户端
├── logger.py              # 日志记录器
├── feishu_client.py       # 飞书客户端
├── browser_manager.py     # 浏览器管理
├── collector.py           # 采集模块
├── rewriter.py            # 二创模块
├── publisher.py           # 发布模块
├── agent.py               # 主代理类
├── main.py                # 入口文件
├── requirements.txt       # 依赖包
├── .env                   # 环境变量
├── selectors.json         # 选择器配置
└── xhs_agent.py           # 原始文件（可删除）
```

## 模块说明

### 1. config.py - 配置和常量
- 集中管理所有配置项和常量
- 包括路径配置、关键词配置、飞书配置、小红书配置、浏览器配置等
- 提供配置检查和获取函数

### 2. models.py - 数据模型
- 定义 `Note` 数据类
- 提供数据验证和转换方法

### 3. llm_client.py - 大模型客户端
- 支持多种AI模型（OpenAI、Azure、通义千问、DeepSeek、Moonshot）
- 实现智能二创功能
- 自动解析API返回的JSON内容

### 4. logger.py - 日志记录器
- 记录运行日志到JSONL文件
- 支持结构化日志输出

### 5. feishu_client.py - 飞书客户端
- 飞书多维表格API封装
- 实现数据的增删改查
- 自动处理字段映射和规范化

### 6. browser_manager.py - 浏览器管理
- Playwright浏览器实例管理
- 支持CDP连接、持久化上下文
- 实现隐身模式和签名注入
- 登录状态管理

### 7. collector.py - 采集模块
- 小红书笔记采集逻辑
- 支持关键词搜索和详情页采集
- 实现频控检测和重试机制
- 评论数提取和验证

### 8. rewriter.py - 二创模块
- 笔记内容智能改写
- 支持大模型二创和模板二创
- 自动生成标题、正文、标签

### 9. publisher.py - 发布模块
- 小红书笔记发布逻辑
- 图片上传和内容填充
- 发布防护机制

### 10. agent.py - 主代理类
- 协调各个模块完成整个流程
- 实现每日流水线
- 错误处理和重试机制

### 11. main.py - 入口文件
- 程序入口点
- 支持立即执行和定时任务

## 使用方法

### 立即执行
```bash
python main.py now
```

### 定时任务（每日 09:00）
```bash
python main.py
```

## 配置说明

所有配置项都在 `.env` 文件中，参考 `.env.example` 进行配置。

### 必需配置
- `FEISHU_APP_ID` - 飞书应用ID
- `FEISHU_APP_SECRET` - 飞书应用密钥
- `FEISHU_APP_TOKEN` - 飞书应用Token
- `FEISHU_TABLE_ID` - 飞书表格ID
- `XHS_COOKIES_JSON` - 小红书Cookie

### 可选配置
- `LLM_API_KEY` - 大模型API密钥（启用智能二创）
- `DAILY_TARGET` - 每日采集目标数量
- `MIN_COMMENTS` - 最小评论数过滤
- `HEADLESS` - 是否无头模式运行

## 依赖安装

```bash
pip install -r requirements.txt
playwright install
```

## 模块依赖关系

```
main.py
  └── agent.py
        ├── browser_manager.py
        ├── collector.py
        ├── rewriter.py
        │     └── llm_client.py
        ├── publisher.py
        ├── feishu_client.py
        ├── logger.py
        ├── config.py
        └── models.py
```

## 优势

1. **模块化设计** - 每个模块职责单一，易于维护
2. **可扩展性** - 可以轻松添加新功能或替换模块
3. **可测试性** - 每个模块可以独立测试
4. **代码复用** - 模块可以在其他项目中复用
5. **清晰的接口** - 模块之间通过明确的接口通信

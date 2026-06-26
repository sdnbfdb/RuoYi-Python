# RuoYi-Python 智能知识库与文档处理系统

基于 Python Flask 框架构建的智能知识库管理系统，集成 LangChain Multi-Agent AI 智能体、MCP 协议服务、NLP 表格分析和移动端扫码交互。

## 核心功能

### 1. 知识库系统
- **向量数据库**：基于 ChromaDB 的高效语义检索（768维 Embedding）
- **文档管理**：支持多格式文档（图片、Excel、Word、PDF等）的上传、解析和存储
- **智能检索**：支持按标题、内容、标签等多维度搜索
- **知识图谱**：可视化展示知识关系，支持鼠标滚轮缩放、拖动平移、节点交互
- **数据库持久化**：MySQL 存储，支持 CRUD 和统计查询

### 2. AI 智能体 (LangChain Multi-Agent)
- **5种Agent**：知识库助手、个人助手、搜索助手、NLP助手、全能助手
- **Function Calling**：基于 DashScope 原生函数调用，工具自动调度
- **真实工具接入**：博查搜索API、通义千问图片生成(wanx-v1)、组织架构查询、知识库数据库查询
- **LangChain集成**：基于 LangChain StructuredTool 工具封装和 Agent 编排
- **ReAct Agent**：具备反思和规划能力的增强型智能体
- **MCP 协议服务**：Model Context Protocol 标准化工具调用接口

### 3. NLP 表格处理
- **表头向量化**：基于 BERT/RoBERTa 的表头语义编码
- **表格关联分析**：多表连接和条件检索
- **数据检索**：灵活的多表数据查询
- **文本处理**：文本清理、分块、信息提取

### 4. 用户认证系统
- **JWT 鉴权**：基于 Token 的用户认证
- **用户管理**：注册、登录、个人信息编辑、头像上传
- **组织架构**：可视化组织架构管理，支持 1400+ 部门层级展示

### 5. 移动端交互
- **扫码连接**：手机扫码与电脑端建立 WebSocket 连接
- **实时预览**：手机端实时预览文档内容
- **文件传输**：支持文档、图片下载到手机
- **心跳检测**：自动保持连接活跃

### 6. 内容创作
- **多种格式模板**：小红书、公众号、朋友圈、短视频文案、论文等
- **智能生成**：基于通义千问的文案创作辅助
- **带图文案**：AI 自动生成配图 + 文字内容
- **PDF导出**：支持高质量 PDF 输出

## 快速开始

### 环境要求
- Python 3.8+
- MySQL 5.7+
- Node.js（前端依赖，可选）

### 安装

```bash
# 1. 克隆项目
git clone https://github.com/sdnbfdb/RuoYi-Python.git
cd RuoYi-Python

# 2. 创建虚拟环境
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # Linux/Mac

# 3. 安装 Python 依赖
pip install -r back/requirements.txt

# 4. 安装 LangChain 及 AI 相关依赖
pip install chromadb langchain langchain-community langchain-openai langgraph mcp dashscope sentence-transformers

# 5. 配置环境变量
cp back/.env.example back/old/.env
# 编辑 back/old/.env 填入实际 API Key 和数据库配置

# 6. 初始化数据库
# 在 MySQL 中创建数据库并执行 back/sql/init.sql

# 7. 前端依赖（可选）
cd front && npm install && cd ..
```

### 启动服务
```bash
cd back
python app.py
```

服务启动后访问：
- **后端 API**：`http://localhost:5000`
- **智能体页面**：`http://localhost:5000/front/agent.html`
- **知识库管理**：`http://localhost:5000/front/knowledge.html`
- **组织架构**：`http://localhost:5000/front/organization.html`

> **注意**：使用前请确保 `back/old/.env` 配置文件存在且包含必要的 API 密钥和数据库配置。

## 架构设计

### 模块关系

```
┌─────────────────────────────────────────────────────────────────┐
│                      app.py (Flask 主应用)                      │
│              路由注册 | 静态文件 | 中间件 | CORS                 │
└──────────────────────────┬──────────────────────────────────────┘
                           │
           ┌───────────────┼───────────────────┐
           │               │                   │
           ▼               ▼                   ▼
    ┌────────────┐  ┌────────────┐     ┌────────────┐
    │   old/     │  │   nlp/     │     │  knowledge/ │
    │ 旧版兼容层  │  │ NLP核心模块│     │ 知识库模块  │
    │ • API封装  │  │ • 文本处理 │     │ • 数据访问  │
    │ • 工具函数  │  │ • 向量化   │     │ • 文件上传  │
    │ • 手机连接  │  │ • 表格分析 │     │ • 统计查询  │
    └─────┬──────┘  └─────┬──────┘     └─────┬──────┘
          │               │                   │
          └───────┬───────┴───────────┬───────┘
                  │                   │
                  ▼                   ▼
     ┌──────────────────────────────────────┐
     │       ruoyi_langchain/ (AI智能体)     │
     │  ┌────────────────────────────────┐  │
     │  │  tools/ (LangChain工具封装)     │  │
     │  │  • knowledge_tool (知识库查询)  │  │
     │  │  • organization_tool (组织架构)  │  │
     │  │  • web_search_tool (博查搜索)   │  │
     │  │  • image_generation_tool (生图)  │  │
     │  │  • nlp_text_tool (文本处理)     │  │
     │  │  • nlp_table_tool (表格分析)     │  │
     │  └────────────────────────────────┘  │
     │  ┌────────────────────────────────┐  │
     │  │  agents/ (5种Agent)            │  │
     │  │  • BaseAgent (requests直调)     │  │
     │  │  • KnowledgeAgent | Personal    │  │
     │  │  • NLPAgent | FullAgent        │  │
     │  └────────────────────────────────┘  │
     │  routes/ | agent_factory.py          │
     └──────────────────────────────────────┘

     ┌──────────────┐    ┌────────────────┐
     │  agent/      │    │  mcp/          │
     │ ReAct Agent  │    │ MCP协议服务    │
     │ (反思+规划)  │    │ (标准化工具)   │
     └──────────────┘    └────────────────┘
```

### 各模块职责

| 模块 | 目录 | 职责 |
|------|------|------|
| **app.py** | `back/app.py` | Flask 主入口，路由注册，CORS，静态文件服务 |
| **ruoyi_langchain** | `back/ruoyi_langchain/` | LangChain Multi-Agent 框架，封装 nlp/old/knowledge 为工具 |
| **old** | `back/old/` | 旧版兼容层，提供 DashScope API 封装、搜索/图片/组织等业务工具 |
| **nlp** | `back/nlp/` | NLP 核心功能：文本清理、BERT 向量化、表格关联分析、知识处理 |
| **knowledge** | `back/knowledge/` | 知识库数据访问层（CRUD、文件上传、统计） |
| **agent** | `back/agent/` | ReAct Agent，具备反思-行动循环的增强型智能体 |
| **mcp** | `back/mcp/` | MCP (Model Context Protocol) 服务端，标准化工具调用接口 |
| **routes** | `back/routes/` | 聊天路由、知识库路由蓝图 |
| **layer/user** | `back/layer/user/` | 用户管理、登录注册、组织架构、文件上传 |
| **front** | `front/` | 原生 HTML/JS 前端页面 |

### 调用链路

1. **传统聊天**：`app.py → old/api_call.py → DashScope API`
2. **Agent 工具调用**：`app.py → ruoyi_langchain → Function Calling → tools/ → old/nlp/knowledge → DashScope 总结`
3. **知识库操作**：`app.py → knowledge/ → MySQL → 返回结果`
4. **NLP 表格分析**：`ruoyi_langchain → nlp_table_tool → nlp/excel/ → BERT 向量化 + 关联分析`
5. **联网搜索**：`ruoyi_langchain → web_search_tool → 博查搜索 API → 格式化结果`
6. **图片生成**：`ruoyi_langchain → image_generation_tool → 通义千问 wanx-v1 → 异步轮询`

## 项目结构

```
ruoyi/
├── back/                           # 后端服务
│   ├── app.py                      # Flask 主应用入口
│   ├── config.py                   # 配置文件
│   ├── requirements.txt            # 依赖列表
│   │
│   ├── ruoyi_langchain/            # LangChain AI 模块
│   │   ├── agents/                 # Agent 实现
│   │   │   ├── base_agent.py           # Agent 基类（requests + verify=False 调用 DashScope）
│   │   │   ├── knowledge_agent.py      # 知识库助手
│   │   │   ├── personal_agent.py       # 个人助手
│   │   │   ├── nlp_agent.py            # NLP 助手
│   │   │   └── full_agent.py           # 全能助手
│   │   ├── tools/                  # LangChain 工具
│   │   │   ├── knowledge_tool.py           # 知识库查询
│   │   │   ├── organization_tool.py        # 组织架构查询
│   │   │   ├── web_search_tool.py          # 博查联网搜索
│   │   │   ├── image_generation_tool.py    # 通义千问图片生成
│   │   │   ├── nlp_table_tool.py           # 表格分析工具
│   │   │   ├── nlp_text_tool.py            # 文本处理工具
│   │   │   └── table_tool.py              # 表格工具
│   │   ├── routes/
│   │   │   └── langchain_routes.py       # LangChain API 路由
│   │   ├── agent_factory.py        # Agent 工厂
│   │   └── chat_service.py         # 聊天服务
│   │
│   ├── agent/                      # ReAct Agent
│   │   └── react_agent.py          # 反思-行动循环智能体
│   │
│   ├── mcp/                        # MCP 协议服务
│   │   └── server.py               # MCP Server（知识库/表格/搜索工具）
│   │
│   ├── nlp/                        # NLP 核心模块
│   │   ├── total.py                # 对话系统主逻辑
│   │   ├── understand.py           # 语义理解
│   │   ├── vector_db.py            # 向量数据库
│   │   ├── process_knowledge.py    # 知识库处理
│   │   ├── clear.py                # 文本清理
│   │   ├── code.py                 # 代码处理
│   │   └── excel/                  # 表格处理
│   │       ├── header_embedding.py     # 表头向量化（BERT）
│   │       ├── header_matrix.py        # 关联矩阵分析
│   │       ├── table_retriever.py      # 数据检索
│   │       ├── excel_viewer.py          # Excel 查看器
│   │       └── data/                    # 测试数据
│   │
│   ├── knowledge/                  # 知识库模块
│   │   └── knowledge.py            # 知识库数据访问
│   │
│   ├── vector_store/               # 向量存储
│   │   └── chroma_store.py         # ChromaDB 封装（DashScope Embedding）
│   │
│   ├── routes/                     # API 路由蓝图
│   │   ├── chat_routes.py          # 聊天路由
│   │   └── knowledge_routes.py     # 知识库路由
│   │
│   ├── layer/user/                 # 用户功能层
│   │   ├── login.py                # 登录认证
│   │   ├── register.py             # 用户注册
│   │   ├── user.py                 # 用户管理
│   │   ├── edit.py                 # 信息编辑
│   │   ├── organization.py         # 组织架构（1406 条数据）
│   │   └── upload.py               # 文件上传
│   │
│   ├── old/                        # 旧版兼容层
│   │   ├── api_call.py             # DashScope API 封装（requests + verify=False）
│   │   ├── phone/link.py           # 移动端连接
│   │   ├── tool/tool.py            # 业务工具（搜索/图片/组织/知识库/视频）
│   │   └── .env                    # 环境变量配置（不纳入版本控制）
│   │
│   ├── format/                     # 内容格式模板
│   │   ├── context.md              # 论文格式规范
│   │   ├── red book.md             # 小红书格式规范
│   │   ├── Official Account.md     # 公众号格式规范
│   │   ├── friend.md               # 朋友圈格式规范
│   │   └── quick video.md          # 短视频文案规范
│   │
│   ├── middleware/                 # 中间件（日志、错误处理）
│   ├── utils/                      # 工具函数（auth/response/validators）
│   ├── sql/                        # SQL 脚本（初始化/迁移）
│   ├── migrations/                 # 数据库迁移脚本
│   ├── data/                       # 静态数据（组织架构、用户、知识库）
│   ├── video/                      # 视频处理工具
│   └── uploads/                    # 上传文件目录
│
├── front/                          # 前端页面（静态 HTML/JS）
│   ├── agent.html                  # 智能体对话页面（扫码上传、AI对话、图表生成）
│   ├── knowledge.html              # 知识库管理页面
│   ├── organization.html           # 组织架构管理页面
│   ├── index.html                  # 首页/仪表盘
│   ├── login.html                  # 登录页面
│   ├── register.html               # 注册页面
│   ├── edit.html                   # 信息编辑页面
│   ├── my.html                     # 个人中心
│   ├── operation.html              # 操作记录页面
│   ├── nav.html                    # 导航栏组件
│   ├── api.js                      # 前端 API 封装
│   └── auth.js                     # 认证逻辑
│
├── .gitignore                      # Git 忽略规则
└── README.md                       # 项目说明
```

## API 接口

### 用户认证
```
POST /api/auth/login                    # 用户登录
POST /api/auth/register                 # 用户注册
GET  /api/auth/profile                  # 获取用户信息
```

### 知识库
```
GET    /api/knowledge/list              # 获取知识库列表
GET    /api/knowledge/<id>              # 获取知识库详情
POST   /api/knowledge/create            # 创建知识库
PUT    /api/knowledge/update/<id>       # 更新知识库
DELETE /api/knowledge/delete/<id>       # 删除知识库
POST   /api/knowledge/upload            # 上传文件
GET    /api/knowledge/statistics        # 获取统计信息
POST   /api/knowledge/<id>/qa           # 知识库问答
GET    /uploads/knowledge/<filename>    # 访问附件文件
```

### 聊天
```
POST   /api/chat                        # 发送消息（支持 @robot 调用）
POST   /api/chat/image                  # 图片识别聊天
GET    /api/chat/history                # 获取聊天历史
POST   /api/chat/history                # 保存聊天历史
DELETE /api/chat/history/<id>           # 删除聊天历史
```

### LangChain Agent
```
POST /api/langchain/chat                # Agent 对话
  请求: { message, agent_type, model }
  agent_type: knowledge | personal | search | nlp | full
  响应: { success, data: { reply, agent_type } }
GET  /api/langchain/agents              # 获取 5 种 Agent 详情
GET  /api/langchain/tools               # 获取所有工具列表及参数
```

### 移动端
```
GET  /api/qrcode/server-url             # 获取服务端地址（扫码用）
POST /api/qrcode/heartbeat              # 心跳检测
POST /api/qrcode/disconnect             # 断开连接
POST /api/phone/send                    # 发送文档到手机
GET  /api/phone/messages                # 获取手机端消息
```

### 静态资源
```
GET  /image/<filename>                  # 上传图片访问
GET  /media/photo/<filename>            # AI 生成图片访问
GET  /old/image/<filename>              # 旧版图片访问
```

## 前端页面

| 页面 | 文件 | 功能 |
|------|------|------|
| **智能体对话** | `agent.html` | AI 对话、扫码上传、文件拖拽、图表生成、带图文案 |
| **知识库管理** | `knowledge.html` | 知识库 CRUD、文件上传、搜索过滤、知识图谱 |
| **组织架构** | `organization.html` | 部门树形展示、搜索、层级导航 |
| **首页** | `index.html` | 仪表盘、快捷入口 |
| **登录/注册** | `login.html` / `register.html` | 用户认证 |
| **个人中心** | `my.html` | 个人信息、头像上传 |
| **信息编辑** | `edit.html` | 资料编辑 |
| **操作记录** | `operation.html` | 操作日志 |

## 技术栈

| 分类 | 技术 |
|------|------|
| **后端框架** | Flask 3.0 + Flask-CORS |
| **AI 框架** | LangChain, LangGraph, MCP |
| **大模型** | 通义千问 (DashScope qwen-turbo/qwen-plus) |
| **图片生成** | 通义千问 wanx-v1 (异步任务) |
| **联网搜索** | 博查搜索 API |
| **向量数据库** | ChromaDB |
| **Embedding** | DashScope text-embedding-v1 (768维) |
| **NLP 模型** | BERT/RoBERTa (HuggingFace Transformers, sentence-transformers) |
| **数据库** | MySQL + PyMySQL |
| **前端** | 原生 HTML/JS + jQuery |
| **生产部署** | Waitress WSGI Server |

## ChromaDB 配置

### 存储配置
| 配置项 | 值 | 说明 |
|--------|-----|------|
| **存储路径** | `back/chroma_db/` | 本地持久化存储目录 |
| **数据库大小** | ~1.66 MB | 当前数据量（3个集合） |
| **集合数量** | 3个 | documents, headers, table_data |

### 向量配置
| 配置项 | 值 | 说明 |
|--------|-----|------|
| **向量维度** | 768维 | DashScope text-embedding-v1 模型输出 |
| **Embedding模型** | DashScope text-embedding-v1 | 阿里云通义千问 Embedding API |
| **距离度量** | 余弦相似度 | 默认相似度计算方式 |

### 分块配置
| 配置项 | 值 | 说明 |
|--------|-----|------|
| **Chunk大小** | 800字符 | 每个文本块的最大字符数 |
| **Chunk重叠** | 100字符 | 相邻块之间的重叠字符数 |

### 集合说明
| 集合名 | 数据类型 | 说明 |
|--------|----------|------|
| documents | 知识库文档 | 知识库内容分块存储 |
| headers | 表格表头 | Excel 表头向量 |
| table_data | 表格数据 | NLP 表格处理结果 |

## 环境变量

在 `back/old/.env` 中配置必要的环境变量：

```env
# DashScope API（通义千问）
API_KEY=sk-xxx                   # 主 API Key
QWEN_API_KEY=sk-xxx             # 备用 API Key

# 博查搜索 API
SEARCH_API_KEY=sk-xxx
SEARCH_API_ID=api-key-xxx
SEARCH_API_NAME=search

# 数据库配置（MySQL）
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=xxx
DB_NAME=ruoyi
DB_CHARSET=utf8mb4
```

> `.env` 文件已在 `.gitignore` 中忽略，不会被提交到 Git 仓库。

## 内容创作

系统支持以下内容类型的智能生成：

| 类型 | 说明 | 关键词 |
|------|------|--------|
| 小红书 | 小红书风格图文文案 | 小红书、配图文案、图文 |
| 公众号 | 公众号推文 | 公众号、推文 |
| 朋友圈 | 朋友圈文案 | 朋友圈 |
| 短视频 | 抖音/快手文案 | 抖音文案、短视频文案 |
| 论文 | 学术论文格式 | 论文、摘要、关键词 |

## 许可证

MIT License

# RuoYi-Python 智能知识库与文档处理系统

基于 Python Flask 框架构建的智能知识库管理系统，集成 LangChain AI 智能体，支持文档解析、向量检索、NLP表格分析和移动端交互。

## 核心功能

### 1. 知识库系统
- **向量数据库**：基于 ChromaDB 的高效语义检索
- **文档管理**：支持多格式文档（图片、Excel、Word等）的上传、解析和存储
- **智能检索**：支持按标题、内容、标签等多维度搜索
- **权限控制**：基于用户和组织的访问控制

### 2. AI 智能体
- **多类型Agent**：知识库助手、个人助手、NLP助手、全能助手
- **工具调用**：集成搜索、表格分析、图片生成等多种工具
- **LangChain集成**：基于 LangChain 的工具调用和Agent编排
- **MCP支持**：Model Context Protocol 协议支持

### 3. NLP 表格处理
- **表头向量化**：基于 BERT 的表头语义编码
- **表格关联分析**：多表连接和条件检索
- **数据检索**：灵活的多表数据查询

### 4. 移动端交互
- **扫码连接**：手机扫码与电脑端建立连接
- **实时预览**：手机端实时预览文档内容
- **文件下载**：支持文档下载到手机

### 5. 内容创作
- **多种格式模板**：小红书、公众号、朋友圈、短视频文案等
- **智能生成**：基于AI的文案创作辅助
- **PDF导出**：支持高质量PDF输出

## 快速开始

### 环境要求
- Python 3.8+
- Flask 2.0+
- ChromaDB
- LangChain
- PyTorch, Transformers (NLP)

### 安装依赖
```bash
# 创建虚拟环境
python -m venv .venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # Linux/Mac

# 安装依赖
pip install -r back/requirements.txt

# 可选：安装LangChain相关依赖
.venv\Scripts\pip.exe install chromadb langchain langchain-community langgraph mcp dashscope sentence-transformers
```

### 启动服务
```bash
cd back
python app.py
```

服务启动后访问：`http://localhost:5000`

> **注意**：使用前请确保 `.env` 配置文件存在且包含必要的API密钥。

## 模块关系

本项目有三个核心模块，它们之间的关系如下：

```
┌─────────────────────────────────────────────────────────────────┐
│                        app.py (主应用)                          │
│                    Flask 主入口，统一调度                         │
└──────────────────────────┬──────────────────────────────────────┘
                           │
           ┌───────────────┼───────────────┐
           │               │               │
           ▼               ▼               ▼
    ┌────────────┐  ┌────────────┐  ┌────────────┐
    │   old/     │  │   nlp/     │  │  knowledge/ │
    │ 旧版兼容模块 │  │ NLP核心模块 │  │  知识库模块 │
    └─────┬──────┘  └─────┬──────┘  └─────┬──────┘
          │               │               │
          │               │               │
          └───────┬───────┴───────┬─────┘
                  │               │
                  ▼               ▼
         ┌──────────────────────────────┐
         │       ruoyi_langchain/        │
         │      LangChain AI智能体模块     │
         │  ┌────────────────────────┐  │
         │  │  tools/ (封装为工具)    │  │
         │  │  • nlp_text_tool       │  │
         │  │  • nlp_table_tool     │  │
         │  │  • knowledge_tool      │  │
         │  │  • organization_tool   │  │
         │  └────────────────────────┘  │
         │  ┌────────────────────────┐  │
         │  │  agents/ (AI智能体)    │  │
         │  │  • KnowledgeAgent      │  │
         │  │  • PersonalAgent      │  │
         │  │  • NLPAgent           │  │
         │  │  • FullAgent          │  │
         │  └────────────────────────┘  │
         └──────────────────────────────┘
```

### 各模块职责

| 模块 | 目录 | 职责 | 依赖关系 |
|------|------|------|----------|
| **old** | `back/old/` | 旧版兼容模块，提供API调用封装、手机连接、旧版工具 | 被主应用和LangChain工具直接调用 |
| **nlp** | `back/nlp/` | NLP核心功能，包括文本清理、向量化、表格分析等 | 被LangChain工具调用，提供底层能力 |
| **ruoyi_langchain** | `back/ruoyi_langchain/` | LangChain AI智能体，封装nlp/old/knowledge为工具，供Agent调用 | 依赖nlp模块的底层功能 |

### 调用链路

1. **传统API调用** (不经过Agent)
   ```
   app.py → old/ (API调用/手机连接) → 返回结果
   ```

2. **知识库操作** (通过Agent)
   ```
   app.py → ruoyi_langchain → knowledge_tool → knowledge/ → ChromaDB
   ```

3. **NLP表格分析** (通过Agent)
   ```
   app.py → ruoyi_langchain → nlp_table_tool → nlp/excel/ → 返回分析结果
   ```

4. **NLP文本处理** (通过Agent)
   ```
   app.py → ruoyi_langchain → nlp_text_tool → nlp/clear.py → 返回处理结果
   ```

## 项目结构

```
ruoyi/
├── back/                      # 后端服务
│   ├── app.py                 # Flask 主应用入口
│   ├── config.py              # 配置文件
│   ├── requirements.txt       # 依赖列表
│   │
│   ├── ruoyi_langchain/       # LangChain AI模块
│   │   ├── agents/            # Agent实现
│   │   │   ├── base_agent.py      # Agent基类
│   │   │   ├── knowledge_agent.py # 知识库助手
│   │   │   ├── personal_agent.py  # 个人助手
│   │   │   ├── nlp_agent.py       # NLP助手
│   │   │   └── full_agent.py      # 全能助手
│   │   ├── tools/             # LangChain工具
│   │   │   ├── knowledge_tool.py   # 知识库工具
│   │   │   ├── nlp_table_tool.py   # 表格分析工具
│   │   │   ├── nlp_text_tool.py    # 文本处理工具
│   │   │   ├── organization_tool.py # 组织架构工具
│   │   │   ├── table_tool.py       # 表格工具
│   │   │   ├── image_generation_tool.py # 图片生成工具
│   │   │   └── web_search_tool.py  # 网络搜索工具
│   │   ├── routes/            # API路由
│   │   │   └── langchain_routes.py
│   │   ├── agent_factory.py   # Agent工厂
│   │   └── chat_service.py    # 聊天服务
│   │
│   ├── nlp/                   # NLP核心模块
│   │   ├── total.py           # 对话系统主逻辑
│   │   ├── understand.py      # 语义理解
│   │   ├── vector_db.py       # 向量数据库
│   │   ├── process_knowledge.py  # 知识库处理
│   │   ├── clear.py           # 文本清理
│   │   ├── code.py            # 代码处理
│   │   └── excel/             # 表格处理
│   │       ├── header_embedding.py   # 表头向量化
│   │       ├── header_matrix.py      # 关联矩阵分析
│   │       ├── table_retriever.py    # 数据检索
│   │       ├── excel_viewer.py        # Excel查看器
│   │       └── data/                  # 测试数据
│   │
│   ├── format/                # 内容格式模板
│   │   ├── context.md         # 论文格式规范
│   │   ├── red book.md        # 小红书格式规范
│   │   ├── Official Account.md # 公众号格式规范
│   │   ├── friend.md          # 朋友圈格式规范
│   │   └── quick video.md     # 短视频文案规范
│   │
│   ├── knowledge/             # 知识库模块
│   │   └── knowledge.py       # 知识库数据访问
│   │
│   ├── vector_store/          # 向量存储
│   │   └── chroma_store.py    # ChromaDB封装
│   │
│   ├── routes/                # API路由
│   │   ├── chat_routes.py     # 聊天路由
│   │   └── knowledge_routes.py # 知识库路由
│   │
│   ├── layer/                 # 功能层
│   │   └── user/             # 用户相关
│   │       ├── login.py       # 登录
│   │       ├── register.py    # 注册
│   │       ├── user.py        # 用户管理
│   │       ├── edit.py        # 编辑
│   │       ├── organization.py # 组织架构
│   │       └── upload.py       # 上传
│   │
│   ├── mcp/                   # MCP协议
│   │   └── server.py         # MCP服务器
│   │
│   ├── middleware/            # 中间件
│   ├── utils/                # 工具函数
│   ├── migrations/            # 数据迁移
│   │   └── migrate_all.py    # 完整迁移脚本
│   ├── sql/                   # SQL脚本
│   ├── data/                  # 数据目录
│   ├── old/                   # 旧版兼容模块
│   │   ├── api_call.py        # API调用封装
│   │   ├── phone/link.py      # 移动端连接
│   │   └── tool/tool.py       # 工具调用
│   ├── uploads/              # 上传文件目录
│   ├── chroma_db/             # ChromaDB持久化
│   └── video/                # 视频处理
│
├── front/                     # 前端页面
│   ├── src/                  # Vue源代码
│   └── package.json          # 前端依赖
│
├── .env.example              # 环境变量示例
└── README.md                 # 项目说明
```

## API 接口

### 知识库接口
```
GET  /api/knowledge/list              # 获取知识库列表
GET  /api/knowledge/<id>              # 获取知识库详情
POST /api/knowledge/create            # 创建知识库
PUT  /api/knowledge/update/<id>      # 更新知识库
POST /api/knowledge/upload            # 上传文件
GET  /api/knowledge/statistics        # 获取统计信息
```

### 聊天接口
```
POST /api/chat                        # 发送消息
POST /api/chat/image                  # 图片聊天
GET  /api/chat/history                # 获取聊天历史
POST /api/chat/history                # 保存聊天历史
DELETE /api/chat/history/<id>        # 删除聊天历史
```

### LangChain Agent接口
```
GET  /api/langchain/agents            # 获取Agent列表
GET  /api/langchain/tools             # 获取工具列表
POST /api/langchain/chat             # Agent对话
```

### 移动端接口
```
GET  /mobile/connect                  # 扫码连接页面
POST /api/qrcode/connect              # 建立连接
POST /api/qrcode/heartbeat            # 心跳检测
POST /api/phone/send                 # 发送文档
GET  /api/phone/messages             # 获取消息
```

## 内容创作类型

系统支持以下内容类型的智能生成：

| 类型 | 说明 | 关键词 |
|------|------|--------|
| 小红书 | 小红书风格文案 | 小红书、配图文案、图文 |
| 公众号 | 公众号推文 | 公众号、推文 |
| 朋友圈 | 朋友圈文案 | 朋友圈 |
| 短视频 | 抖音/快手文案 | 抖音文案、短视频文案 |
| 论文 | 学术论文格式 | 论文、摘要、关键词 |

## 技术栈

- **后端框架**: Flask 2.0+
- **AI框架**: LangChain, LangGraph
- **向量数据库**: ChromaDB
- **NLP模型**: BERT/RoBERTa (HuggingFace Transformers)
- **数据库**: SQLite
- **前端**: Vue.js

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
| **Embedding模型** | DashScope text-embedding-v1 | 阿里云通义千问Embedding API |
| **距离度量** | 余弦相似度 | 默认相似度计算方式 |

### 分块配置
| 配置项 | 值 | 说明 |
|--------|-----|------|
| **Chunk大小** | 800字符 | 每个文本块的最大字符数 |
| **Chunk重叠** | 100字符 | 相邻块之间的重叠字符数 |

### 并发配置
| 模式 | 说明 | 适用场景 |
|------|------|----------|
| **PersistentClient (当前)** | 本地文件存储，单进程访问 | 开发/小规模部署 |
| **Server模式** | 客户端-服务器模式，支持多客户端并发 | 生产环境/高并发 |

### 并发性能

| 指标 | 当前配置 | 说明 |
|------|----------|------|
| **理论最大并发** | ~50-100 用户/秒 | Flask单进程 + 本地SQLite |
| **实际建议并发** | 20-30 用户 | 考虑Embedding API延迟 |
| **主要瓶颈** | DashScope API QPS | 通常限制 5-10 QPS |

### 限制因素
1. **Flask单进程**：当前未配置多线程/多进程
2. **Embedding API**：DashScope text-embedding-v1 有QPS限制
3. **SQLite**：写入并发受限，本地文件锁

### 性能优化建议

```python
# 1. 启用多线程（app.py）
from werkzeug.serving import run_simple
run_simple('0.0.0.0', 5000, app, threaded=True)

# 2. 或使用Gunicorn多进程
# gunicorn -w 4 -b 0.0.0.0:5000 app:app

# 3. ChromaDB Server模式
chromadb --host localhost --port 8000 --workers 4
```

### 切换到Server模式

如需支持高并发，可启动ChromaDB服务器：

```bash
# 启动ChromaDB服务器（支持多worker）
chromadb --host localhost --port 8000 --workers 4

# 修改客户端连接（chroma_store.py）
from chromadb import HttpClient
self.client = HttpClient(host='localhost', port=8000)
```

### 集合说明
| 集合名 | 数据类型 | 说明 |
|--------|----------|------|
| documents | 知识库文档 | 知识库内容分块存储 |
| headers | 表格表头 | Excel表头向量 |
| table_data | 表格数据 | NLP表格处理结果 |

## 环境变量

创建 `.env` 文件，配置必要的环境变量：

```env
# 数据库配置
DATABASE_URL=sqlite:///ruoyi.db

# API密钥配置
DASHSCOPE_API_KEY=your_api_key_here
OPENAI_API_KEY=your_api_key_here

# 服务器配置
FLASK_HOST=0.0.0.0
FLASK_PORT=5000
```

## 许可证

MIT License

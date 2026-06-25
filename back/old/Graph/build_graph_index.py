"""
GraphRAG 知识库索引构建脚本
功能：
1. 检查并安装 graphrag 依赖
2. 从 MySQL 数据库读取 knowledge 表内容
3. 构建 GraphRAG 向量索引和知识图谱

用法：
    cd back/old/Graph
    python build_graph_index.py
"""

import os
import sys
import json
import subprocess
import shutil
from pathlib import Path
from datetime import datetime

# 项目根目录
GRAPH_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = GRAPH_DIR.parent.parent
ENV_FILE = PROJECT_ROOT / "old" / ".env"


def install_dependencies():
    """检查并安装 graphrag 及相关依赖"""
    print("=" * 60)
    print("[1/5] 检查并安装 graphrag 依赖...")
    print("=" * 60)

    required_packages = [
        "graphrag>=0.5.0",
        "lancedb>=0.15.0",
        "tiktoken>=0.7.0",
        "pyyaml>=6.0",
    ]

    # 使用清华镜像源加速下载
    PIP_MIRROR = "-i https://pypi.tuna.tsinghua.edu.cn/simple"

    for pkg in required_packages:
        pkg_name = pkg.split(">=")[0]
        try:
            __import__(pkg_name.replace("-", "_"))
            print(f"  ✓ {pkg_name} 已安装")
        except ImportError:
            print(f"  ⬇ 正在安装 {pkg} ...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", pkg, PIP_MIRROR])
            print(f"  ✓ {pkg} 安装完成")

    print("\n所有依赖已就绪！\n")


def load_env():
    """从 .env 文件加载环境变量"""
    if not ENV_FILE.exists():
        print(f"[ERROR] 找不到 .env 文件: {ENV_FILE}")
        sys.exit(1)

    with open(ENV_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                os.environ.setdefault(key.strip(), value.strip())

    print("[2/5] 环境变量加载完成")
    print(f"  DB_HOST={os.getenv('DB_HOST', 'localhost')}")
    print(f"  DB_NAME={os.getenv('DB_NAME', 'ruoyi')}")
    print()


def fetch_knowledge_from_db():
    """从 MySQL 数据库读取 knowledge 表内容"""
    print("=" * 60)
    print("[3/5] 从数据库读取知识库内容...")
    print("=" * 60)

    try:
        import pymysql
    except ImportError:
        print("  ⬇ 安装 pymysql ...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "pymysql", PIP_MIRROR])
        import pymysql

    db_host = os.getenv("DB_HOST", "localhost")
    db_port = int(os.getenv("DB_PORT", 3306))
    db_user = os.getenv("DB_USER", "root")
    db_password = os.getenv("DB_PASSWORD", "")
    db_name = os.getenv("DB_NAME", "ruoyi")

    conn = pymysql.connect(
        host=db_host,
        port=db_port,
        user=db_user,
        password=db_password,
        database=db_name,
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
    )

    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM knowledge ORDER BY created_at DESC")
            rows = cursor.fetchall()

            records = []
            for row in rows:
                tags = row.get("tags", "[]")
                if isinstance(tags, str):
                    try:
                        tags = json.loads(tags)
                    except:
                        tags = []

                attachments = row.get("attachments", "[]")
                if isinstance(attachments, str):
                    try:
                        attachments = json.loads(attachments)
                    except:
                        attachments = []

                records.append(
                    {
                        "id": row.get("id", ""),
                        "title": row.get("title", ""),
                        "type": row.get("type", "other"),
                        "tags": tags,
                        "description": row.get("description", ""),
                        "content": row.get("content", ""),
                        "attachments": attachments,
                        "created_by": row.get("created_by", ""),
                        "created_at": (
                            row.get("created_at").strftime("%Y-%m-%d %H:%M:%S")
                            if hasattr(row.get("created_at"), "strftime")
                            else str(row.get("created_at", ""))
                        ),
                    }
                )

            print(f"  ✓ 共读取 {len(records)} 条知识库记录\n")
            return records
    finally:
        conn.close()


def export_to_text_files(records):
    """将知识库内容导出为 GraphRAG 输入文本文件"""
    print("=" * 60)
    print("[4/5] 导出文本到 GraphRAG 输入目录...")
    print("=" * 60)

    input_dir = GRAPH_DIR / "input"
    if input_dir.exists():
        shutil.rmtree(input_dir)
    input_dir.mkdir(parents=True)

    type_labels = {"doc": "文档", "video": "视频", "image": "图片", "other": "其他"}

    for idx, item in enumerate(records):
        title = item["title"] or "未命名"
        content = item["content"] or ""
        description = item["description"] or ""
        tags = ", ".join(item.get("tags", [])) if item.get("tags") else ""
        item_type = type_labels.get(item["type"], item["type"])

        text_lines = [
            f"# {title}",
            f"",
            f"**类型**: {item_type}",
            f"**标签**: {tags}" if tags else "",
            f"**创建时间**: {item.get('created_at', '')}",
            f"**创建人**: {item.get('created_by', '')}",
            f"",
            f"## 描述",
            description if description else "（无描述）",
            f"",
            f"## 内容",
            content if content else "（无内容）",
            f"",
        ]

        # 去空行
        text_lines = [line for line in text_lines if line is not None]

        filename = f"knowledge_{item['id']}.txt"
        filepath = input_dir / filename
        with open(filepath, "w", encoding="utf-8") as f:
            f.write("\n".join(text_lines))

    print(f"  ✓ 已导出 {len(records)} 个文本文件到: {input_dir}\n")
    return input_dir


def create_settings_yaml():
    """创建 GraphRAG settings.yaml 配置文件"""
    print("=" * 60)
    print("[5/5] 配置 GraphRAG settings.yaml...")
    print("=" * 60)

    # 使用 DeepSeek API Key
    deepseek_api_key = os.getenv("DEEPSEEK_API_KEY", os.getenv("GRAPHRAG_API_KEY", ""))
    # Embedding 使用 DashScope（DeepSeek 不提供 Embedding API）
    dashscope_api_key = os.getenv("API_KEY", os.getenv("QWEN_API_KEY", ""))

    if not deepseek_api_key:
        print("[ERROR] 未找到 DEEPSEEK_API_KEY 或 GRAPHRAG_API_KEY，请检查 .env 文件")
        sys.exit(1)

    if not dashscope_api_key:
        print("[ERROR] 未找到 DashScope Embedding API Key (API_KEY 或 QWEN_API_KEY)，请检查 .env 文件")
        sys.exit(1)

    settings_content = f"""encoding_model: cl100k_base
skip_workflows: []

# LLM 配置 - 使用 DeepSeek API
llm:
  api_key: {deepseek_api_key}
  type: openai_chat
  model: deepseek-chat
  model_supports_json: true
  api_base: https://api.deepseek.com/v1
  # tokens per minute
  tokens_per_minute: 50000
  # requests per minute
  requests_per_minute: 30
  # concurrent requests
  concurrent_requests: 5
  # retry settings
  retry_strategy: native
  max_retries: 10
  # temperature
  temperature: 0.0
  # top_p
  top_p: 1.0
  # max tokens
  max_tokens: 4000

parallelization:
  stagger: 0.3
  # num_threads
  num_threads: 4

async_mode: threaded

# Embedding 配置 - 使用 DashScope API（DeepSeek 不提供 Embedding）
embeddings:
  async_mode: threaded
  vector_store:
    type: lancedb
    db_uri: '{(GRAPH_DIR / "lancedb").as_posix()}'
    container_name: default
    overwrite: true
  llm:
    api_key: {dashscope_api_key}
    type: openai_embedding
    model: text-embedding-v1
    api_base: https://dashscope.aliyuncs.com/compatible-mode/v1
    # tokens per minute
    tokens_per_minute: 50000
    # requests per minute
    requests_per_minute: 30
    # concurrent requests
    concurrent_requests: 5
    # retry settings
    retry_strategy: native
    max_retries: 10
    # batch size
    batch_size: 16
    # batch max tokens
    batch_max_tokens: 8191
    # target tokens
    target_tokens: 8000

chunks:
  size: 800
  overlap: 100
  group_by_columns:
    - id

input:
  type: file
  file_type: text
  base_dir: "{(GRAPH_DIR / 'input').as_posix()}"
  file_encoding: utf-8
  file_pattern: "**/*.txt"

storage:
  type: file
  base_dir: "{(GRAPH_DIR / 'output' / 'artifacts').as_posix()}"

reporting:
  type: file
  base_dir: "{(GRAPH_DIR / 'output' / 'reports').as_posix()}"

entity_extraction:
  prompt: "prompts/entity_extraction.txt"
  entity_types:
    - 组织
    - 人物
    - 地点
    - 事件
    - 概念
    - 产品
    - 技术
    - 文档
  max_gleanings: 1

summarize_descriptions:
  prompt: "prompts/summarize_descriptions.txt"
  max_length: 500

claim_extraction:
  prompt: "prompts/claim_extraction.txt"
  description: "任何相关的声明或信息"
  max_gleanings: 1

community_reports:
  prompt: "prompts/community_report.txt"
  max_length: 2000
  max_input_length: 8000

cluster_graph:
  max_cluster_size: 10

embed_graph:
  enabled: false

umap:
  enabled: false

snapshots:
  graphml: false
  raw_entities: false
  top_level_nodes: false

local_search:
  text_unit_prop: 0.5
  community_prop: 0.1
  conversation_history_max_turns: 5
  top_k_mapped_entities: 10
  top_k_relationships: 10
  llm_temperature: 0.0
  llm_top_p: 1.0
  llm_max_tokens: 4000
  llm_max_retries: 10

global_search:
  llm_temperature: 0.0
  llm_top_p: 1.0
  llm_max_tokens: 4000
  llm_max_retries: 10
"""

    settings_path = GRAPH_DIR / "settings.yaml"
    with open(settings_path, "w", encoding="utf-8") as f:
        f.write(settings_content)

    print(f"  ✓ 配置文件已保存: {settings_path}\n")
    return settings_path


def run_graphrag_index():
    """运行 GraphRAG 索引构建"""
    print("=" * 60)
    print("开始构建 GraphRAG 索引...")
    print("=" * 60)

    # 设置环境变量用于 GraphRAG（DeepSeek API）
    os.environ["GRAPHRAG_API_KEY"] = os.getenv("DEEPSEEK_API_KEY", os.getenv("GRAPHRAG_API_KEY", ""))

    # 确保 prompts 目录存在（GraphRAG 需要）
    prompts_dir = GRAPH_DIR / "prompts"
    prompts_dir.mkdir(exist_ok=True)

    try:
        print("  正在构建 GraphRAG 索引...")
        print("  这可能需要几分钟，请耐心等待...")
        
        cmd = [
            sys.executable, "-m", "graphrag",
            "index",
            "--root", str(GRAPH_DIR),
            "--verbose",
            "--cache"
        ]
        
        result = subprocess.run(
            cmd,
            cwd=str(GRAPH_DIR),
            capture_output=True,
            text=True
        )
        
        if result.stdout:
            print("\n构建输出:")
            for line in result.stdout.split('\n')[-20:]:
                print(f"  {line}")
        
        if result.stderr:
            print("\n警告/错误:")
            for line in result.stderr.split('\n')[-10:]:
                print(f"  {line}")
        
        if result.returncode == 0:
            print("\n✅ GraphRAG 索引构建完成！")
            print(f"  输出目录: {GRAPH_DIR / 'output'}")
            print(f"  向量数据库: {GRAPH_DIR / 'lancedb'}")
        else:
            print(f"\n❌ GraphRAG 索引构建失败 (返回码: {result.returncode})")
            print(f"  错误详情: {result.stderr}")
            
    except Exception as e:
        print(f"\n[ERROR] GraphRAG 索引构建失败: {e}")
        import traceback
        traceback.print_exc()


def main():
    print("\n" + "=" * 60)
    print(" GraphRAG 知识库索引构建工具")
    print("=" * 60 + "\n")

    # 1. 安装依赖
    install_dependencies()

    # 2. 加载环境变量
    load_env()

    # 3. 读取数据库
    records = fetch_knowledge_from_db()

    if not records:
        print("[WARNING] 数据库中没有知识库记录，跳过索引构建")
        return

    # 4. 导出文本
    export_to_text_files(records)

    # 5. 创建配置（如果不存在）
    settings_path = GRAPH_DIR / "settings.yaml"
    if not settings_path.exists():
        create_settings_yaml()
    else:
        print(f"[5/5] 配置文件已存在: {settings_path}")
        print("  ✓ 跳过配置文件创建\n")

    # 6. 构建索引
    run_graphrag_index()

    print("\n" + "=" * 60)
    print(" 全部完成！")
    print("=" * 60)
    print(f"""
使用说明：
  - 索引输出: {GRAPH_DIR / "output"}
  - 向量存储: {GRAPH_DIR / "lancedb"}
  - 查询方式: 使用 GraphRAG 的 local_search 或 global_search

快速查询示例：
  from graphrag.query.cli import run_local_search
  run_local_search(
      root_dir="{GRAPH_DIR}",
      query="你的查询问题",
  )
""")


if __name__ == "__main__":
    main()

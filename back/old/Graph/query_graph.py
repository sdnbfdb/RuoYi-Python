"""
GraphRAG 知识库查询脚本
功能：基于已构建的 GraphRAG 索引进行本地/全局搜索

用法：
    cd back/old/Graph
    python query_graph.py "你的查询问题"
    python query_graph.py "你的查询问题" --mode global
"""

import os
import sys
import argparse
from pathlib import Path

GRAPH_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = GRAPH_DIR.parent.parent
ENV_FILE = PROJECT_ROOT / "old" / ".env"


def load_env():
    """加载环境变量"""
    if ENV_FILE.exists():
        with open(ENV_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    os.environ.setdefault(key.strip(), value.strip())


def local_search(query: str):
    """本地搜索（基于实体和关系）"""
    print(f"\n[本地搜索] 查询: {query}\n")

    # 使用 DeepSeek API
    deepseek_api_key = os.getenv("DEEPSEEK_API_KEY", os.getenv("GRAPHRAG_API_KEY", ""))
    dashscope_api_key = os.getenv("API_KEY", os.getenv("QWEN_API_KEY", ""))
    os.environ["GRAPHRAG_API_KEY"] = deepseek_api_key

    try:
        from graphrag.query.structured_search.local_search.search import LocalSearch
        from graphrag.query.structured_search.local_search.community_context import (
            LocalSearchCommunityContext,
        )
        from graphrag.query.context_builder.entity_extraction import EntityVectorStoreKey
        from graphrag.query.indexer_adapters import (
            read_indexer_entities,
            read_indexer_relationships,
            read_indexer_reports,
            read_indexer_text_units,
        )
        from graphrag.query.llm.oai.chat_openai import ChatOpenAI
        from graphrag.query.llm.oai.embedding import OpenAIEmbedding
        from graphrag.query.question_gen.local_gen import LocalQuestionGen
        from graphrag.query.structured_search.local_search.search import LocalSearch
        from graphrag.vector_stores.lancedb import LanceDBVectorStore

        print("正在加载索引数据...")

        # 读取实体
        entity_df = read_indexer_entities(
            str(GRAPH_DIR / "output" / "artifacts" / "create_final_nodes.parquet"),
            str(GRAPH_DIR / "output" / "artifacts" / "create_final_entities.parquet"),
        )

        # 读取关系
        relationship_df = read_indexer_relationships(
            str(GRAPH_DIR / "output" / "artifacts" / "create_final_relationships.parquet")
        )

        # 读取社区报告
        report_df = read_indexer_reports(
            str(GRAPH_DIR / "output" / "artifacts" / "create_final_community_reports.parquet"),
            str(GRAPH_DIR / "output" / "artifacts" / "create_final_text_units.parquet"),
        )

        # 读取文本单元
        text_unit_df = read_indexer_text_units(
            str(GRAPH_DIR / "output" / "artifacts" / "create_final_text_units.parquet")
        )

        # 初始化 LLM（DeepSeek）
        llm = ChatOpenAI(
            api_key=deepseek_api_key,
            model="deepseek-chat",
            api_base="https://api.deepseek.com/v1",
            deployment_name="deepseek-chat",
            max_retries=10,
        )

        # 初始化 Embedding（DashScope）
        text_embedder = OpenAIEmbedding(
            api_key=dashscope_api_key,
            api_base="https://dashscope.aliyuncs.com/compatible-mode/v1",
            api_type="openai",
            model="text-embedding-v1",
            deployment_name="text-embedding-v1",
            max_retries=10,
        )

        # 向量存储
        description_embedding_store = LanceDBVectorStore(
            collection_name="entity_description_embeddings",
        )
        description_embedding_store.connect(
            db_uri=str(GRAPH_DIR / "lancedb"),
        )

        print("正在执行本地搜索...\n")

        search_engine = LocalSearch(
            llm=llm,
            context_builder=LocalSearchCommunityContext(
                entities=entity_df,
                relationships=relationship_df,
                reports=report_df,
                text_units=text_unit_df,
                entity_text_embeddings=description_embedding_store,
            ),
            token_encoder=None,
            llm_params={
                "max_tokens": 4000,
                "temperature": 0.0,
            },
            context_builder_params={
                "text_unit_prop": 0.5,
                "community_prop": 0.1,
                "conversation_history_max_turns": 5,
                "top_k_mapped_entities": 10,
                "top_k_relationships": 10,
                "include_entity_rank": True,
                "include_relationship_weight": True,
                "include_community_rank": False,
                "return_candidate_context": False,
                "embedding_vectorstore_key": EntityVectorStoreKey.ID,
                "max_tokens": 12000,
            },
            response_type="多个段落",
        )

        result = search_engine.search(query)
        print("=" * 60)
        print("搜索结果:")
        print("=" * 60)
        print(result.response)
        print("=" * 60)

    except Exception as e:
        print(f"[ERROR] 本地搜索失败: {e}")
        import traceback
        traceback.print_exc()


def global_search(query: str):
    """全局搜索（基于社区报告）"""
    print(f"\n[全局搜索] 查询: {query}\n")

    # 使用 DeepSeek API
    deepseek_api_key = os.getenv("DEEPSEEK_API_KEY", os.getenv("GRAPHRAG_API_KEY", ""))
    os.environ["GRAPHRAG_API_KEY"] = deepseek_api_key

    try:
        from graphrag.query.structured_search.global_search.search import GlobalSearch
        from graphrag.query.indexer_adapters import read_indexer_reports
        from graphrag.query.llm.oai.chat_openai import ChatOpenAI

        print("正在加载社区报告...")

        report_df = read_indexer_reports(
            str(GRAPH_DIR / "output" / "artifacts" / "create_final_community_reports.parquet"),
            str(GRAPH_DIR / "output" / "artifacts" / "create_final_text_units.parquet"),
        )

        # 初始化 LLM（DeepSeek）
        llm = ChatOpenAI(
            api_key=deepseek_api_key,
            model="deepseek-chat",
            api_base="https://api.deepseek.com/v1",
            deployment_name="deepseek-chat",
            max_retries=10,
        )

        print("正在执行全局搜索...\n")

        search_engine = GlobalSearch(
            llm=llm,
            token_encoder=None,
            reports=report_df,
            context_builder_params={
                "use_community_summary": False,
                "shuffle_data": True,
                "include_community_rank": True,
                "min_community_rank": 0,
                "community_rank_name": "rank",
                "include_community_weight": True,
                "community_weight_name": "occurrence weight",
                "normalize_community_weight": True,
                "max_tokens": 12000,
                "context_name": "Reports",
            },
            concurrent_coroutines=4,
            response_type="多个段落",
        )

        result = search_engine.search(query)
        print("=" * 60)
        print("搜索结果:")
        print("=" * 60)
        print(result.response)
        print("=" * 60)

    except Exception as e:
        print(f"[ERROR] 全局搜索失败: {e}")
        import traceback
        traceback.print_exc()


def main():
    parser = argparse.ArgumentParser(description="GraphRAG 知识库查询")
    parser.add_argument("query", help="查询问题")
    parser.add_argument(
        "--mode",
        choices=["local", "global"],
        default="local",
        help="搜索模式: local=本地搜索(实体级), global=全局搜索(社区报告级)",
    )
    args = parser.parse_args()

    load_env()

    # 检查索引是否存在
    artifacts_dir = GRAPH_DIR / "output" / "artifacts"
    if not artifacts_dir.exists():
        print(f"[ERROR] 找不到索引目录: {artifacts_dir}")
        print("请先运行: python build_graph_index.py")
        sys.exit(1)

    if args.mode == "local":
        local_search(args.query)
    else:
        global_search(args.query)


if __name__ == "__main__":
    main()

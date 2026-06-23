from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field
from typing import Optional
from ruoyi_langchain.tools.nlp_table_tool import (
    list_tables,
    retrieve_table_data,
    analyze_table_relationships,
    find_similar_headers,
    calculate_header_similarity,
    ListTablesInput,
    RetrieveTableDataInput,
    AnalyzeTableRelationshipsInput,
    FindSimilarHeadersInput,
    HeaderSimilarityInput
)


class TableQueryInput(BaseModel):
    action: str = Field(description="操作类型：list(列表), retrieve(检索), analyze(分析), similar_headers(相似表头), similarity(表头相似度)")
    query_header: Optional[str] = Field(default="", description="查询表头名称")
    top_n: int = Field(default=50, description="返回的最大记录数")
    directory_path: Optional[str] = Field(default="", description="包含表格文件的目录路径")
    header1: Optional[str] = Field(default="", description="第一个表头名称")
    header2: Optional[str] = Field(default="", description="第二个表头名称")


def query_table(action: str, query_header: str = "", top_n: int = 50, directory_path: str = "",
                header1: str = "", header2: str = "") -> str:
    if action == "list":
        return list_tables(directory_path=directory_path)
    elif action == "retrieve":
        return retrieve_table_data(query_header=query_header, top_n=top_n, directory_path=directory_path)
    elif action == "analyze":
        return analyze_table_relationships(directory_path=directory_path)
    elif action == "similar_headers":
        return find_similar_headers(query_header=query_header, top_k=5, directory_path=directory_path)
    elif action == "similarity":
        if not header1 or not header2:
            return "请提供两个表头名称"
        return calculate_header_similarity(header1=header1, header2=header2)
    else:
        return f"无效的操作类型: {action}。支持的类型：list, retrieve, analyze, similar_headers, similarity"


table_tool = StructuredTool.from_function(
    func=query_table,
    name="query_table",
    description="查询表格数据，支持列表、检索、分析、相似表头匹配等操作",
    args_schema=TableQueryInput
)
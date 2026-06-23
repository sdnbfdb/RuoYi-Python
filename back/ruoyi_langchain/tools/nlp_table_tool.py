from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field
from typing import Optional, List
from nlp.excel.header_embedding import HeaderEmbeddingEncoder
from nlp.excel.header_matrix import HeaderMatrixAnalyzer
from nlp.excel.table_retriever import TableDataRetriever
import os


class HeaderEncodeInput(BaseModel):
    directory_path: str = Field(description="包含Excel/CSV文件的目录路径")


def encode_table_headers(directory_path: str = "") -> str:
    if not directory_path:
        nlp_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        directory_path = os.path.join(nlp_dir, 'data')
    
    if not os.path.exists(directory_path):
        return f"目录不存在: {directory_path}"
    
    encoder = HeaderEmbeddingEncoder()
    results = encoder.encode_directory(directory_path)
    
    if not results:
        return f"目录中未找到支持的文件（.xlsx, .xls, .csv）: {directory_path}"
    
    result_lines = [f"已处理 {len(results)} 个文件:"]
    for filename, headers in results.items():
        header_names = list(headers.keys())
        result_lines.append(f"\n文件: {filename}")
        result_lines.append(f"  表头数量: {len(header_names)}")
        result_lines.append(f"  表头: {', '.join(header_names)}")
    
    result_lines.append(f"\n总独特表头数: {len(encoder.header_vectors)}")
    return '\n'.join(result_lines)


class HeaderSimilarityInput(BaseModel):
    header1: str = Field(description="第一个表头名称")
    header2: str = Field(description="第二个表头名称")


def calculate_header_similarity(header1: str, header2: str) -> str:
    encoder = HeaderEmbeddingEncoder()
    similarity = encoder.calculate_similarity(header1, header2)
    
    if similarity >= 0.8:
        level = "非常相似"
    elif similarity >= 0.6:
        level = "比较相似"
    elif similarity >= 0.4:
        level = "一般相似"
    else:
        level = "不太相似"
    
    return f"'{header1}' 与 '{header2}' 的相似度: {similarity:.4f} ({level})"


class FindSimilarHeadersInput(BaseModel):
    query_header: str = Field(description="查询表头名称")
    top_k: int = Field(default=5, description="返回的相似表头数量")
    directory_path: str = Field(default="", description="包含表格文件的目录路径（可选）")


def find_similar_headers(query_header: str, top_k: int = 5, directory_path: str = "") -> str:
    if not directory_path:
        nlp_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        directory_path = os.path.join(nlp_dir, 'data')
    
    encoder = HeaderEmbeddingEncoder()
    
    if os.path.exists(directory_path):
        encoder.encode_directory(directory_path)
    
    if not encoder.header_vectors:
        return "未找到任何表头数据，请先指定包含表格文件的目录"
    
    results = encoder.find_similar_headers(query_header, top_k=top_k)
    
    if not results:
        return f"未找到与 '{query_header}' 相似的表头"
    
    result_lines = [f"与 '{query_header}' 相似的表头（共{len(results)}个）:"]
    for i, res in enumerate(results, 1):
        if res['similarity'] >= 0.8:
            mark = "⭐"
        elif res['similarity'] >= 0.6:
            mark = "✓"
        else:
            mark = ""
        result_lines.append(f"{i}. {mark} {res['header']} (相似度: {res['similarity']:.4f}, 文件: {res['file']})")
    
    return '\n'.join(result_lines)


class AnalyzeTableRelationshipsInput(BaseModel):
    directory_path: str = Field(default="", description="包含表格文件的目录路径（可选）")


def analyze_table_relationships(directory_path: str = "") -> str:
    if not directory_path:
        nlp_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        directory_path = os.path.join(nlp_dir, 'data')
    
    if not os.path.exists(directory_path):
        return f"目录不存在: {directory_path}"
    
    analyzer = HeaderMatrixAnalyzer()
    success = analyzer.load_files_from_directory(directory_path)
    
    if not success:
        return f"目录中未找到支持的文件: {directory_path}"
    
    analyzer.build_association_matrix()
    
    result_lines = [f"表头关联分析结果:"]
    result_lines.append(f"  加载文件数: {len(analyzer.file_list)}")
    result_lines.append(f"  不同表头数: {len(analyzer.all_headers)}")
    
    common_headers = analyzer.find_common_headers(min_files=2)
    if common_headers:
        result_lines.append(f"\n  公共表头（出现在多个文件中）:")
        for header, count in common_headers[:5]:
            result_lines.append(f"    - {header}: 出现在 {count} 个文件中")
    
    relationships = analyzer.find_file_relationships()
    if relationships:
        result_lines.append(f"\n  文件间关系（共享表头）:")
        for rel in relationships[:5]:
            result_lines.append(f"    - {rel['file1']} ↔ {rel['file2']}")
            result_lines.append(f"      共享表头: {rel['shared_headers']} 个, 相似度: {rel['similarity']:.2%}")
    
    return '\n'.join(result_lines)


class RetrieveTableDataInput(BaseModel):
    query_header: str = Field(default="", description="查询表头名称（用于匹配相关列）")
    top_n: int = Field(default=50, description="返回的最大记录数")
    directory_path: str = Field(default="", description="包含表格文件的目录路径（可选）")


def retrieve_table_data(query_header: str = "", top_n: int = 50, directory_path: str = "") -> str:
    if not directory_path:
        nlp_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        directory_path = os.path.join(nlp_dir, 'data')
    
    if not os.path.exists(directory_path):
        return f"目录不存在: {directory_path}"
    
    retriever = TableDataRetriever(data_dir=directory_path)
    retriever.load_all()
    
    if not retriever.tables:
        return f"目录中未找到CSV文件: {directory_path}"
    
    if query_header:
        encoder = HeaderEmbeddingEncoder()
        encoder.encode_directory(directory_path)
        matched_headers = encoder.find_similar_headers(query_header, top_k=10)
    else:
        matched_headers = []
    
    result = retriever.retrieve(matched_headers=matched_headers, top_n=top_n)
    
    result_lines = [f"表格检索结果:"]
    result_lines.append(f"  加载文件: {', '.join(result['files_loaded'])}")
    result_lines.append(f"  总记录数: {result['total']}")
    result_lines.append(f"  返回记录: {len(result['records'])}")
    result_lines.append(f"  列: {', '.join(result['headers'])}")
    
    if result['join_info']:
        result_lines.append(f"  连接信息: {result['join_info']}")
    
    if result['records']:
        result_lines.append(f"\n  示例数据:")
        for i, row in enumerate(result['records'][:5]):
            row_str = ", ".join(f"{k}: {v}" for k, v in row.items())
            result_lines.append(f"    {i+1}. {row_str}")
    
    return '\n'.join(result_lines)


class ListTablesInput(BaseModel):
    directory_path: str = Field(default="", description="包含表格文件的目录路径（可选）")


def list_tables(directory_path: str = "") -> str:
    if not directory_path:
        nlp_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        directory_path = os.path.join(nlp_dir, 'data')
    
    if not os.path.exists(directory_path):
        return f"目录不存在: {directory_path}"
    
    retriever = TableDataRetriever(data_dir=directory_path)
    retriever.load_all()
    
    if not retriever.tables:
        return f"目录中未找到CSV文件: {directory_path}"
    
    result_lines = [f"已加载的表格数据（共{len(retriever.tables)}个）:"]
    for filename, rows in retriever.tables.items():
        headers = retriever.table_headers[filename]
        result_lines.append(f"\n  文件: {filename}")
        result_lines.append(f"    行数: {len(rows)}")
        result_lines.append(f"    表头: {', '.join(headers)}")
    
    return '\n'.join(result_lines)


header_encode_tool = StructuredTool.from_function(
    func=encode_table_headers,
    name="encode_table_headers",
    description="对目录中的所有Excel/CSV文件进行表头向量化编码",
    args_schema=HeaderEncodeInput
)

header_similarity_tool = StructuredTool.from_function(
    func=calculate_header_similarity,
    name="calculate_header_similarity",
    description="计算两个表头之间的相似度",
    args_schema=HeaderSimilarityInput
)

find_similar_headers_tool = StructuredTool.from_function(
    func=find_similar_headers,
    name="find_similar_headers",
    description="查找与查询表头相似的表头",
    args_schema=FindSimilarHeadersInput
)

analyze_table_relationships_tool = StructuredTool.from_function(
    func=analyze_table_relationships,
    name="analyze_table_relationships",
    description="分析多个表格文件之间的表头关联关系",
    args_schema=AnalyzeTableRelationshipsInput
)

retrieve_table_data_tool = StructuredTool.from_function(
    func=retrieve_table_data,
    name="retrieve_table_data",
    description="根据表头匹配检索表格数据，支持多表连接",
    args_schema=RetrieveTableDataInput
)

list_tables_tool = StructuredTool.from_function(
    func=list_tables,
    name="list_tables",
    description="列出目录中所有CSV表格文件及其表头信息",
    args_schema=ListTablesInput
)
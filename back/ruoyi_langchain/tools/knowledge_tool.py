from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field
from typing import Optional, List
from knowledge.knowledge import load_knowledge_data, get_knowledge_by_id, get_statistics
from vector_store.chroma_store import CharmDBStore


class KnowledgeQueryInput(BaseModel):
    action: str = Field(description="操作类型：list(列表), detail(详情), search(搜索), extract(提取), stats(统计), vector_search(向量搜索)")
    search: Optional[str] = Field(default="", description="搜索关键词")
    knowledge_id: Optional[str] = Field(default="", description="知识库ID")
    top_k: int = Field(default=5, description="向量搜索返回结果数量")


def query_knowledge_base(action: str, search: str = "", knowledge_id: str = "", top_k: int = 5) -> str:
    if action == "list":
        knowledge_data = load_knowledge_data()
        if not knowledge_data:
            return "知识库为空"
        
        result_lines = [f"知识库共有 {len(knowledge_data)} 条记录："]
        for i, item in enumerate(knowledge_data[:10], 1):
            result_lines.append(f"\n{i}. 标题: {item.get('title', '无标题')}")
            result_lines.append(f"   ID: {item.get('id', '')}")
            result_lines.append(f"   类型: {item.get('type', 'other')}")
            result_lines.append(f"   创建时间: {item.get('created_at', '')}")
        
        if len(knowledge_data) > 10:
            result_lines.append(f"\n... 还有 {len(knowledge_data) - 10} 条记录")
        
        return '\n'.join(result_lines)
    
    elif action == "search":
        if not search:
            return "请提供搜索关键词"
        
        knowledge_data = load_knowledge_data()
        results = [item for item in knowledge_data 
                  if search.lower() in item.get('title', '').lower() 
                  or search.lower() in item.get('content', '').lower()
                  or search.lower() in item.get('description', '').lower()
                  or any(search.lower() in tag.lower() for tag in item.get('tags', []))]
        
        if not results:
            return f"未找到与 '{search}' 相关的知识库记录"
        
        result_lines = [f"搜索 '{search}' 共找到 {len(results)} 条记录："]
        for i, item in enumerate(results[:10], 1):
            preview = item.get('content', '')[:100] + '...' if len(item.get('content', '')) > 100 else item.get('content', '')
            result_lines.append(f"\n{i}. 标题: {item.get('title', '无标题')}")
            result_lines.append(f"   ID: {item.get('id', '')}")
            result_lines.append(f"   类型: {item.get('type', 'other')}")
            result_lines.append(f"   预览: {preview}")
        
        if len(results) > 10:
            result_lines.append(f"\n... 还有 {len(results) - 10} 条记录")
        
        return '\n'.join(result_lines)
    
    elif action == "detail":
        if not knowledge_id:
            return "请提供知识库ID"
        
        item = get_knowledge_by_id(knowledge_id)
        if not item:
            return f"未找到ID为 '{knowledge_id}' 的知识库条目"
        
        result_lines = []
        result_lines.append(f"标题: {item.get('title', '')}")
        result_lines.append(f"ID: {item.get('id', '')}")
        result_lines.append(f"类型: {item.get('type', 'other')}")
        result_lines.append(f"创建时间: {item.get('created_at', '')}")
        result_lines.append(f"更新时间: {item.get('updated_at', '')}")
        result_lines.append(f"创建者: {item.get('created_by', '')}")
        
        if item.get('tags'):
            result_lines.append(f"标签: {', '.join(item.get('tags'))}")
        
        if item.get('description'):
            result_lines.append(f"\n描述: {item.get('description')}")
        
        if item.get('content'):
            content_preview = item.get('content')[:500] + '...' if len(item.get('content')) > 500 else item.get('content')
            result_lines.append(f"\n内容预览:\n{content_preview}")
        
        if item.get('attachments'):
            result_lines.append(f"\n附件（{len(item.get('attachments'))}个）:")
            for att in item.get('attachments'):
                result_lines.append(f"  - {att.get('filename', '')} ({att.get('size_display', '')})")
        
        if item.get('qa_records'):
            result_lines.append(f"\n问答记录（{len(item.get('qa_records'))}条）:")
            for qa in item.get('qa_records')[:3]:
                result_lines.append(f"  Q: {qa.get('question', '')}")
                result_lines.append(f"  A: {qa.get('answer', '')[:100]}...")
        
        return '\n'.join(result_lines)
    
    elif action == "extract":
        if not knowledge_id:
            return "请提供知识库ID"
        
        item = get_knowledge_by_id(knowledge_id)
        if not item:
            return f"未找到ID为 '{knowledge_id}' 的知识库条目"
        
        content = item.get('content', '')
        if content:
            return f"提取的内容（长度：{len(content)}字符）:\n{content}"
        return "该条目没有内容"
    
    elif action == "stats":
        stats_result = get_statistics()
        if not stats_result.is_json:
            return "获取统计信息失败"
        
        import json
        try:
            stats = json.loads(stats_result.get_data(as_text=True))
        except:
            return "解析统计信息失败"
        
        data = stats.get('data', {})
        
        result_lines = [f"知识库统计信息:"]
        result_lines.append(f"  总记录数: {data.get('total', 0)}")
        
        if data.get('by_type'):
            result_lines.append(f"\n  类型分布:")
            for type_name, count in data['by_type'].items():
                result_lines.append(f"    - {type_name}: {count} 条")
        
        if data.get('by_tag'):
            result_lines.append(f"\n  标签分布（前10个）:")
            for tag, count in list(data['by_tag'].items())[:10]:
                result_lines.append(f"    - {tag}: {count} 次")
        
        result_lines.append(f"\n  总附件数: {data.get('total_attachments', 0)}")
        result_lines.append(f"  总大小: {data.get('total_size_display', '0 KB')}")
        
        return '\n'.join(result_lines)
    
    elif action == "vector_search":
        if not search:
            return "请提供搜索关键词"
        
        try:
            chroma_store = CharmDBStore(persist_directory=os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'chroma_db'))
            results = chroma_store.similarity_search(
                collection_name='knowledge_base',
                query=search,
                k=top_k
            )
            
            if not results:
                return f"向量搜索未找到与 '{search}' 相关的记录"
            
            result_lines = [f"向量搜索 '{search}' 找到 {len(results)} 条记录："]
            for i, doc in enumerate(results, 1):
                metadata = doc.metadata
                result_lines.append(f"\n{i}. 标题: {metadata.get('title', '无标题')}")
                result_lines.append(f"   章节: {metadata.get('section_title', '')}")
                result_lines.append(f"   相似度: {doc.score:.4f}")
                result_lines.append(f"   预览: {metadata.get('content_preview', '')}")
            
            return '\n'.join(result_lines)
        except Exception as e:
            return f"向量搜索失败: {str(e)}"
    
    else:
        return f"无效的操作类型: {action}。支持的类型：list, detail, search, extract, stats, vector_search"


knowledge_tool = StructuredTool.from_function(
    func=query_knowledge_base,
    name="query_knowledge",
    description="查询知识库，支持列表、搜索、详情、提取、统计和向量搜索操作",
    args_schema=KnowledgeQueryInput
)
from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field
from typing import Optional, List
import sys
import os

# 确保可以导入后端模块
_back_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _back_dir not in sys.path:
    sys.path.insert(0, _back_dir)

try:
    from knowledge.knowledge import load_knowledge_data, get_knowledge_by_id, get_statistics
except ImportError:
    load_knowledge_data = None
    get_knowledge_by_id = None
    get_statistics = None


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
        try:
            if load_knowledge_data is None:
                return "知识库模块未加载"
            from knowledge.knowledge import load_knowledge_from_db
            data_list = load_knowledge_from_db()
            total = len(data_list)
            by_type = {}
            by_tag = {}
            total_attachments = 0
            total_size = 0
            for item in data_list:
                t = item.get('type', 'other')
                by_type[t] = by_type.get(t, 0) + 1
                for tag in item.get('tags', []):
                    by_tag[tag] = by_tag.get(tag, 0) + 1
                total_attachments += item.get('attachment_count', 0)
                total_size += item.get('total_size', 0)
            size_display = f'{total_size/1024:.1f} KB' if total_size < 1024*1024 else f'{total_size/(1024*1024):.2f} MB'

            result_lines = ["知识库统计信息:"]
            result_lines.append(f"  总记录数: {total}")
            if by_type:
                result_lines.append("\n  类型分布:")
                for type_name, count in by_type.items():
                    result_lines.append(f"    - {type_name}: {count} 条")
            if by_tag:
                result_lines.append("\n  标签分布（前10个）:")
                for tag, count in list(by_tag.items())[:10]:
                    result_lines.append(f"    - {tag}: {count} 次")
            result_lines.append(f"\n  总附件数: {total_attachments}")
            result_lines.append(f"  总大小: {size_display}")
            return '\n'.join(result_lines)
        except Exception as e:
            return f"获取统计信息失败: {str(e)}"
    
    elif action == "vector_search":
        if not search:
            return "请提供搜索关键词"
        # 向量搜索降级为关键词搜索
        try:
            if load_knowledge_data is None:
                return "知识库模块未加载"
            knowledge_data = load_knowledge_data()
            results = [item for item in knowledge_data
                       if search.lower() in item.get('title', '').lower()
                       or search.lower() in item.get('content', '').lower()]
            if not results:
                return f"向量搜索未找到与 '{search}' 相关的记录"
            result_lines = [f"向量搜索(关键词降级) '{search}' 找到 {len(results)} 条记录："]
            for i, item in enumerate(results[:top_k], 1):
                preview = item.get('content', '')[:100]
                result_lines.append(f"\n{i}. 标题: {item.get('title', '无标题')}")
                result_lines.append(f"   预览: {preview}")
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
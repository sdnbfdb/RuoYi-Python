from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field
import sys
import os

# 确保可以导入后端模块
_back_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _back_dir not in sys.path:
    sys.path.insert(0, _back_dir)


class WebSearchInput(BaseModel):
    query: str = Field(description="搜索查询词")


def web_search(query: str) -> str:
    """调用博查搜索 API 进行真实联网搜索"""
    try:
        from old.tool.tool import call_search_api
        result = call_search_api(query)
        if not result.get('success'):
            return f"搜索失败: {result.get('message', '未知错误')}"

        data = result.get('data', {})
        web_pages = data.get('webPages', {}).get('value', [])
        if not web_pages:
            return f"未找到与 '{query}' 相关的搜索结果"

        lines = [f"联网搜索 '{query}' 的结果：\n"]
        for i, page in enumerate(web_pages[:8], 1):
            lines.append(f"{i}. {page.get('name', '')}")
            lines.append(f"   链接: {page.get('url', '')}")
            snippet = page.get('snippet', '')
            if snippet:
                lines.append(f"   摘要: {snippet[:150]}")
            lines.append("")
        return "\n".join(lines)
    except Exception as e:
        return f"联网搜索失败: {str(e)}"


web_search_tool = StructuredTool.from_function(
    func=web_search,
    name="web_search",
    description="联网搜索，调用博查API获取实时网页信息",
    args_schema=WebSearchInput
)

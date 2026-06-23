from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

class WebSearchInput(BaseModel):
    query: str = Field(description="搜索查询词")

def web_search(query: str) -> str:
    return f"联网搜索结果: {query}"

web_search_tool = StructuredTool.from_function(
    func=web_search,
    name="web_search",
    description="联网搜索，获取实时信息",
    args_schema=WebSearchInput
)

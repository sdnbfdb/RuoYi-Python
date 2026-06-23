from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field
from typing import Optional

class OrganizationQueryInput(BaseModel):
    action: str = Field(description="操作类型：search(搜索), detail(详情)")
    search: Optional[str] = Field(default="", description="搜索关键词")

def query_organization(action: str, search: str = "") -> str:
    return f"组织架构查询: {action} - {search}"

organization_tool = StructuredTool.from_function(
    func=query_organization,
    name="query_organization",
    description="查询煤矿组织架构信息，包括部门、人员、岗位等",
    args_schema=OrganizationQueryInput
)

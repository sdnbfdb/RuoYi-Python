from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field
from typing import Optional
import sys
import os

# 确保可以导入后端模块
_back_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _back_dir not in sys.path:
    sys.path.insert(0, _back_dir)


class OrganizationQueryInput(BaseModel):
    action: str = Field(description="操作类型：list(列表), get(按名称查询), search(搜索)")
    search: Optional[str] = Field(default="", description="搜索关键词或人员/部门名称")
    parent_id: Optional[str] = Field(default="", description="父节点ID（用于查询子部门）")


def query_organization(action: str, search: str = "", parent_id: str = "") -> str:
    """调用真实组织架构数据查询煤矿部门、人员信息"""
    try:
        from old.tool.tool import call_organization
        result = call_organization(action, name=search, parent=parent_id)

        if not result.get('success'):
            return f"组织架构查询失败: {result.get('message', '未知错误')}"

        data = result.get('data', {})

        if action == 'list':
            items = data if isinstance(data, list) else data.get('items', [])
            if not items:
                return "组织架构列表为空"
            lines = [f"组织架构列表（共 {len(items)} 条）：\n"]
            for i, item in enumerate(items[:20], 1):
                name = item.get('name', item.get('部门', item.get('姓名', '')))
                dept = item.get('department', item.get('部门', ''))
                position = item.get('position', item.get('职务', ''))
                info = name
                if dept:
                    info += f" - {dept}"
                if position:
                    info += f" ({position})"
                lines.append(f"{i}. {info}")
            if len(items) > 20:
                lines.append(f"\n... 还有 {len(items) - 20} 条")
            return "\n".join(lines)

        elif action in ('get', 'get_by_name', 'search'):
            items = data if isinstance(data, list) else ([data] if data else [])
            if not items:
                return f"未找到与 '{search}' 相关的组织架构信息"
            lines = [f"查询 '{search}' 的结果（共 {len(items)} 条）：\n"]
            for item in items[:15]:
                for k, v in item.items():
                    if v and str(v).strip():
                        lines.append(f"  {k}: {v}")
                lines.append("")
            return "\n".join(lines)

        else:
            return str(data)

    except Exception as e:
        return f"组织架构查询失败: {str(e)}"


organization_tool = StructuredTool.from_function(
    func=query_organization,
    name="query_organization",
    description="查询煤矿组织架构信息，包括部门、人员、岗位、联系方式等，支持列表和按名称搜索",
    args_schema=OrganizationQueryInput
)

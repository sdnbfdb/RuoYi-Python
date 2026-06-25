from mcp.server import Server
from mcp.types import Tool, TextContent
from typing import Any
import asyncio

app = Server("ruoyi-mcp-server")

@app.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="query_knowledge",
            description="查询煤矿知识库，获取煤矿安全、技术、管理等方面的资料",
            inputSchema={
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["list", "detail", "search", "extract"],
                        "description": "操作类型"
                    },
                    "search": {
                        "type": "string",
                        "description": "搜索关键词"
                    },
                    "knowledge_id": {
                        "type": "string",
                        "description": "知识库ID"
                    }
                },
                "required": ["action"]
            }
        ),
        Tool(
            name="query_organization",
            description="查询煤矿组织架构信息，包括部门层级、负责人、上下级关系等",
            inputSchema={
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["get", "list"],
                        "description": "操作类型"
                    },
                    "name": {
                        "type": "string",
                        "description": "部门名称或ID"
                    }
                },
                "required": ["action"]
            }
        ),
        Tool(
            name="web_search",
            description="使用博查搜索API进行联网搜索，获取最新的煤矿行业新闻、政策、技术等信息",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "搜索关键词"
                    }
                },
                "required": ["query"]
            }
        )
    ]

@app.call_tool()
async def call_tool(name: str, arguments: Any) -> list[TextContent]:
    from knowledge.knowledge import load_knowledge_data
    from old.tool.tool import call_search_api
    from layer.user.organization import OrganizationManager
    
    if name == "query_knowledge":
        action = arguments.get("action")
        search = arguments.get("search", "")
        knowledge_id = arguments.get("knowledge_id", "")
        
        knowledge_data = load_knowledge_data()
        
        if action == "list":
            result = f"知识库共有 {len(knowledge_data)} 条记录"
        elif action == "search":
            results = [item for item in knowledge_data 
                      if search.lower() in item.get('title', '').lower()]
            result = f"搜索到 {len(results)} 条相关记录"
        elif action == "detail":
            item = next((item for item in knowledge_data 
                        if str(item.get('id')) == knowledge_id), None)
            if item:
                result = f"标题：{item.get('title')}\n内容：{item.get('content')}"
            else:
                result = "未找到该知识库条目"
        else:
            result = "无效的操作类型"
        
        return [TextContent(type="text", text=result)]
    
    elif name == "web_search":
        query = arguments.get("query")
        search_result = call_search_api(query)
        
        if search_result.get('success'):
            data = search_result.get('data', {})
            web_pages = data.get('webPages', {})
            results = web_pages.get('value', [])
            
            lines = [f'🔍 「{query}」的博查搜索结果', '']
            for idx, item in enumerate(results[:10], 1):
                title = item.get('name', '无标题')
                snippet = item.get('snippet', '')
                lines.append(f'{idx}. **{title}**')
                if snippet:
                    lines.append(f'   {snippet}')
            
            result = '\n'.join(lines)
        else:
            result = f'搜索失败：{search_result.get("message", "未知错误")}'
        
        return [TextContent(type="text", text=result)]
    
    elif name == "query_organization":
        action = arguments.get("action")
        name = arguments.get("name", "")
        
        org_manager = OrganizationManager()
        
        if action == "list":
            tree = org_manager.build_org_tree()
            
            def count_depts(node):
                cnt = 1
                for c in node.get('children', []):
                    cnt += count_depts(c)
                return cnt
            
            total = count_depts(tree)
            result = f"组织架构共有 {total} 个部门"
        elif action == "get":
            org = org_manager.get_org_by_name(name)
            if org:
                result = f"部门：{org.get('name')}\n负责人：{org.get('leader')}"
            else:
                result = "未找到该部门"
        else:
            result = "无效的操作类型"
        
        return [TextContent(type="text", text=result)]
    
    return [TextContent(type="text", text="未知工具")]

async def main():
    from mcp.server.stdio import stdio_server
    
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )

if __name__ == "__main__":
    asyncio.run(main())

"""
知识库 Agent - 负责内部知识检索
"""

from ruoyi_langchain.agents.base.base_agent import BaseAgent
from typing import List, Dict


class KnowledgeAgent(BaseAgent):
    """知识库助手 - 负责内部知识检索、文档查询"""
    
    def __init__(self, tools: List = None, model: str = "qwen-turbo", llm_config: Dict = None):
        system_prompt = """你是一个专业的知识库助手，擅长：
1. 知识检索 - 从内部知识库中查找相关信息
2. 文档总结 - 提炼文档核心内容
3. 关联分析 - 发现知识间的联系
4. 问答解答 - 基于知识库回答问题

你的风格：准确、全面、引用来源"""
        
        super().__init__(
            name="knowledge",
            role="knowledge_specialist",
            description="内部知识库检索和文档分析",
            model=model,
            system_prompt=system_prompt,
            tools=tools,
            llm_config=llm_config
        )
    
    def search_knowledge(self, query: str) -> str:
        """搜索知识库"""
        if not self.tools:
            return f"知识库搜索: {query}"
        
        for tool in self.tools:
            if tool.name == "query_knowledge":
                return tool.func(action="search", search=query)
        
        return f"知识库搜索结果: {query}"
    
    def get_knowledge_detail(self, knowledge_id: str) -> str:
        """获取知识详情"""
        for tool in self.tools:
            if tool.name == "query_knowledge":
                return tool.func(action="detail", knowledge_id=knowledge_id)
        return f"知识详情 ID: {knowledge_id}"
    
    def vector_search(self, query: str, top_k: int = 5) -> str:
        """向量检索"""
        for tool in self.tools:
            if tool.name == "query_knowledge":
                return tool.func(action="vector_search", search=query, top_k=top_k)
        return f"向量搜索: {query}"
    
    def get_statistics(self) -> Dict:
        """获取统计信息"""
        for tool in self.tools:
            if tool.name == "query_knowledge":
                result = tool.func(action="stats")
                return {"success": True, "data": result}
        return {"success": False, "message": "统计工具不可用"}

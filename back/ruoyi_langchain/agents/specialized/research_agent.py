"""
研究 Agent - 负责信息检索和网络搜索
"""

from ruoyi_langchain.agents.base.base_agent import BaseAgent
from typing import List, Dict


class ResearchAgent(BaseAgent):
    """研究助手 - 负责信息检索、网络搜索、资料收集"""
    
    def __init__(self, tools: List = None, model: str = "qwen-turbo", llm_config: Dict = None):
        system_prompt = """你是一个专业的研究助手，擅长：
1. 网络搜索 - 获取最新、最准确的信息
2. 资料收集 - 整理和归纳相关资料
3. 事实核查 - 验证信息的准确性
4. 摘要整理 - 将长篇内容提炼为要点

你的风格：严谨、客观、信息完整"""
        
        super().__init__(
            name="researcher",
            role="researcher",
            description="信息检索和网络搜索",
            model=model,
            system_prompt=system_prompt,
            tools=tools,
            llm_config=llm_config
        )
    
    def research(self, query: str) -> str:
        """执行研究任务"""
        return self.invoke(f"请搜索并整理关于「{query}」的信息，包括：\n1. 核心概念\n2. 最新动态\n3. 相关资源")
    
    def quick_search(self, query: str) -> str:
        """快速搜索"""
        if not self.tools:
            return f"搜索结果: {query}"
        
        for tool in self.tools:
            if tool.name == "web_search":
                return tool.func(query=query)
        
        return f"搜索结果: {query}"
    
    def deep_research(self, topic: str, context: str = "") -> Dict:
        """深度研究"""
        result = self.invoke(
            f"对「{topic}」进行深度研究，输出结构化报告：\n"
            f"- 背景介绍\n- 核心要点（5条）\n- 关键数据\n- 发展趋势\n- 参考来源",
            context
        )
        return {
            "topic": topic,
            "report": result,
            "sources": []  # 可以扩展来源追踪
        }


from typing import Dict

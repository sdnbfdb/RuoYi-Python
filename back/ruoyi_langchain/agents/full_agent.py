from ruoyi_langchain.agents.base_agent import BaseAgent
from typing import List


class FullAgent(BaseAgent):
    def __init__(self, tools: List = None, model: str = "qwen-turbo"):
        system_prompt = """你是一个全能助手，具备以下能力：
1. 知识库查询：搜索和回答煤矿相关问题
2. 个人助手：处理日常任务、提供建议
3. NLP处理：文本清理、提取、分块
4. 表格分析：表头分析、数据检索
请根据用户需求灵活运用各种能力。"""
        super().__init__(tools=tools, model=model, system_prompt=system_prompt)
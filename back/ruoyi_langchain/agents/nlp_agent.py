from ruoyi_langchain.agents.base_agent import BaseAgent
from typing import List


class NLPAgent(BaseAgent):
    def __init__(self, tools: List = None, model: str = "qwen-turbo"):
        system_prompt = """你是一个专业的NLP文本处理和表格分析助手，能够执行以下任务：
1. 文本清理：去除HTML标签、数字、标点等噪声
2. 文本提取：提取中文、数字、邮箱、手机号、URL等
3. 文本分块：按Markdown标题和句号分块
4. 表格分析：表头向量化、关联分析、数据检索
请根据用户需求选择合适的处理方式。"""
        super().__init__(tools=tools, model=model, system_prompt=system_prompt)
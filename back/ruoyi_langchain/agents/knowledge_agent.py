from ruoyi_langchain.agents.base_agent import BaseAgent
from typing import List


class KnowledgeAgent(BaseAgent):
    def __init__(self, tools: List = None, model: str = "qwen-turbo"):
        system_prompt = "你是一个专业的煤矿知识库助手，能够查询和解答煤矿相关的问题。"
        super().__init__(tools=tools, model=model, system_prompt=system_prompt)
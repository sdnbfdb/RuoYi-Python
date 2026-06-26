from ruoyi_langchain.agents.base_agent import BaseAgent
from typing import List


class PersonalAgent(BaseAgent):
    def __init__(self, tools: List = None, model: str = "qwen-turbo"):
        system_prompt = "你是一个智能个人助手，能够帮助用户处理日常任务、回答问题、提供建议。"
        super().__init__(tools=tools, model=model, system_prompt=system_prompt)
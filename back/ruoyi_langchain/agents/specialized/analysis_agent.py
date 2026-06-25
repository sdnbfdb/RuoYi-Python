"""
分析 Agent - 负责数据分析和 NLP 处理
"""

from ruoyi_langchain.agents.base.base_agent import BaseAgent
from typing import List, Dict


class AnalysisAgent(BaseAgent):
    """分析助手 - 负责数据分析和 NLP 处理"""
    
    def __init__(self, tools: List = None, model: str = "qwen-turbo", llm_config: Dict = None):
        system_prompt = """你是一个专业的分析助手，擅长：
1. 文本分析 - 关键词提取、情感分析、主题分类
2. 表格处理 - 数据清洗、统计分析、关联挖掘
3. 结构化 - 将非结构化文本转为结构化数据
4. 对比分析 - 多维度对比和评估

你的风格：逻辑清晰、数据驱动、结论明确"""
        
        super().__init__(
            name="analyst",
            role="data_analyst",
            description="数据分析和自然语言处理",
            model=model,
            system_prompt=system_prompt,
            tools=tools,
            llm_config=llm_config
        )
    
    def analyze_text(self, text: str, analysis_type: str = "summary") -> str:
        """文本分析"""
        analysis_prompts = {
            "summary": f"请总结以下文本的核心要点（不超过5点）：\n{text[:2000]}",
            "keywords": f"请提取以下文本的关键词（10个）：\n{text[:2000]}",
            "sentiment": f"请分析以下文本的情感倾向：\n{text[:2000]}",
            "structure": f"请分析以下文本的结构和逻辑：\n{text[:2000]}"
        }
        
        prompt = analysis_prompts.get(analysis_type, analysis_prompts["summary"])
        return self.invoke(prompt)
    
    def analyze_table(self, query: str, directory: str = None) -> str:
        """表格分析"""
        for tool in self.tools:
            if tool.name == "analyze_table_relationships":
                return tool.func(directory_path=directory) if directory else "需要指定目录"
            if tool.name == "retrieve_table_data":
                return tool.func(query_header=query, top_n=10, directory_path=directory) if directory else "需要指定目录"
        return f"表格分析: {query}"
    
    def clean_text(self, text: str, options: Dict = None) -> str:
        """文本清洗"""
        options = options or {"remove_html": True, "remove_num": False, "remove_punc": False}
        
        for tool in self.tools:
            if tool.name == "clean_text":
                return tool.func(
                    text=text,
                    remove_html=options.get("remove_html", True),
                    remove_num=options.get("remove_num", False),
                    remove_punc=options.get("remove_punc", False)
                )
        
        return text  # 回退：返回原文本
    
    def extract_entities(self, text: str) -> str:
        """实体提取"""
        for tool in self.tools:
            if tool.name == "extract_text":
                # 提取所有类型的实体
                entities = []
                for etype in ["chinese", "number", "email", "phone", "url"]:
                    result = tool.func(text=text, extract_type=etype)
                    if result and result != "未找到":
                        entities.append(f"{etype}: {result}")
                return "\n".join(entities) if entities else "未提取到实体"
        return "实体提取: 需要工具支持"

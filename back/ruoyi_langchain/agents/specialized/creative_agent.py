"""
创意 Agent - 负责内容创作和生成
"""

from ruoyi_langchain.agents.base.base_agent import BaseAgent
from typing import List, Dict


class CreativeAgent(BaseAgent):
    """创意助手 - 负责内容创作和生成"""
    
    def __init__(self, tools: List = None, model: str = "qwen-turbo", llm_config: Dict = None):
        system_prompt = """你是一个富有创意的助手，擅长：
1. 内容创作 - 文章、报告、文案撰写
2. 图片生成 - 根据描述生成创意图片
3. 方案设计 - 制定计划、方案、策略
4. 头脑风暴 - 生成多样化的创意点子

你的风格：创意十足、表达生动、结构清晰"""
        
        super().__init__(
            name="creative",
            role="creative_writer",
            description="内容创作和创意生成",
            model=model,
            system_prompt=system_prompt,
            tools=tools,
            llm_config=llm_config
        )
    
    def write_article(self, topic: str, style: str = "informative", 
                       length: str = "medium") -> str:
        """撰写文章"""
        length_map = {"short": "500字", "medium": "1500字", "long": "3000字"}
        style_map = {
            "informative": "信息性强、客观中立",
            "creative": "创意十足、生动有趣",
            "formal": "正式严谨、逻辑清晰",
            "casual": "轻松随意、口语化"
        }
        
        prompt = f"""请撰写一篇关于「{topic}」的文章：
- 字数：{length_map.get(length, '1500字')}
- 风格：{style_map.get(style, '信息性强')}
- 要求：结构完整、有深度、可读性强"""
        
        return self.invoke(prompt)
    
    def generate_image(self, description: str, style: str = "realistic") -> str:
        """生成图片"""
        for tool in self.tools:
            if tool.name == "generate_image":
                return tool.func(prompt=description, size="1024x1024")
        return f"图片生成提示词: {description}"
    
    def brainstorm(self, topic: str, num_ideas: int = 5) -> List[str]:
        """头脑风暴"""
        prompt = f"""针对「{topic}」，请生成 {num_ideas} 个创意想法：
要求：
1. 每个想法要有独特视角
2. 简要说明实现思路
3. 标注适用场景

请以列表形式输出。"""
        
        result = self.invoke(prompt)
        
        # 解析结果
        ideas = []
        for line in result.split("\n"):
            if line.strip() and (line[0].isdigit() or line.startswith("-") or line.startswith("•")):
                ideas.append(line.strip())
        
        return ideas if ideas else [result]
    
    def write_copy(self, product: str, platform: str = "general") -> str:
        """撰写营销文案"""
        platform_styles = {
            "xiaohongshu": "小红书风格： emoji + 分段 + 标签",
            "wechat": "微信公众号风格：标题党 + 干货",
            "weibo": "微博风格：简短有力 + 热搜话题",
            "general": "通用风格：简洁明了"
        }
        
        prompt = f"""为「{product}」撰写营销文案：
平台：{platform_styles.get(platform, '通用')}
要求：吸引眼球、突出卖点、引导行动"""
        
        return self.invoke(prompt)
    
    def make_plan(self, goal: str, constraints: str = "") -> str:
        """制定计划"""
        prompt = f"""请为实现「{goal}」制定详细计划：
{f"约束条件：{constraints}" if constraints else ""}

计划要求：
1. 分解为具体步骤
2. 每步有明确目标
3. 标注时间节点
4. 考虑可能的风险"""
        
        return self.invoke(prompt)

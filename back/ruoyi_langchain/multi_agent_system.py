"""
多 Agent 协作系统
"""

from typing import Dict, List, Optional, Any
import os

from ruoyi_langchain.agents.specialized import (
    ResearchAgent,
    KnowledgeAgent,
    AnalysisAgent,
    CreativeAgent
)
from ruoyi_langchain.agents.supervisor import SupervisorAgent
from ruoyi_langchain.agents.base import BaseAgent

# 工具导入
from ruoyi_langchain.tools.knowledge_tool import knowledge_tool
from ruoyi_langchain.tools.web_search_tool import web_search_tool
from ruoyi_langchain.tools.image_generation_tool import image_generation_tool
from ruoyi_langchain.tools.table_tool import table_tool
from ruoyi_langchain.tools.nlp_text_tool import (
    clean_text_tool, extract_text_tool, split_text_tool, extract_knowledge_tool
)
from ruoyi_langchain.tools.nlp_table_tool import (
    header_encode_tool, header_similarity_tool, find_similar_headers_tool,
    analyze_table_relationships_tool, retrieve_table_data_tool, list_tables_tool
)


class MultiAgentSystem:
    """多 Agent 协作系统"""
    
    def __init__(self, model: str = "qwen-turbo", llm_config: Dict = None):
        self.model = model
        self.llm_config = llm_config or {}
        
        # 初始化 Agent 池
        self.agents: Dict[str, BaseAgent] = {}
        
        # 初始化 Supervisor
        self.supervisor: Optional[SupervisorAgent] = None
        
        # 初始化所有 Agent
        self._initialize_agents()
    
    def _initialize_agents(self):
        """初始化所有 Agent"""
        
        # Research Agent
        self.agents["researcher"] = ResearchAgent(
            tools=[web_search_tool],
            model=self.model,
            llm_config=self.llm_config
        )
        
        # Knowledge Agent
        self.agents["knowledge"] = KnowledgeAgent(
            tools=[knowledge_tool],
            model=self.model,
            llm_config=self.llm_config
        )
        
        # Analysis Agent
        self.agents["analyst"] = AnalysisAgent(
            tools=[
                clean_text_tool,
                extract_text_tool,
                split_text_tool,
                extract_knowledge_tool,
                header_encode_tool,
                header_similarity_tool,
                find_similar_headers_tool,
                analyze_table_relationships_tool,
                retrieve_table_data_tool,
                list_tables_tool,
                table_tool
            ],
            model=self.model,
            llm_config=self.llm_config
        )
        
        # Creative Agent
        self.agents["creative"] = CreativeAgent(
            tools=[image_generation_tool],
            model=self.model,
            llm_config=self.llm_config
        )
        
        # Supervisor Agent
        self.supervisor = SupervisorAgent(
            agents=self.agents,
            model=self.model,
            llm_config=self.llm_config
        )
        
        # 设置 Agent 间通信
        for agent in self.agents.values():
            agent.set_message_callback(self._on_message)
    
    def _on_message(self, message):
        """处理 Agent 间消息"""
        # 可以在这里添加日志、监控等
        pass
    
    def chat(self, message: str, mode: str = "auto") -> Dict[str, Any]:
        """
        对话入口
        
        Args:
            message: 用户消息
            mode: 模式
                - "auto": 自动选择最合适的 Agent
                - "supervisor": 使用 Supervisor 进行多 Agent 协作
                - "researcher"/"knowledge"/"analyst"/"creative": 指定 Agent
        """
        try:
            if mode == "auto":
                # 自动选择
                result = self.supervisor.orchestrate(message)
            elif mode == "supervisor":
                # 强制多 Agent 协作
                result = self.supervisor.orchestrate(message)
            elif mode in self.agents:
                # 指定 Agent
                result = self.agents[mode].invoke(message)
            else:
                return {
                    "success": False,
                    "message": f"未知模式: {mode}",
                    "available_modes": ["auto", "supervisor"] + list(self.agents.keys())
                }
            
            return {
                "success": True,
                "data": {
                    "reply": result,
                    "mode": mode
                }
            }
        
        except Exception as e:
            return {
                "success": False,
                "message": f"执行出错: {str(e)}"
            }
    
    def get_agents_info(self) -> List[Dict]:
        """获取所有 Agent 信息"""
        agents_info = []
        
        for name, agent in self.agents.items():
            agents_info.append({
                "name": agent.name,
                "role": agent.role,
                "description": agent.description,
                "tools_count": len(agent.tools),
                "tools": [t.name for t in agent.tools]
            })
        
        return agents_info
    
    def get_execution_history(self) -> Dict:
        """获取执行历史"""
        if self.supervisor:
            return self.supervisor.get_execution_summary()
        return {"message": "Supervisor 未初始化"}


# 全局实例
_multi_agent_system: Optional[MultiAgentSystem] = None


def get_multi_agent_system(model: str = "qwen-turbo") -> MultiAgentSystem:
    """获取多 Agent 系统实例（单例）"""
    global _multi_agent_system
    
    if _multi_agent_system is None:
        _multi_agent_system = MultiAgentSystem(model=model)
    
    return _multi_agent_system


def reset_multi_agent_system():
    """重置系统实例"""
    global _multi_agent_system
    _multi_agent_system = None

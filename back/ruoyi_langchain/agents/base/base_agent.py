"""
Agent 基类 - 支持角色定义和消息传递
"""

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from typing import List, Dict, Any, Optional, Callable
import os
import json


class AgentMessage:
    """Agent 间传递的消息"""
    def __init__(self, sender: str, receiver: str, content: str, 
                 msg_type: str = "text", metadata: Dict = None):
        self.sender = sender
        self.receiver = receiver
        self.content = content
        self.msg_type = msg_type  # text, tool_result, system
        self.metadata = metadata or {}
        self.timestamp = None
    
    def to_dict(self) -> Dict:
        return {
            "sender": self.sender,
            "receiver": self.receiver,
            "content": self.content,
            "msg_type": self.msg_type,
            "metadata": self.metadata
        }


class BaseAgent:
    """支持角色定义的 Agent 基类"""
    
    def __init__(
        self, 
        name: str,
        role: str,
        description: str,
        model: str = "qwen-turbo",
        system_prompt: str = "",
        tools: List = None,
        llm_config: Dict = None
    ):
        self.name = name
        self.role = role  # 如: "researcher", "analyst", "coordinator"
        self.description = description
        self.tools = tools or []
        
        # LLM 配置
        llm_config = llm_config or {}
        self.llm = ChatOpenAI(
            model=model,
            base_url=llm_config.get("base_url", "https://dashscope.aliyuncs.com/compatible-mode/v1"),
            api_key=llm_config.get("api_key", os.getenv('API_KEY')),
            temperature=llm_config.get("temperature", 0.7)
        )
        
        # System prompt
        self.system_prompt = system_prompt or self._default_system_prompt()
        
        # 消息历史
        self.message_history: List[AgentMessage] = []
        
        # 回调函数（用于 Agent 间通信）
        self.on_message_callback: Optional[Callable] = None
    
    def _default_system_prompt(self) -> str:
        return f"""你是一个 {self.role}，负责 {self.description}。"""
    
    def set_message_callback(self, callback: Callable):
        """设置消息回调，用于 Agent 间通信"""
        self.on_message_callback = callback
    
    def send_message(self, receiver: str, content: str, msg_type: str = "text", metadata: Dict = None):
        """发送消息给其他 Agent"""
        msg = AgentMessage(
            sender=self.name,
            receiver=receiver,
            content=content,
            msg_type=msg_type,
            metadata=metadata
        )
        self.message_history.append(msg)
        
        # 通过回调发送
        if self.on_message_callback:
            self.on_message_callback(msg)
        
        return msg
    
    def receive_message(self, message: AgentMessage):
        """接收来自其他 Agent 的消息"""
        self.message_history.append(message)
    
    def get_context(self) -> str:
        """获取上下文信息（消息历史）"""
        if not self.message_history:
            return ""
        
        context_lines = ["=== 对话历史 ==="]
        for msg in self.message_history[-10:]:  # 最近 10 条
            context_lines.append(f"[{msg.sender} -> {msg.receiver}]: {msg.content[:200]}")
        
        return "\n".join(context_lines)
    
    def _get_tools_description(self) -> str:
        """获取工具描述"""
        if not self.tools:
            return "无"
        
        tool_descriptions = []
        for tool in self.tools:
            tool_info = f"- {tool.name}: {tool.description}"
            tool_descriptions.append(tool_info)
        
        return "\n可用工具:\n" + "\n".join(tool_descriptions)
    
    def think(self, task: str, context: str = "") -> str:
        """思考：分析任务，决定如何处理"""
        prompt = f"""{self.system_prompt}

## 当前任务
{task}

## 对话上下文
{context}

请分析任务，确定你的行动方案。返回格式：
<action>
thinking: 你的思考过程
action_type: execute_tool / respond / delegate / request_info
action_detail: 具体行动描述
</action>
"""
        response = self.llm.invoke([HumanMessage(content=prompt)])
        return response.content
    
    def execute(self, task: str, context: str = "") -> str:
        """执行任务：使用工具或直接响应"""
        # 先思考
        thought = self.think(task, context)
        
        # 解析行动
        if "<action>" in thought:
            start = thought.index("<action>") + len("<action>")
            end = thought.index("</action>")
            action_text = thought[start:end]
            
            # 检查是否需要委托
            if "delegate" in action_text.lower():
                # 提取委托目标
                if "to=" in action_text:
                    target = action_text.split("to=")[1].split()[[i for i, c in enumerate(action_text.split("to=")[1]) if c in ' \n'][0]]
                    return {"action": "delegate", "target": target, "task": task}
            
            # 检查是否需要执行工具
            if "execute_tool" in action_text.lower():
                # 提取工具名和参数
                if "<tool_call>" in thought:
                    return {"action": "execute_tool", "plan": thought}
        
        # 直接响应
        response = self.llm.invoke([
            SystemMessage(content=self.system_prompt),
            HumanMessage(content=f"任务: {task}\n\n上下文: {context}")
        ])
        return response.content
    
    def invoke(self, task: str, context: str = "") -> str:
        """通用调用入口"""
        result = self.execute(task, context)
        
        if isinstance(result, dict):
            if result.get("action") == "delegate":
                return result  # 返回委托指令
            elif result.get("action") == "execute_tool":
                # 执行工具调用流程
                return self._execute_with_tools(result.get("plan", ""), task, context)
        
        return result
    
    def _execute_with_tools(self, plan: str, task: str, context: str) -> str:
        """执行带工具的任务"""
        # 简化版：直接让 LLM 生成工具调用
        prompt = f"""{self.system_prompt}

## 任务
{task}

## 可用工具
{self._get_tools_description()}

## 执行计划
{plan}

请根据计划调用合适的工具（如果有），然后给出最终回答。
"""
        response = self.llm.invoke([HumanMessage(content=prompt)])
        return response.content

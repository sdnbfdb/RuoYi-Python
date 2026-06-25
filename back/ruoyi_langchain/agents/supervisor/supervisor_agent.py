"""
Supervisor Agent - 任务编排器和协调者
"""

from ruoyi_langchain.agents.base.base_agent import BaseAgent, AgentMessage
from typing import List, Dict, Callable, Optional
import json


class SupervisorAgent(BaseAgent):
    """任务编排器 - 负责任务分解和 Agent 协调"""
    
    def __init__(
        self, 
        agents: Dict[str, BaseAgent] = None,
        model: str = "qwen-turbo",
        llm_config: Dict = None
    ):
        system_prompt = """你是一个专业的任务协调者，擅长：
1. 任务理解 - 准确把握用户需求
2. 任务分解 - 将复杂任务拆分为可执行的子任务
3. Agent 协调 - 分配合适的 Agent 执行任务
4. 结果整合 - 汇总各 Agent 结果给出完整回答

你的团队成员：
- researcher: 研究助手，负责信息检索和网络搜索
- knowledge: 知识库助手，负责内部知识检索
- analyst: 分析助手，负责数据分析和 NLP 处理
- creative: 创意助手，负责内容创作和生成

调用格式（必须严格遵循）：
<delegate>
task: 子任务描述
to: agent_name
priority: high/medium/low
</delegate>

如需多个 Agent 协作，按顺序调用。"""
        
        super().__init__(
            name="supervisor",
            role="coordinator",
            description="任务分解和 Agent 协调",
            model=model,
            system_prompt=system_prompt,
            tools=[],  # Supervisor 不直接执行工具
            llm_config=llm_config
        )
        
        # 注册子 Agent
        self.agents: Dict[str, BaseAgent] = agents or {}
        
        # Agent 调用历史
        self.execution_history: List[Dict] = []
        
        # 设置 Agent 间通信
        for agent in self.agents.values():
            agent.set_message_callback(self._on_agent_message)
    
    def register_agent(self, agent: BaseAgent):
        """注册 Agent"""
        self.agents[agent.name] = agent
        agent.set_message_callback(self._on_agent_message)
    
    def _on_agent_message(self, message: AgentMessage):
        """处理 Agent 间的消息"""
        self.message_history.append(message)
    
    def delegate_task(self, task: str, agent_name: str, context: str = "") -> str:
        """委托任务给指定 Agent"""
        if agent_name not in self.agents:
            return f"未知 Agent: {agent_name}"
        
        agent = self.agents[agent_name]
        
        # 记录执行
        self.execution_history.append({
            "task": task,
            "agent": agent_name,
            "status": "executing"
        })
        
        # 执行任务
        result = agent.invoke(task, context)
        
        # 记录结果
        self.execution_history[-1]["status"] = "completed"
        self.execution_history[-1]["result_preview"] = str(result)[:200]
        
        # 记录消息
        agent.receive_message(AgentMessage(
            sender="supervisor",
            receiver=agent_name,
            content=task,
            msg_type="task"
        ))
        
        return result
    
    def analyze_and_plan(self, user_input: str) -> List[Dict]:
        """分析用户输入，规划任务分解"""
        prompt = f"""{self.system_prompt}

## 用户需求
{user_input}

请分析需求，判断是否需要多 Agent 协作。
返回格式（必须严格遵循）：
<plan>
subtasks: [
  {{"task": "子任务1", "agent": "agent_name", "priority": "high"}},
  {{"task": "子任务2", "agent": "agent_name", "priority": "medium"}}
]
reasoning: 你的分析思路
</plan>
"""
        response = self.llm.invoke([HumanMessage(content=prompt)])
        
        # 解析计划
        if "<plan>" in response:
            start = response.index("<plan>") + len("<plan>")
            end = response.index("</plan>")
            plan_text = response[start:end]
            
            # 简单解析
            tasks = []
            if "subtasks:" in plan_text:
                subtasks_text = plan_text.split("subtasks:")[1].split("reasoning:")[0]
                # 这里可以更精细地解析 JSON
                # 简化处理
                tasks.append({"task": user_input, "agent": self._infer_agent(user_input), "priority": "high"})
            
            return tasks
        
        # 回退：根据关键词推断
        return [{"task": user_input, "agent": self._infer_agent(user_input), "priority": "high"}]
    
    def _infer_agent(self, task: str) -> str:
        """根据任务关键词推断合适的 Agent"""
        task_lower = task.lower()
        
        if any(kw in task_lower for kw in ["搜索", "查找", "查询", "检索", "最新", "联网"]):
            return "researcher"
        elif any(kw in task_lower for kw in ["知识库", "文档", "内部", "资料", "制度"]):
            return "knowledge"
        elif any(kw in task_lower for kw in ["分析", "统计", "提取", "处理", "清洗", "表格", "数据"]):
            return "analyst"
        elif any(kw in task_lower for kw in ["写", "创作", "生成", "设计", "方案", "文案", "文章"]):
            return "creative"
        else:
            return "knowledge"  # 默认使用知识库
    
    def orchestrate(self, user_input: str) -> str:
        """编排执行：分析 → 分解 → 协作 → 整合"""
        # 1. 分析和规划
        plan = self.analyze_and_plan(user_input)
        
        if not plan:
            return "无法理解任务，请重新描述。"
        
        # 2. 执行子任务
        results = {}
        context = ""
        
        for subtask in plan:
            agent_name = subtask.get("agent", self._infer_agent(subtask["task"]))
            
            if agent_name not in self.agents:
                results[agent_name] = f"Agent {agent_name} 不可用"
                continue
            
            # 传递上下文
            result = self.delegate_task(subtask["task"], agent_name, context)
            results[agent_name] = result
            
            # 更新上下文
            context += f"\n\n=== {agent_name.upper()} 结果 ===\n{str(result)[:500]}"
        
        # 3. 整合结果
        return self._synthesize(user_input, results)
    
    def _synthesize(self, original_task: str, results: Dict) -> str:
        """整合各 Agent 结果"""
        if len(results) == 1:
            return list(results.values())[0]
        
        # 多 Agent 结果整合
        prompt = f"""## 原始任务
{original_task}

## 各 Agent 执行结果
{json.dumps(results, ensure_ascii=False, indent=2)}

请整合以上结果，给出完整、连贯的回答。
要求：
1. 结构清晰，逻辑通顺
2. 突出关键信息
3. 自然流畅，不生硬拼接
"""
        response = self.llm.invoke([HumanMessage(content=prompt)])
        return response.content
    
    def invoke(self, message: str) -> str:
        """执行编排"""
        # 检查是否需要委托
        thought = self.think(message, self.get_context())
        
        # 解析委托指令
        if "<delegate>" in thought:
            return self.orchestrate(message)
        
        # 单 Agent 处理
        agent_name = self._infer_agent(message)
        if agent_name in self.agents:
            return self.delegate_task(message, agent_name)
        
        # 直接回答
        return self.llm.invoke([HumanMessage(content=message)]).content
    
    def get_execution_summary(self) -> Dict:
        """获取执行摘要"""
        return {
            "total_tasks": len(self.execution_history),
            "history": self.execution_history,
            "available_agents": list(self.agents.keys())
        }

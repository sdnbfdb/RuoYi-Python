from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.tools import StructuredTool
from typing import List, Dict, Any
import os
import json
import re


class BaseAgent:
    def __init__(self, tools: List = None, model: str = "qwen-turbo", system_prompt: str = ""):
        self.llm = ChatOpenAI(
            model=model,
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
            api_key=os.getenv('API_KEY'),
            temperature=0.7
        )
        
        self.tools = tools or []
        self.system_prompt = system_prompt
    
    def _get_tools_description(self) -> str:
        """获取工具描述字符串"""
        if not self.tools:
            return ""
        
        tool_descriptions = []
        for tool in self.tools:
            tool_info = f"- {tool.name}: {tool.description}"
            if hasattr(tool, 'args_schema') and tool.args_schema:
                params = tool.args_schema.model_fields.keys()
                tool_info += f" (参数: {', '.join(params)})"
            tool_descriptions.append(tool_info)
        
        return "\n可用工具:\n" + "\n".join(tool_descriptions)
    
    def _get_tools_schema(self) -> List[Dict[str, Any]]:
        """获取工具的JSON Schema描述，用于标准工具调用"""
        schemas = []
        for tool in self.tools:
            schema = {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": {}
                }
            }
            
            if hasattr(tool, 'args_schema') and tool.args_schema:
                for field_name, field_info in tool.args_schema.model_fields.items():
                    field_type = "string"
                    if hasattr(field_info.annotation, '__origin__'):
                        if field_info.annotation.__origin__ == list:
                            field_type = "array"
                        elif field_info.annotation.__origin__ == dict:
                            field_type = "object"
                    elif field_info.annotation == int:
                        field_type = "integer"
                    elif field_info.annotation == float:
                        field_type = "number"
                    elif field_info.annotation == bool:
                        field_type = "boolean"
                    
                    schema["function"]["parameters"][field_name] = {
                        "type": field_type,
                        "description": field_info.description or ""
                    }
            
            schemas.append(schema)
        
        return schemas
    
    def _find_tool(self, tool_name: str):
        """根据名称查找工具"""
        for tool in self.tools:
            if tool.name == tool_name:
                return tool
        return None
    
    def _call_tool(self, tool_name: str, args: Dict) -> str:
        """调用工具"""
        tool = self._find_tool(tool_name)
        if not tool:
            return f"工具 '{tool_name}' 不存在"
        
        try:
            result = tool.func(**args)
            return str(result)
        except Exception as e:
            return f"调用工具 '{tool_name}' 失败: {str(e)}"
    
    def _parse_tool_call(self, content: str) -> Dict[str, Any]:
        """解析工具调用格式，支持多种格式"""
        try:
            if "<tool_call>" in content and "</tool_call>" in content:
                start = content.index("<tool_call>") + len("<tool_call>")
                end = content.index("</tool_call>")
                tool_json = content[start:end].strip()
                return json.loads(tool_json)
            elif "tool_calls" in content:
                match = re.search(r'"tool_calls":\s*\[(.+?)\]', content, re.DOTALL)
                if match:
                    return {"tool_calls": json.loads(f"[{match.group(1)}]")}
            elif '"tool"' in content or '"name"' in content:
                match = re.search(r'\{[\s\S]*?"tool"\s*:\s*"([^"]+)"[\s\S]*?\}', content)
                if match:
                    return json.loads(match.group(0))
            elif "function" in content:
                match = re.search(r'\{[\s\S]*?"function"\s*:\s*\{[\s\S]*?"name"\s*:\s*"([^"]+)"[\s\S]*?\}\}', content)
                if match:
                    return {"tool_calls": [{"function": json.loads(match.group(0))}]}
        except json.JSONDecodeError:
            pass
        
        return {}
    
    def invoke(self, message: str) -> str:
        """执行Agent对话，支持工具调用"""
        tool_desc = self._get_tools_description()
        tool_schemas = self._get_tools_schema()
        
        full_prompt = f"""你是一个智能助手，必须根据用户需求调用合适的工具。{self.system_prompt}

可用工具列表:
{tool_desc}

调用工具格式要求（必须严格遵循）:
<tool_call>
{{
    "tool": "工具名称",
    "args": {{参数键值对}}
}}
</tool_call>

示例:
用户问"列出知识库"，你应该输出:
<tool_call>
{{
    "tool": "query_knowledge",
    "args": {{"action": "list"}}
}}
</tool_call>

用户问题: {message}

请立即分析并调用合适的工具，不要直接回答！"""
        
        messages = [HumanMessage(content=full_prompt)]
        
        try:
            response = self.llm.invoke(messages)
            content = response.content
            
            tool_data = self._parse_tool_call(content)
            
            if "tool" in tool_data and tool_data["tool"]:
                tool_name = tool_data["tool"]
                tool_args = tool_data.get("args", {})
                
                tool_result = self._call_tool(tool_name, tool_args)
                
                summary_prompt = f"""以下是工具调用结果，请用自然语言总结给用户：

工具名称: {tool_name}
参数: {tool_args}
结果:
{tool_result}

用户原始问题: {message}

请给出友好、自然的总结回答。"""
                
                summary_response = self.llm.invoke([HumanMessage(content=summary_prompt)])
                return summary_response.content
            
            elif "tool_calls" in tool_data and tool_data["tool_calls"]:
                tool_calls = tool_data["tool_calls"]
                results = []
                
                for tool_call in tool_calls:
                    if isinstance(tool_call, dict) and "function" in tool_call:
                        func_info = tool_call["function"]
                        tool_name = func_info.get("name", "")
                        try:
                            tool_args = json.loads(func_info.get("arguments", "{}"))
                        except json.JSONDecodeError:
                            tool_args = {}
                        
                        if tool_name:
                            result = self._call_tool(tool_name, tool_args)
                            results.append({
                                "tool": tool_name,
                                "args": tool_args,
                                "result": result
                            })
                
                if results:
                    results_text = "\n\n".join([
                        f"工具: {r['tool']}\n参数: {r['args']}\n结果: {r['result']}"
                        for r in results
                    ])
                    
                    summary_prompt = f"""以下是工具调用结果，请用自然语言总结给用户：

{results_text}

用户原始问题: {message}

请给出友好、自然的总结回答。"""
                    
                    summary_response = self.llm.invoke([HumanMessage(content=summary_prompt)])
                    return summary_response.content
            
            return content
                
        except Exception as e:
            return f"调用出错: {str(e)}"
    
    def chat(self, message: str, conversation_id: str = None) -> str:
        return self.invoke(message)

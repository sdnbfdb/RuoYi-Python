import os
import json
import re
import sys
import requests
from typing import List, Dict, Any

# 加载环境变量
try:
    from dotenv import load_dotenv
    _env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'old', '.env')
    load_dotenv(_env_path)
except Exception:
    pass

# DashScope API 配置（使用 requests + verify=False 绕过 SSL 问题）
DASHSCOPE_API_KEY = os.getenv('API_KEY') or os.getenv('QWEN_API_KEY') or "sk-833a4c468f51407f91381661324e3878"
DASHSCOPE_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"

# 禁用 SSL 警告
try:
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
except Exception:
    pass


def _call_llm(messages: List[Dict], model: str = "qwen-turbo", timeout: int = 60) -> str:
    """直接用 requests 调用 DashScope，支持 verify=False"""
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {DASHSCOPE_API_KEY}"
    }
    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 4096
    }
    try:
        response = requests.post(
            f"{DASHSCOPE_BASE_URL}/chat/completions",
            headers=headers,
            json=payload,
            verify=False,
            timeout=timeout
        )
        if response.status_code == 200:
            result = response.json()
            if result.get("choices"):
                return result["choices"][0]["message"]["content"] or ""
            return f"API返回异常: {result.get('message', '无内容')}"
        else:
            return f"HTTP错误: {response.status_code}"
    except Exception as e:
        return f"请求失败: {str(e)}"


class BaseAgent:
    def __init__(self, tools: List = None, model: str = "qwen-turbo", system_prompt: str = ""):
        self.model = model
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
                try:
                    params = tool.args_schema.model_fields.keys()
                    tool_info += f" (参数: {', '.join(params)})"
                except Exception:
                    pass
            tool_descriptions.append(tool_info)
        return "\n".join(tool_descriptions)

    def _get_tools_schema(self) -> List[Dict[str, Any]]:
        """获取工具的 JSON Schema，用于 function calling"""
        schemas = []
        for tool in self.tools:
            schema = {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                }
            }
            if hasattr(tool, 'args_schema') and tool.args_schema:
                try:
                    for field_name, field_info in tool.args_schema.model_fields.items():
                        field_type = "string"
                        ann = field_info.annotation
                        if hasattr(ann, '__origin__'):
                            if ann.__origin__ == list:
                                field_type = "array"
                            elif ann.__origin__ == dict:
                                field_type = "object"
                        elif ann == int:
                            field_type = "integer"
                        elif ann == float:
                            field_type = "number"
                        elif ann == bool:
                            field_type = "boolean"
                        schema["function"]["parameters"]["properties"][field_name] = {
                            "type": field_type,
                            "description": field_info.description or ""
                        }
                        # 判断 required 字段（pydantic v2）
                        try:
                            from pydantic_core import PydanticUndefinedType
                            if isinstance(field_info.default, PydanticUndefinedType):
                                schema["function"]["parameters"]["required"].append(field_name)
                        except Exception:
                            pass
                except Exception:
                    pass
            schemas.append(schema)
        return schemas

    def _find_tool(self, tool_name: str):
        for tool in self.tools:
            if tool.name == tool_name:
                return tool
        return None

    def _call_tool(self, tool_name: str, args: Dict) -> str:
        tool = self._find_tool(tool_name)
        if not tool:
            return f"工具 '{tool_name}' 不存在"
        try:
            result = tool.func(**args)
            return str(result)
        except Exception as e:
            return f"调用工具 '{tool_name}' 失败: {str(e)}"

    def _parse_tool_call(self, content: str) -> Dict[str, Any]:
        """解析工具调用，支持 <tool_call> 标签和 JSON 格式"""
        try:
            if "<tool_call>" in content and "</tool_call>" in content:
                start = content.index("<tool_call>") + len("<tool_call>")
                end = content.index("</tool_call>")
                tool_json = content[start:end].strip()
                return json.loads(tool_json)
            match = re.search(r'\{[^{}]*"tool"\s*:\s*"([^"]+)"[^{}]*\}', content, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(0))
                except Exception:
                    pass
        except Exception:
            pass
        return {}

    def invoke(self, message: str) -> str:
        """执行 Agent 对话，支持 function calling（标准工具调用）"""
        tool_schemas = self._get_tools_schema()
        tool_desc = self._get_tools_description()

        system_content = (
            "你是一个智能助手，能够调用工具帮助用户解决问题。"
            + (self.system_prompt or "")
            + "\n\n可用工具：\n"
            + tool_desc
        )

        messages = [
            {"role": "system", "content": system_content},
            {"role": "user", "content": message}
        ]

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {DASHSCOPE_API_KEY}"
        }
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 4096
        }
        if tool_schemas:
            payload["tools"] = tool_schemas

        try:
            response = requests.post(
                f"{DASHSCOPE_BASE_URL}/chat/completions",
                headers=headers,
                json=payload,
                verify=False,
                timeout=60
            )

            if response.status_code != 200:
                return f"API请求失败: HTTP {response.status_code}"

            result = response.json()
            if not result.get("choices"):
                return f"API返回异常: {result.get('message', str(result)[:200])}"

            choice = result["choices"][0]
            msg = choice.get("message", {})

            # 处理 function calling 返回
            tool_calls = msg.get("tool_calls")
            if tool_calls:
                tool_results = []
                for tc in tool_calls:
                    func = tc.get("function", {})
                    tool_name = func.get("name", "")
                    try:
                        tool_args = json.loads(func.get("arguments", "{}"))
                    except Exception:
                        tool_args = {}
                    if tool_name:
                        res = self._call_tool(tool_name, tool_args)
                        tool_results.append({
                            "tool": tool_name,
                            "args": tool_args,
                            "result": res
                        })

                if tool_results:
                    # 将工具结果发回给模型总结
                    messages.append({"role": "assistant", "content": "", "tool_calls": tool_calls})
                    for i, tr in enumerate(tool_results):
                        messages.append({
                            "role": "tool",
                            "content": tr["result"],
                            "tool_call_id": tool_calls[i]["id"] if i < len(tool_calls) else f"call_{i}"
                        })

                    summary_payload = {
                        "model": self.model,
                        "messages": messages,
                        "temperature": 0.7,
                        "max_tokens": 4096
                    }
                    summary_resp = requests.post(
                        f"{DASHSCOPE_BASE_URL}/chat/completions",
                        headers=headers,
                        json=summary_payload,
                        verify=False,
                        timeout=60
                    )
                    if summary_resp.status_code == 200:
                        sr = summary_resp.json()
                        if sr.get("choices"):
                            final_content = sr["choices"][0]["message"].get("content") or ""
                            if final_content:
                                return final_content
                    # 降级：直接返回工具结果
                    return "\n\n".join([r["result"] for r in tool_results])

            # 无工具调用，直接返回内容
            content = msg.get("content") or ""

            # 降级：尝试解析 <tool_call> 格式
            if content and "<tool_call>" in content:
                tool_data = self._parse_tool_call(content)
                if "tool" in tool_data:
                    tool_name = tool_data["tool"]
                    tool_args = tool_data.get("args", {})
                    tool_result = self._call_tool(tool_name, tool_args)
                    summary = _call_llm([
                        {"role": "user", "content": (
                            f"工具{tool_name}返回结果：\n{tool_result}"
                            f"\n\n请用自然语言回答用户问题：{message}"
                        )}
                    ], model=self.model)
                    return summary

            return content if content else "我无法处理该请求，请重新描述您的需求。"

        except Exception as e:
            return f"调用出错: {str(e)}"

    def chat(self, message: str, conversation_id: str = None) -> str:
        return self.invoke(message)

import json
import os
import time
from datetime import datetime
import requests

DASHSCOPE_API_KEY = "sk-833a4c468f51407f91381661324e3878"
DASHSCOPE_BASE_URL = "https://dashscope.aliyuncs.com/api/v1"

REACT_SYSTEM_PROMPT = """
你是一个拥有反思和规划能力的智能助手。你需要按照以下格式进行思考和行动：

## 思考-行动循环

在每次回复时，你必须先思考再行动。你的回复必须严格遵循以下格式之一：

### 格式1：直接回答（不需要调用工具）
当你已经有足够的信息来回答用户问题时，直接给出最终答案。

### 格式2：思考后调用工具
```thought
[你的思考过程]
```

```action
{
  "tool_name": "[工具名称]",
  "arguments": {
    "[参数名]": "[参数值]"
  }
}
```

## 反思机制

在每个步骤中，你需要反思：
1. 当前问题是什么？
2. 我已经知道了什么信息？
3. 我需要什么额外信息？
4. 应该调用哪个工具来获取这些信息？
5. 如果上次工具调用失败或结果不理想，我是否应该换一种方式重试？

## 工具列表

以下是你可以使用的工具：
"""

def build_system_prompt(tools):
    tool_descriptions = []
    for tool in tools:
        func = tool.get("function", {})
        name = func.get("name", "")
        description = func.get("description", "")
        params = func.get("parameters", {}).get("properties", {})
        
        param_lines = []
        for param_name, param_info in params.items():
            param_lines.append(f"  - {param_name}: {param_info.get('description', '')}")
        
        tool_descriptions.append(f"- {name}: {description}\n  参数:")
        tool_descriptions.extend(param_lines)
    
    return REACT_SYSTEM_PROMPT + "\n".join(tool_descriptions) + "\n\n请严格按照上述格式回复。"

def parse_react_response(response_text):
    thought_match = None
    action_match = None
    
    thought_pattern = r'```thought\s*\n([\s\S]*?)\n```'
    action_pattern = r'```action\s*\n([\s\S]*?)\n```'
    
    import re
    thought_match = re.search(thought_pattern, response_text)
    action_match = re.search(action_pattern, response_text)
    
    thought = thought_match.group(1).strip() if thought_match else ""
    
    action = None
    if action_match:
        try:
            action = json.loads(action_match.group(1))
        except json.JSONDecodeError:
            pass
    
    if action:
        return {
            "type": "action",
            "thought": thought,
            "tool_name": action.get("tool_name"),
            "arguments": action.get("arguments", {})
        }
    else:
        return {
            "type": "answer",
            "thought": thought,
            "content": response_text
        }

def call_react_api(messages, tools, model="qwen-turbo"):
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {DASHSCOPE_API_KEY}"
    }
    
    payload = {
        "model": model,
        "messages": messages,
        "tools": tools,
        "temperature": 0.7,
        "max_tokens": 4096
    }
    
    response = requests.post(
        f"{DASHSCOPE_BASE_URL}/chat/completions",
        headers=headers,
        json=payload,
        verify=False,
        timeout=120
    )
    
    if response.status_code == 200:
        result = response.json()
        if result.get("choices"):
            choice = result["choices"][0]
            message_obj = choice.get("message", {})
            
            tool_calls = message_obj.get("tool_calls")
            if tool_calls and len(tool_calls) > 0:
                tool_call = tool_calls[0]
                return {
                    "type": "tool_call",
                    "tool_name": tool_call["function"]["name"],
                    "arguments": json.loads(tool_call["function"]["arguments"]),
                    "tool_call_id": tool_call["id"],
                    "raw_message": message_obj
                }
            else:
                return {
                    "type": "answer",
                    "content": message_obj.get("content", "")
                }
        else:
            error_msg = result.get("message", "API返回无结果")
            return {"type": "error", "content": f"调用失败: {error_msg}"}
    else:
        return {"type": "error", "content": f"HTTP错误: {response.status_code}"}

def react_loop(user_message, tools, handlers, model="qwen-turbo", save=True, conversation_id=None, history_messages=None, display_prompt=None, max_steps=5):
    if not conversation_id:
        conversation_id = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    messages = []
    
    system_prompt = build_system_prompt(tools)
    messages.append({"role": "system", "content": system_prompt})
    
    if history_messages:
        for msg in history_messages:
            if msg.get("role") != "system":
                messages.append(msg)
    
    messages.append({"role": "user", "content": user_message})
    
    conversation_history = []
    
    for step in range(max_steps):
        print(f'[ReAct] 步骤 {step + 1}/{max_steps}', flush=True)
        
        api_result = call_react_api(messages, tools, model)
        
        if api_result["type"] == "error":
            return api_result["content"], conversation_id
        
        if api_result["type"] == "answer":
            final_answer = api_result["content"]
            
            if conversation_history:
                history_text = "\n\n## 思考过程\n"
                for h in conversation_history:
                    if h.get("thought"):
                        history_text += f"\n### 步骤 {h['step']}: {h['thought']}\n"
                    if h.get("action"):
                        history_text += f"**行动**: {h['action']}\n"
                    if h.get("observation"):
                        history_text += f"**结果**: {h['observation'][:200]}...\n"
                final_answer += history_text
            
            if save:
                _save_conversation(conversation_id, display_prompt or user_message, final_answer)
            
            return final_answer, conversation_id
        
        if api_result["type"] == "tool_call":
            tool_name = api_result["tool_name"]
            tool_args = api_result["arguments"]
            tool_call_id = api_result["tool_call_id"]
            
            handler = handlers.get(tool_name)
            if handler:
                try:
                    tool_result = handler(**tool_args)
                except Exception as e:
                    tool_result = {"success": False, "message": f"工具执行失败: {str(e)}"}
            else:
                tool_result = {"success": False, "message": f"未找到工具: {tool_name}"}
            
            observation = json.dumps(tool_result, ensure_ascii=False, indent=2)
            
            conversation_history.append({
                "step": step + 1,
                "thought": "",
                "action": f"{tool_name}({json.dumps(tool_args, ensure_ascii=False)})",
                "observation": observation
            })
            
            messages.append({
                "role": "assistant",
                "content": None,
                "tool_calls": [{
                    "id": tool_call_id,
                    "type": "function",
                    "function": {
                        "name": tool_name,
                        "arguments": tool_args
                    }
                }]
            })
            
            messages.append({
                "role": "tool",
                "content": observation,
                "tool_call_id": tool_call_id
            })
            
            print(f'[ReAct] 调用工具 {tool_name}, 结果: {tool_result.get("success", False)}', flush=True)
    
    final_answer = f"已达到最大思考步数({max_steps}步)。以下是我的思考过程和当前结论：\n\n"
    
    for h in conversation_history:
        if h.get("thought"):
            final_answer += f"\n### 步骤 {h['step']}: {h['thought']}\n"
        if h.get("action"):
            final_answer += f"**行动**: {h['action']}\n"
        if h.get("observation"):
            final_answer += f"**结果**: {h['observation'][:300]}...\n"
    
    final_answer += "\n请提供更多信息或简化问题，我将继续帮您分析。"
    
    if save:
        _save_conversation(conversation_id, display_prompt or user_message, final_answer)
    
    return final_answer, conversation_id

def _save_conversation(conversation_id, question, answer):
    data_dir = os.path.join(os.path.dirname(__file__), '..', 'old', 'data')
    os.makedirs(data_dir, exist_ok=True)
    
    file_path = os.path.join(data_dir, f'{conversation_id}.json')
    try:
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        else:
            data = {
                'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'conversation_id': conversation_id,
                'qa_pairs': []
            }
        
        data['qa_pairs'].append({
            'question': question,
            'answer': answer,
            'question_attachments': [],
            'answer_attachments': []
        })
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f'[WARN] ReAct保存对话失败: {e}', flush=True)
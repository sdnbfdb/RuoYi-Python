import json
import os
import time
from datetime import datetime
import requests

DASHSCOPE_API_KEY = "sk-833a4c468f51407f91381661324e3878"
DASHSCOPE_BASE_URL = "https://dashscope.aliyuncs.com/api/v1"

def call_api(message, model="qwen-turbo", save=True, conversation_id=None, history_messages=None):
    if not conversation_id:
        conversation_id = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {DASHSCOPE_API_KEY}"
    }
    
    messages = []
    if history_messages:
        messages.extend(history_messages)
    
    messages.append({"role": "user", "content": message})
    
    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 2048
    }
    
    response = requests.post(
        f"{DASHSCOPE_BASE_URL}/chat/completions",
        headers=headers,
        json=payload,
        verify=False,
        timeout=60
    )
    
    if response.status_code == 200:
        result = response.json()
        if result.get("choices"):
            reply = result["choices"][0]["message"]["content"]
            if save:
                _save_conversation(conversation_id, message, reply)
            return reply, conversation_id
        else:
            error_msg = result.get("message", "API返回无结果")
            return f"调用失败: {error_msg}", conversation_id
    else:
        return f"HTTP错误: {response.status_code}", conversation_id

def call_api_with_tools(message, tools, handlers, model="qwen-turbo", save=True, conversation_id=None, history_messages=None, display_prompt=None):
    if not conversation_id:
        conversation_id = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {DASHSCOPE_API_KEY}"
    }
    
    messages = []
    if history_messages:
        messages.extend(history_messages)
    
    messages.append({"role": "user", "content": message})
    
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
                tool_name = tool_call["function"]["name"]
                tool_args = json.loads(tool_call["function"]["arguments"])
                
                handler = handlers.get(tool_name)
                if handler:
                    try:
                        tool_result = handler(**tool_args)
                    except Exception as e:
                        tool_result = {"success": False, "message": f"工具执行失败: {str(e)}"}
                else:
                    tool_result = {"success": False, "message": f"未找到工具: {tool_name}"}
                
                observation = json.dumps(tool_result, ensure_ascii=False)
                
                messages.append({
                    "role": "assistant",
                    "content": None,
                    "tool_calls": tool_calls
                })
                messages.append({
                    "role": "tool",
                    "content": observation,
                    "tool_call_id": tool_call["id"]
                })
                
                second_payload = {
                    "model": model,
                    "messages": messages,
                    "tools": tools,
                    "temperature": 0.7,
                    "max_tokens": 4096
                }
                
                second_response = requests.post(
                    f"{DASHSCOPE_BASE_URL}/chat/completions",
                    headers=headers,
                    json=second_payload,
                    verify=False,
                    timeout=120
                )
                
                if second_response.status_code == 200:
                    second_result = second_response.json()
                    if second_result.get("choices"):
                        reply = second_result["choices"][0]["message"]["content"]
                        if save:
                            _save_conversation(conversation_id, display_prompt or message, reply)
                        return reply, conversation_id
                    else:
                        error_msg = second_result.get("message", "API返回无结果")
                        return f"调用失败: {error_msg}", conversation_id
                else:
                    return f"HTTP错误: {second_response.status_code}", conversation_id
            else:
                reply = message_obj.get("content", "")
                if save:
                    _save_conversation(conversation_id, display_prompt or message, reply)
                return reply, conversation_id
        else:
            error_msg = result.get("message", "API返回无结果")
            return f"调用失败: {error_msg}", conversation_id
    else:
        return f"HTTP错误: {response.status_code}", conversation_id

def _save_conversation(conversation_id, question, answer):
    data_dir = os.path.join(os.path.dirname(__file__), 'data')
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
        print(f'[WARN] 保存对话失败: {e}', flush=True)
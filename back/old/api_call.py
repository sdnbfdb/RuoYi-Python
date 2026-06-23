import os
import csv
import json
import requests
import urllib3
from dotenv import load_dotenv
from datetime import datetime

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

API_KEY = os.getenv('API_KEY')
API_ID = os.getenv('API_ID')

BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"

DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')
os.makedirs(DATA_DIR, exist_ok=True)

UPLOAD_DIR = os.path.join(os.path.dirname(__file__), '..', 'uploads', 'chat_files')
os.makedirs(UPLOAD_DIR, exist_ok=True)

def save_conversation(conversation_id, messages):
    """
    保存对话记录为 JSON 格式，支持文本/图片/文件等多类型
    messages: [{"role": "user"/"assistant", "content": "...", "attachments": [{"type": "image", "url": "..."}]}]
    """
    file_path = os.path.join(DATA_DIR, f'{conversation_id}.json')
    
    # 构建 qa_pairs
    qa_pairs = []
    current_q = None
    current_q_attachments = []
    current_a = None
    current_a_attachments = []
    
    for msg in messages:
        if msg["role"] == "user":
            if current_q is not None and current_a is not None:
                qa_pairs.append({
                    "question": current_q,
                    "answer": current_a,
                    "question_attachments": current_q_attachments,
                    "answer_attachments": current_a_attachments
                })
            current_q = msg.get("content", "")
            current_q_attachments = msg.get("attachments", [])
            current_a = None
            current_a_attachments = []
        elif msg["role"] == "assistant":
            current_a = msg.get("content", "")
            current_a_attachments = msg.get("attachments", [])
    
    if current_q is not None and current_a is not None:
        qa_pairs.append({
            "question": current_q,
            "answer": current_a,
            "question_attachments": current_q_attachments,
            "answer_attachments": current_a_attachments
        })
    
    data = {
        "time": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "conversation_id": conversation_id,
        "qa_pairs": qa_pairs
    }
    
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    return file_path

def delete_conversation(history_id):
    """删除历史记录（同时支持 json 和 txt 格式）"""
    # 优先删除 json
    json_path = os.path.join(DATA_DIR, f'{history_id}.json')
    txt_path = os.path.join(DATA_DIR, f'{history_id}.txt')
    
    deleted = False
    for file_path in [json_path, txt_path]:
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
                deleted = True
            except Exception as e:
                return {'success': False, 'message': str(e)}
    
    if deleted:
        return {'success': True, 'message': '删除成功'}
    else:
        return {'success': False, 'message': '记录不存在'}

def _clean_tool_result_for_llm(func_name: str, tool_result: dict) -> dict:
    """
    清理工具结果，去除大体积 base64 数据，只保留 LLM 需要的文本信息。
    - generate_image: 只保留 local_url，去除 base64 chart_image
    - table_chart: 去除 chart_image，传入 local_url/message
    """
    if not isinstance(tool_result, dict):
        return tool_result
    
    try:
        import copy
        cleaned = copy.deepcopy(tool_result)
        
        if func_name == 'generate_image':
            # generate_image 成功时：data.images[].local_url 是路径，不含 base64
            # 直接把路径列表告知 AI 即可
            data = cleaned.get('data', {})
            if isinstance(data, dict):
                images = data.get('images', [])
                img_urls = []
                for img in images:
                    if isinstance(img, dict):
                        local_url = img.get('local_url', '')
                        if local_url:
                            img_urls.append(local_url)
                        # 清除可能存在的 base64 字段
                        img.pop('base64', None)
                        img.pop('data', None)
                if img_urls:
                    cleaned['message'] = cleaned.get('message', '图片生成成功')
                    cleaned['image_urls'] = img_urls
                    cleaned['usage_hint'] = f'请在回复中以 Markdown 格式插入图片: ![描述]({img_urls[0]})'
        
        # 通用：去除任何值以 data:image 开头的字段（base64 图片）
        def strip_base64(obj):
            if isinstance(obj, dict):
                return {k: strip_base64(v) for k, v in obj.items()
                        if not (isinstance(v, str) and v.startswith('data:image'))}
            if isinstance(obj, list):
                return [strip_base64(i) for i in obj]
            return obj
        cleaned = strip_base64(cleaned)
        
        return cleaned
    except Exception:
        return tool_result


def call_api(prompt, model="qwen-turbo", save=True, conversation_id=None, history_messages=None, display_prompt=None, user_attachments=None, assistant_attachments=None):
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    messages = [
        {"role": "system", "content": "你是一个专业的智能助手，精通各领域的知识。请用中文回答用户的问题。当用户要求生成文章、论文、报告、摘要等内容时，你必须生成完整的实际内容，不要只返回格式模板、空框架或示例文本。严禁编造虚假的参考文献或引用来源；如果无法获取真实的引用信息，直接不写参考文献部分，绝不要虚构任何来源。"}
    ]
    
    if history_messages:
        # 过滤掉 attachments 等额外字段，只保留 role 和 content 用于 API 调用
        clean_history = []
        for msg in history_messages:
            clean_msg = {"role": msg["role"], "content": msg["content"]}
            clean_history.append(clean_msg)
        messages.extend(clean_history)
        print(f"[call_api] history_messages 数量: {len(history_messages)}, 总消息数: {len(messages)}")
    else:
        print(f"[call_api] history_messages 为空，仅发送当前消息")
    
    messages.append({"role": "user", "content": prompt})
    
    data = {
        "model": model,
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 2048
    }
    
    try:
        response = requests.post(BASE_URL, headers=headers, json=data, verify=False)
        response.raise_for_status()
        result = response.json()
        
        if "choices" in result and len(result["choices"]) > 0:
            answer = result["choices"][0]["message"]["content"]
            
            if save:
                full_messages = messages.copy()
                full_messages.append({"role": "assistant", "content": answer, "attachments": assistant_attachments or []})
                # 如果有 display_prompt，替换最后一条用户消息用于保存（保持历史记录显示原始消息）
                display = display_prompt if display_prompt else prompt
                for i in range(len(full_messages) - 1, -1, -1):
                    if full_messages[i]["role"] == "user":
                        full_messages[i] = {"role": "user", "content": display, "attachments": user_attachments or []}
                        break
                conv_id = conversation_id if conversation_id else datetime.now().strftime('%Y%m%d_%H%M%S')
                save_conversation(conv_id, full_messages[1:])
                
            return answer, conv_id if conversation_id else datetime.now().strftime('%Y%m%d_%H%M%S')
        else:
            return f"响应格式异常: {result}", None
            
    except requests.exceptions.RequestException as e:
        return f"请求失败: {e}", None


def call_api_with_tools(prompt, tools, tool_handlers, model="qwen-turbo", save=True, conversation_id=None, history_messages=None, display_prompt=None, user_attachments=None, assistant_attachments=None, max_tool_rounds=5):
    """
    支持 Function Calling 的 API 调用
    
    Args:
        prompt: 用户输入的提示词
        tools: 工具定义列表 [{"type": "function", "function": {"name": "...", "description": "...", "parameters": {}}}]
        tool_handlers: 工具执行函数字典 {"function_name": handler_function}
        max_tool_rounds: 最大工具调用轮数
    
    Returns:
        (answer, conversation_id)
    """
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    system_content = "你是一个专业的智能助手，精通各领域的知识。请用中文回答用户的问题。\n\n【工具使用原则】\n1. 你拥有多个工具：query_knowledge（查询煤矿知识库资料）、query_organization（查询组织架构信息）、web_search（联网搜索最新信息）、generate_image（生成AI图片）。\n2. 当用户的问题涉及多个维度时，你必须同时调用所有相关工具获取信息，然后综合所有工具返回的结果生成完整回答。例如：用户要求汇总员工工作成文章时，应同时调用 query_organization 获取员工信息、query_knowledge 获取煤矿相关资料、web_search 搜索行业补充信息，再综合生成文章。\n3. 知识库（query_knowledge）是首要信息来源，联网搜索（web_search）作为知识库不足的补充。\n4. 当用户要求生成带图、配图的文案或内容时，必须调用 generate_image 工具生成匹配的AI图片。工具会返回图片的 local_url，你必须在最终回复中使用该 local_url 以 Markdown 格式 ![描述](local_url) 插入图片。严禁编造不存在的图片路径或URL。\n5. 禁止编造数据，所有事实信息必须通过工具获取。\n\n【内容生成原则】\n当用户要求生成文章、论文、报告、摘要、文案等内容时，必须生成完整的实际内容，不要只返回格式模板、空框架或示例文本。\n\n【历史图片引用原则】\n当用户消息中包含【之前对话中生成的图片和图表】时，你必须在生成的内容中引用这些图片，使用相同的Markdown格式 ![描述](url) 插入到文章或文案的合适位置。不要遗漏任何一张历史图片。\n\n【综合信息生成原则】\n当用户要求写文章、文案、科普内容时，你必须：\n1. 调用 web_search 搜索相关最新信息和案例\n2. 调用 query_knowledge 查询知识库中的相关资料\n3. 如果用户要求带图片，调用 generate_image 生成新图片\n4. 引用之前对话中已生成的所有图片和图表\n5. 综合以上所有信息生成完整内容"
    
    messages = [
        {"role": "system", "content": system_content}
    ]
    
    if history_messages:
        clean_history = []
        for msg in history_messages:
            content = msg.get("content", "")
            # 对历史消息中的大文件内容进行摘要压缩（避免 token 爆炸）
            # 超过 2000 字符的用户消息，如果包含文件数据块，则只保留消息头部
            if msg.get("role") == "user" and len(content) > 2000:
                if "【文件数据内容" in content or "以下是Excel文件" in content:
                    # 截取到文件内容开始位置，只保留用户问题部分
                    cut_pos = content.find("【文件数据内容")
                    if cut_pos == -1:
                        cut_pos = content.find("以下是Excel文件")
                    if cut_pos > 0:
                        content = content[:cut_pos] + "[文件内容已省略，仅当前消息包含完整数据]"
                    else:
                        content = content[:2000] + "...[内容已截断]"
            clean_msg = {"role": msg["role"], "content": content}
            clean_history.append(clean_msg)
        messages.extend(clean_history)
        print(f"[call_api_with_tools] history_messages 数量: {len(history_messages)}, 总消息数(含system): {len(messages)}")
    else:
        print(f"[call_api_with_tools] history_messages 为空，仅发送当前消息")
    
    messages.append({"role": "user", "content": prompt})
    
    data = {
        "model": model,
        "messages": messages,
        "tools": tools,
        "temperature": 0.7,
        "max_tokens": 2048
    }
    
    try:
        response = requests.post(BASE_URL, headers=headers, json=data, verify=False)
        response.raise_for_status()
        result = response.json()
        
        if "choices" not in result or len(result["choices"]) == 0:
            return f"响应格式异常: {result}", None
        
        message = result["choices"][0]["message"]
        
        # 处理 tool_calls
        tool_rounds = 0
        while "tool_calls" in message and tool_rounds < max_tool_rounds:
            tool_rounds += 1
            
            messages.append({
                "role": "assistant",
                "content": message.get("content", ""),
                "tool_calls": message["tool_calls"]
            })
            
            for tool_call in message["tool_calls"]:
                if tool_call.get("type") == "function":
                    func_name = tool_call["function"]["name"]
                    try:
                        func_args = json.loads(tool_call["function"]["arguments"])
                    except Exception:
                        func_args = {}
                    
                    if func_name in tool_handlers:
                        try:
                            tool_result = tool_handlers[func_name](**func_args)
                        except Exception as e:
                            tool_result = {"success": False, "message": f"工具执行失败: {str(e)}"}
                    else:
                        tool_result = {"success": False, "message": f"未知工具: {func_name}"}
                    
                    # 过滤工具结果中的大体积 base64 数据，避免塞满上下文
                    # 对 generate_image 结果：只保留 local_url 和描述信息
                    tool_result_clean = _clean_tool_result_for_llm(func_name, tool_result)
                    
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call["id"],
                        "content": json.dumps(tool_result_clean, ensure_ascii=False)
                    })
            
            # 再次请求
            data["messages"] = messages
            response = requests.post(BASE_URL, headers=headers, json=data, verify=False)
            response.raise_for_status()
            result = response.json()
            
            if "choices" in result and len(result["choices"]) > 0:
                message = result["choices"][0]["message"]
            else:
                break
        
        answer = message.get("content", "")
        
        if save:
            display = display_prompt if display_prompt else prompt
            save_messages = [
                {"role": "user", "content": display, "attachments": user_attachments or []},
                {"role": "assistant", "content": answer, "attachments": assistant_attachments or []}
            ]
            conv_id = conversation_id if conversation_id else datetime.now().strftime('%Y%m%d_%H%M%S')
            save_conversation(conv_id, save_messages)
        
        return answer, conv_id if conversation_id else datetime.now().strftime('%Y%m%d_%H%M%S')
        
    except requests.exceptions.RequestException as e:
        return f"请求失败: {e}", None


def chat():
    print("=" * 60)
    print("        RYagent 智能对话系统 (千问)")
    print("=" * 60)
    print(f"API_ID: {API_ID}")
    print("模型: qwen-turbo")
    print("输入问题进行对话，输入 'q' 退出")
    print("=" * 60)
    
    while True:
        try:
            query = input("\n您: ").strip()
            
            if not query:
                continue
                
            if query.lower() in ['q', 'quit', 'exit']:
                print("\n对话结束")
                break
            
            print("\nRYagent: ", end="")
            response = call_api(query)
            print(response)
            
        except KeyboardInterrupt:
            print("\n\n对话结束")
            break


if __name__ == "__main__":
    if not API_KEY:
        print("[错误] 未找到 API_KEY，请检查 .env 文件")
    else:
        chat()
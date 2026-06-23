"""
Chat API routes.
Handles chat, image recognition, file upload, and history management.
"""
from flask import Flask, request, jsonify
from utils.auth import require_auth
from utils.response import success_response, error_response

# In-memory session storage for table data
session_table_data = {}


def register_chat_routes(app: Flask):
    """Register chat-related routes.
    
    Args:
        app: Flask application instance
    """
    
    @app.route('/api/chat', methods=['POST'])
    @require_auth
    def api_chat():
        """Main chat endpoint with AI integration."""
        # Import here to avoid circular dependency
        from old.api_call import call_api
        from old.tool.tool import call_robot
        
        data = request.get_json()
        message = data.get('message', '')
        model = data.get('model', app.config['DEFAULT_CHAT_MODEL'])
        conversation_id = data.get('conversation_id')
        history_messages = data.get('history_messages', [])
        
        # Support multiple file uploads
        file_names = data.get('file_names', [])
        file_paths = data.get('file_paths', [])
        file_content = data.get('file_content', '')
        
        # Ensure lists
        if not isinstance(file_names, list):
            file_names = [file_names] if file_names else []
        if not isinstance(file_paths, list):
            file_paths = [file_paths] if file_paths else []
        
        if not message:
            return error_response(message="Message cannot be empty", code=400)
        
        try:
            # Check for @robot format calls
            robot_match = _parse_robot_call(message)
            if robot_match:
                robot_name, query = robot_match
                
                # Process file content if provided
                table_data = None
                if file_content:
                    table_data = _parse_file_content(file_content)
                    if table_data:
                        # Store in session
                        if conversation_id:
                            session_table_data[conversation_id] = table_data
                elif conversation_id and conversation_id in session_table_data:
                    table_data = session_table_data[conversation_id]
                
                # Check for table operations
                table_action = _parse_table_action(query)
                if table_action:
                    action, params = table_action
                    
                    # Add table_data to params
                    if table_data:
                        params['table_data'] = table_data
                    
                    result = call_robot(robot_name, action, **params)
                    
                    if result.get('success'):
                        # Update session data if table was modified
                        if result.get('table_data') and conversation_id:
                            session_table_data[conversation_id] = result['table_data']
                        reply = _format_table_result(result)
                    else:
                        reply = result.get('message', '表格操作失败')
                else:
                    result = call_robot(robot_name, 'search', query=query)
                    
                    if result.get('success'):
                        search_result = result.get('data', {}).get('search_result', {})
                        results_count = len(search_result.get('webPages', {}).get('value', []))
                        
                        if results_count > 0:
                            reply = _format_search_results(search_result)
                        else:
                            reply = f"未找到与「{query}」相关的搜索结果。"
                    else:
                        reply = result.get('message', '搜索失败')
                
                return success_response({
                    'reply': reply,
                    'conversation_id': conversation_id or __import__('uuid').uuid4().hex
                })
            
            # Call LLM
            response, conv_id = call_api(
                message, model,
                save=False,
                conversation_id=conversation_id,
                history_messages=history_messages,
                uploaded_file_names=file_names,
                uploaded_file_paths=file_paths
            )
            
            # Check for tool calls
            if _should_call_tool(response):
                tool_result = _parse_and_call_tool(response, message)
                
                if tool_result.get('success'):
                    import json
                    tool_result_prompt = f"""
工具调用结果：
{json.dumps(tool_result, ensure_ascii=False)}

请根据以上工具调用结果，用自然、友好的语言总结给用户。
                    """
                    
                    new_history = history_messages.copy()
                    new_history.append({'role': 'user', 'content': message})
                    new_history.append({'role': 'assistant', 'content': response})
                    
                    final_response, _ = call_api(
                        tool_result_prompt, model,
                        save=True,
                        conversation_id=conv_id,
                        history_messages=new_history
                    )
                    response = final_response
                else:
                    response = f"工具调用失败：{tool_result.get('message', '未知错误')}"
            
            return success_response({
                'reply': response,
                'conversation_id': conv_id
            })
            
        except Exception as e:
            app.logger.error(f"Chat error: {e}", exc_info=True)
            return error_response(message=str(e), code=500)
    
    @app.route('/api/chat/history', methods=['GET'])
    @require_auth
    def api_chat_history():
        """Get chat history."""
        # Import the existing implementation
        from routes.history_handler import get_chat_history
        return get_chat_history()
    
    @app.route('/api/chat/history/<history_id>', methods=['DELETE'])
    @require_auth
    def api_delete_history(history_id: str):
        """Delete chat history."""
        from routes.history_handler import delete_chat_history
        return delete_chat_history(history_id)


# Helper functions (should be moved to a service layer)
def _parse_robot_call(message: str):
    """Parse @robot format message."""
    import re
    robots = ['AI助手', '知识库', '联网搜索', '组织管理', '个人助手']
    
    for robot in robots:
        for pattern in [
            rf'^{re.escape(robot)}\s+(.+)$',
            rf'^@{re.escape(robot)}\s+(.+)$',
            rf'^@{re.escape(robot)}(\S.+)$'
        ]:
            match = re.match(pattern, message.strip())
            if match:
                return (robot, match.group(1).strip())
    return None


def _format_search_results(search_data: dict) -> str:
    """Format search results to friendly text."""
    if not search_data:
        return "未找到相关搜索结果。"
    
    results = search_data.get('webPages', {}).get('value', [])
    if not results:
        return "未找到相关搜索结果。"
    
    reply = f"为您找到 {len(results)} 条搜索结果：\n\n"
    for i, item in enumerate(results, 1):
        title = item.get('name', '无标题')
        url = item.get('url', '')
        summary = item.get('summary', item.get('snippet', ''))[:150]
        site_name = item.get('siteName', '')
        
        reply += f"{i}. **{title}**\n"
        if site_name:
            reply += f"   📍 {site_name}\n"
        if summary:
            reply += f"   {summary}...\n"
        if url:
            reply += f"   🔗 {url}\n"
        reply += "\n"
    
    return reply


def _parse_table_action(query: str):
    """Parse natural language table operations."""
    import re
    
    # View table pattern
    if '查看表格' in query or '显示表格' in query or '查看数据' in query:
        return ('table_view', {})
    
    # Table creation pattern
    create_match = re.search(r'(创建|新建)表格.*表头[：:](.*?)(?:，|。|$)', query)
    if create_match:
        headers = [h.strip() for h in create_match.group(2).split('，') if h.strip()]
        return ('table_create', {'headers': headers})
    
    # Statistics pattern
    stats_match = re.search(r'(统计|分析)(.*?)的(平均|总和|最大|最小|中位数)', query)
    if stats_match:
        column_name = stats_match.group(2).strip()
        return ('table_statistics', {'column_name': column_name})
    
    # Chart pattern - 支持 生成/创建/画/做/绘制/列/列出/展示/显示/呈现 + 图表类型
    chart_match = re.search(r'(生成|创建|画|做|绘制|列|列出|展示|显示|呈现)(.*?)(柱状图|折线图|饼图|饼状图|散点图|直方图)', query)
    if chart_match:
        chart_type_map = {
            '柱状图': 'bar',
            '折线图': 'line',
            '饼图': 'pie',
            '饼状图': 'pie',
            '散点图': 'scatter',
            '直方图': 'histogram'
        }
        chart_type = chart_type_map.get(chart_match.group(3), 'bar')
        return ('table_chart', {'chart_type': chart_type})
    
    # Simple table operations
    if '表格创建' in query or '创建表格' in query:
        return ('table_create', {'headers': ['姓名', '年龄', '部门']})
    
    if '表格统计' in query or '统计表格' in query:
        return ('table_statistics', {})
    
    if '生成图表' in query or '创建图表' in query:
        return ('table_chart', {'chart_type': 'bar'})
    
    if '添加行' in query:
        return ('table_add_row', {'row_data': ['新数据1', '新数据2', '新数据3']})
    
    if '添加列' in query:
        # Extract column name
        col_match = re.search(r'添加列\s+(\S+)', query)
        col_name = col_match.group(1) if col_match else '新列'
        return ('table_add_column', {'column_name': col_name})
    
    if '删除列' in query:
        col_match = re.search(r'删除列\s+(\S+)', query)
        col_name = col_match.group(1) if col_match else None
        return ('table_delete_column', {'column_name': col_name})
    
    if '删除行' in query:
        row_match = re.search(r'删除行\s*(\d+)', query)
        row_index = int(row_match.group(1)) - 1 if row_match else 0
        return ('table_delete_row', {'row_index': row_index})
    
    if '导出表格' in query or '原样输出' in query:
        return ('table_export', {})
    
    return None


def _format_table_result(result: dict) -> str:
    """Format table operation results to friendly text."""
    message = result.get('message', '操作完成')
    
    if result.get('table_data'):
        table = result['table_data']
        headers = table.get('headers', [])
        rows = table.get('rows', [])
        
        reply = f"{message}\n\n"
        reply += "| " + " | ".join(headers) + " |\n"
        reply += "| " + " | ".join(['---'] * len(headers)) + " |\n"
        
        for row in rows[:5]:  # Show first 5 rows
            reply += "| " + " | ".join(str(cell) for cell in row) + " |\n"
        
        if len(rows) > 5:
            reply += f"（共 {len(rows)} 行，显示前5行）\n"
        
        return reply
    
    if result.get('statistics'):
        stats = result['statistics']
        reply = f"{message}\n\n"
        for col, values in stats.items():
            reply += f"**{col}**\n"
            reply += f"  - 数量: {values.get('count', 0)}\n"
            reply += f"  - 平均值: {values.get('mean', 0):.2f}\n"
            reply += f"  - 中位数: {values.get('median', 0):.2f}\n"
            reply += f"  - 最小值: {values.get('min', 0)}\n"
            reply += f"  - 最大值: {values.get('max', 0)}\n"
            reply += f"  - 总和: {values.get('sum', 0):.2f}\n"
        return reply
    
    if result.get('chart_image'):
        chart_image = result['chart_image']
        chart_type = result.get('chart_type', 'chart')
        # 返回可横向滚动+点击放大的HTML图表容器
        chart_type_zh = {'bar': '柱状图', 'line': '折线图', 'pie': '饼图', 'scatter': '散点图', 'histogram': '直方图'}.get(chart_type, chart_type)
        return (f"{message}\n\n"
                f'<div class="chart-wrapper" style="overflow-x:auto;overflow-y:hidden;width:100%;margin:8px 0;">'
                f'<img src="{chart_image}" alt="{chart_type_zh}" '
                f'style="max-width:none;height:auto;min-width:600px;cursor:zoom-in;display:block;" '
                f'onclick="openImageLightbox(this.src)" title="点击放大" />'
                f'</div>')
    
    return message


def _parse_file_content(content: str):
    """Parse file content into table data structure."""
    try:
        # 统一换行符处理：\r\n -> \n，\r -> \n
        content = content.replace('\r\n', '\n').replace('\r', '\n')
        # Parse tab-separated content
        lines = content.strip().split('\n')
        if not lines:
            return None
        
        # Remove quotes and parse headers
        headers = []
        first_line = lines[0]
        
        # Handle tab-separated format with quoted fields
        # Format: "	交易编号"	"	交易单号"	...
        if '\t' in first_line:
            # Split by tab
            parts = first_line.split('\t')
            # Extract actual field names (skip empty strings, strip quotes)
            headers = []
            for part in parts:
                part = part.strip().strip('"').strip()
                if part:
                    headers.append(part)
            
            data = []
            for line in lines[1:]:
                if line.strip():
                    row_parts = line.split('\t')
                    # Extract actual field values (skip empty strings, strip quotes)
                    row = []
                    for part in row_parts:
                        part = part.strip().strip('"').strip()
                        if part:
                            row.append(part)
                    # Ensure row has same length as headers
                    if len(row) > len(headers):
                        row = row[:len(headers)]
                    elif len(row) < len(headers):
                        row = row + [''] * (len(headers) - len(row))
                    data.append(row)
        
        elif first_line.startswith('"'):
            # Standard CSV format with quotes
            import csv
            import io
            reader = csv.reader(io.StringIO(content))
            rows = list(reader)
            if rows:
                headers = rows[0]
                data = rows[1:]
            else:
                return None
        else:
            # Simple space/tab separated format
            headers = [h.strip().strip('"') for h in first_line.split()]
            data = []
            for line in lines[1:]:
                if line.strip():
                    row = [cell.strip().strip('"') for cell in line.split()]
                    data.append(row)
        
        # Clean up headers (remove extra whitespace)
        headers = [h.strip() for h in headers if h.strip()]
        
        # Ensure all rows have the same number of columns as headers
        fixed_data = []
        header_count = len(headers)
        for row in data:
            # Strip whitespace from each cell
            row = [cell.strip() for cell in row]
            # Remove empty trailing cells that exceed header count
            if len(row) > header_count:
                row = row[:header_count]
            # Fill missing cells with empty strings
            elif len(row) < header_count:
                row = row + [''] * (header_count - len(row))
            fixed_data.append(row)
        
        # 字符串数字列清洗：去除千位分隔符逗号，统一格式
        import re as _re
        cleaned_fixed_data = []
        for row in fixed_data:
            cleaned_row = []
            for cell in row:
                # 去除千位分隔符（如 "1,234.56" -> "1234.56"），只处理纯数字格式
                cleaned = _re.sub(r'^(\s*-?)[\d,]+(\.[\d]+)?\s*$',
                                  lambda m: m.group(0).replace(',', ''), cell)
                cleaned_row.append(cleaned)
            cleaned_fixed_data.append(cleaned_row)
        fixed_data = cleaned_fixed_data
        
        return {
            'headers': headers,
            'rows': fixed_data,
            'row_count': len(fixed_data),
            'col_count': len(headers),
            'table_name': 'uploaded_file'
        }
    except Exception as e:
        print(f"File content parsing error: {e}")
        return None


def _should_call_tool(response: str) -> bool:
    """Check if response contains tool call instruction."""
    return '[TOOL_CALL]' in response


def _parse_and_call_tool(response: str, user_message: str = ''):
    """Parse and execute tool call instruction."""
    import json
    from old.tool.tool import call_knowledge_base, call_organization, call_user_profile
    
    try:
        tag = '[TOOL_CALL]'
        tag_idx = response.find(tag)
        if tag_idx == -1:
            return {'success': False, 'message': '未识别到工具调用指令格式'}
        
        brace_start = response.find('{', tag_idx)
        if brace_start == -1:
            return {'success': False, 'message': '工具调用指令后缺少 JSON'}
        
        # Extract JSON with brace counting
        depth = 0
        brace_end = brace_start
        for i in range(brace_start, len(response)):
            if response[i] == '{':
                depth += 1
            elif response[i] == '}':
                depth -= 1
                if depth == 0:
                    brace_end = i + 1
                    break
        
        json_str = response[brace_start:brace_end]
        tool_data = json.loads(json_str)
        function_name = tool_data.get('function')
        params = tool_data.get('params', {})
        
        if not function_name:
            return {'success': False, 'message': '工具调用指令缺少 function 字段'}
        
        # Route to appropriate tool
        if function_name == 'call_knowledge_base':
            return call_knowledge_base(**params)
        elif function_name == 'call_organization':
            return call_organization(**params)
        elif function_name == 'call_user_profile':
            return call_user_profile(**params)
        else:
            return {'success': False, 'message': f'未知工具函数: {function_name}'}
    
    except json.JSONDecodeError as e:
        return {'success': False, 'message': f'工具调用 JSON 解析失败: {str(e)}'}
    except Exception as e:
        return {'success': False, 'message': f'工具调用异常: {str(e)}'}

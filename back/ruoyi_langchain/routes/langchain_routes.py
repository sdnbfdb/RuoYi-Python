from flask import Blueprint, request, jsonify
from ruoyi_langchain.agent_factory import AgentFactory
import json

langchain_bp = Blueprint('langchain', __name__)


@langchain_bp.route('/api/langchain/chat', methods=['POST'])
def langchain_chat():
    try:
        data = request.get_json()
        message = data.get('message', '')
        agent_type = data.get('agent_type', 'personal')
        model = data.get('model', 'qwen-turbo')
        
        if not message:
            return jsonify({
                'success': False,
                'message': '消息不能为空'
            }), 400
        
        agent = AgentFactory.create_agent_by_type(agent_type, model=model)
        response = agent.invoke(message)
        
        return jsonify({
            'success': True,
            'data': {
                'reply': response,
                'agent_type': agent_type
            }
        })
    
    except ValueError as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 400
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'服务错误: {str(e)}'
        }), 500


@langchain_bp.route('/api/langchain/agents', methods=['GET'])
def get_langchain_agents():
    agents = [
        {
            'id': 'knowledge',
            'name': '知识库助手',
            'description': '专业的煤矿知识库查询助手，支持搜索、详情、统计和向量搜索',
            'tools': ['query_knowledge']
        },
        {
            'id': 'personal',
            'name': '个人助手',
            'description': '综合型助手，包含知识库、组织管理、联网搜索、图片生成、文本处理等功能',
            'tools': ['query_knowledge', 'query_organization', 'web_search', 'generate_image', 'table_tool', 'clean_text', 'extract_text', 'split_text']
        },
        {
            'id': 'search',
            'name': '搜索助手',
            'description': '专业联网搜索助手',
            'tools': ['web_search']
        },
        {
            'id': 'nlp',
            'name': 'NLP助手',
            'description': '专业文本处理和表格分析助手，支持文本清理、分块、表头向量化、表格检索等',
            'tools': ['clean_text', 'extract_text', 'split_text', 'header_encode', 'header_similarity', 'find_similar_headers', 'analyze_table_relationships', 'retrieve_table_data', 'list_tables']
        },
        {
            'id': 'full',
            'name': '全能助手',
            'description': '包含所有功能的全能助手',
            'tools': ['query_knowledge', 'query_organization', 'web_search', 'generate_image', 'table_tool', 'clean_text', 'extract_text', 'split_text', 'header_encode', 'header_similarity', 'find_similar_headers', 'analyze_table_relationships', 'retrieve_table_data', 'list_tables']
        }
    ]
    
    return jsonify({
        'success': True,
        'data': agents
    })


@langchain_bp.route('/api/langchain/tools', methods=['GET'])
def get_langchain_tools():
    tools = [
        {
            'name': 'query_knowledge',
            'description': '查询知识库，支持列表、搜索、详情、提取、统计和向量搜索操作',
            'parameters': ['action', 'search', 'knowledge_id', 'top_k']
        },
        {
            'name': 'query_organization',
            'description': '查询组织架构信息',
            'parameters': ['action', 'name', 'parent_id']
        },
        {
            'name': 'web_search',
            'description': '联网搜索，获取最新信息',
            'parameters': ['query']
        },
        {
            'name': 'generate_image',
            'description': '使用AI生成图片',
            'parameters': ['prompt', 'size']
        },
        {
            'name': 'query_table',
            'description': '查询表格数据，支持列表、检索、分析、相似表头匹配等操作',
            'parameters': ['action', 'query_header', 'top_n', 'directory_path', 'header1', 'header2']
        },
        {
            'name': 'clean_text',
            'description': '清理文本，去除噪声、HTML标签、数字、标点等',
            'parameters': ['text', 'remove_num', 'remove_punc', 'remove_html']
        },
        {
            'name': 'extract_text',
            'description': '从文本中提取特定类型的内容（中文、数字、邮箱、手机号、网址）',
            'parameters': ['text', 'extract_type']
        },
        {
            'name': 'split_text',
            'description': '将长文本按Markdown标题和语义分块',
            'parameters': ['text', 'max_size', 'overlap']
        },
        {
            'name': 'extract_knowledge_content',
            'description': '从知识库文档中提取有效内容',
            'parameters': ['text']
        },
        {
            'name': 'encode_table_headers',
            'description': '对目录中的所有Excel/CSV文件进行表头向量化编码',
            'parameters': ['directory_path']
        },
        {
            'name': 'calculate_header_similarity',
            'description': '计算两个表头之间的相似度',
            'parameters': ['header1', 'header2']
        },
        {
            'name': 'find_similar_headers',
            'description': '查找与查询表头相似的表头',
            'parameters': ['query_header', 'top_k', 'directory_path']
        },
        {
            'name': 'analyze_table_relationships',
            'description': '分析多个表格文件之间的表头关联关系',
            'parameters': ['directory_path']
        },
        {
            'name': 'retrieve_table_data',
            'description': '根据表头匹配检索表格数据，支持多表连接',
            'parameters': ['query_header', 'top_n', 'directory_path']
        },
        {
            'name': 'list_tables',
            'description': '列出目录中所有CSV表格文件及其表头信息',
            'parameters': ['directory_path']
        }
    ]
    
    return jsonify({
        'success': True,
        'data': tools
    })


def register_langchain_routes(app):
    app.register_blueprint(langchain_bp)
"""
多 Agent 协作 API 路由
"""

from flask import Blueprint, request, jsonify
from ruoyi_langchain.multi_agent_system import get_multi_agent_system

multi_agent_bp = Blueprint('multi_agent', __name__, url_prefix='/api/multi-agent')


@multi_agent_bp.route('/chat', methods=['POST'])
def chat():
    """
    多 Agent 对话接口
    
    Body:
        {
            "message": "用户消息",
            "mode": "auto|supervisor|researcher|knowledge|analyst|creative"
        }
    """
    data = request.get_json()
    
    if not data or 'message' not in data:
        return jsonify({
            "success": False,
            "message": "缺少 message 参数"
        }), 400
    
    message = data['message']
    mode = data.get('mode', 'auto')
    
    agent_system = get_multi_agent_system()
    result = agent_system.chat(message, mode)
    
    return jsonify(result)


@multi_agent_bp.route('/agents', methods=['GET'])
def list_agents():
    """获取所有 Agent 信息"""
    agent_system = get_multi_agent_system()
    agents_info = agent_system.get_agents_info()
    
    return jsonify({
        "success": True,
        "data": agents_info
    })


@multi_agent_bp.route('/agents/<agent_name>/invoke', methods=['POST'])
def invoke_agent(agent_name: str):
    """
    直接调用指定 Agent
    
    Args:
        agent_name: researcher, knowledge, analyst, creative
    """
    data = request.get_json()
    
    if not data or 'message' not in data:
        return jsonify({
            "success": False,
            "message": "缺少 message 参数"
        }), 400
    
    agent_system = get_multi_agent_system()
    result = agent_system.chat(data['message'], mode=agent_name)
    
    return jsonify(result)


@multi_agent_bp.route('/history', methods=['GET'])
def get_history():
    """获取执行历史"""
    agent_system = get_multi_agent_system()
    history = agent_system.get_execution_history()
    
    return jsonify({
        "success": True,
        "data": history
    })


@multi_agent_bp.route('/reset', methods=['POST'])
def reset():
    """重置 Agent 系统"""
    from ruoyi_langchain.multi_agent_system import reset_multi_agent_system
    reset_multi_agent_system()
    
    return jsonify({
        "success": True,
        "message": "系统已重置"
    })


def register_multi_agent_routes(app):
    """注册路由"""
    app.register_blueprint(multi_agent_bp)
    print("[INFO] 多 Agent 协作路由注册成功")

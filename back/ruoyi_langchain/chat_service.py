from ruoyi_langchain.agent_factory import AgentFactory

class ChatService:
    def __init__(self):
        self.agents = {}
    
    def chat(self, message: str, agent_type: str = "personal", 
             model: str = "qwen-turbo", conversation_id: str = None) -> dict:
        agent_key = f"{agent_type}_{model}"
        if agent_key not in self.agents:
            self.agents[agent_key] = AgentFactory.create_agent_by_type(
                agent_type=agent_type,
                model=model
            )
        
        agent = self.agents[agent_key]
        
        try:
            response = agent.chat(message, conversation_id)
            
            return {
                'success': True,
                'data': {
                    'reply': response,
                    'conversation_id': conversation_id,
                    'agent_type': agent_type
                }
            }
        except Exception as e:
            return {
                'success': False,
                'message': str(e)
            }

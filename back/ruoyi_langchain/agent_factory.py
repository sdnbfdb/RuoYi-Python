from ruoyi_langchain.agents.knowledge_agent import KnowledgeAgent
from ruoyi_langchain.agents.personal_agent import PersonalAgent
from ruoyi_langchain.agents.nlp_agent import NLPAgent
from ruoyi_langchain.tools.knowledge_tool import knowledge_tool
from ruoyi_langchain.tools.organization_tool import organization_tool
from ruoyi_langchain.tools.web_search_tool import web_search_tool
from ruoyi_langchain.tools.image_generation_tool import image_generation_tool
from ruoyi_langchain.tools.table_tool import table_tool
from ruoyi_langchain.tools.nlp_text_tool import (
    clean_text_tool,
    extract_text_tool,
    split_text_tool,
    extract_knowledge_tool
)
from ruoyi_langchain.tools.nlp_table_tool import (
    header_encode_tool,
    header_similarity_tool,
    find_similar_headers_tool,
    analyze_table_relationships_tool,
    retrieve_table_data_tool,
    list_tables_tool
)


class AgentFactory:
    @staticmethod
    def create_knowledge_agent(model: str = "qwen-turbo"):
        tools = [knowledge_tool]
        return KnowledgeAgent(tools=tools, model=model)
    
    @staticmethod
    def create_personal_agent(model: str = "qwen-turbo"):
        tools = [
            knowledge_tool,
            organization_tool,
            web_search_tool,
            image_generation_tool,
            table_tool,
            clean_text_tool,
            extract_text_tool,
            split_text_tool,
            extract_knowledge_tool
        ]
        return PersonalAgent(tools=tools, model=model)
    
    @staticmethod
    def create_search_agent(model: str = "qwen-turbo"):
        tools = [web_search_tool]
        return PersonalAgent(tools=tools, model=model)
    
    @staticmethod
    def create_nlp_agent(model: str = "qwen-turbo"):
        tools = [
            clean_text_tool,
            extract_text_tool,
            split_text_tool,
            extract_knowledge_tool,
            header_encode_tool,
            header_similarity_tool,
            find_similar_headers_tool,
            analyze_table_relationships_tool,
            retrieve_table_data_tool,
            list_tables_tool
        ]
        return NLPAgent(tools=tools, model=model)
    
    @staticmethod
    def create_full_agent(model: str = "qwen-turbo"):
        tools = [
            knowledge_tool,
            organization_tool,
            web_search_tool,
            image_generation_tool,
            table_tool,
            clean_text_tool,
            extract_text_tool,
            split_text_tool,
            extract_knowledge_tool,
            header_encode_tool,
            header_similarity_tool,
            find_similar_headers_tool,
            analyze_table_relationships_tool,
            retrieve_table_data_tool,
            list_tables_tool
        ]
        return PersonalAgent(tools=tools, model=model)
    
    @staticmethod
    def create_agent_by_type(agent_type: str, model: str = "qwen-turbo"):
        agent_map = {
            'knowledge': AgentFactory.create_knowledge_agent,
            'personal': AgentFactory.create_personal_agent,
            'search': AgentFactory.create_search_agent,
            'nlp': AgentFactory.create_nlp_agent,
            'full': AgentFactory.create_full_agent
        }
        
        creator = agent_map.get(agent_type)
        if creator:
            return creator(model=model)
        
        raise ValueError(f"未知的 Agent 类型: {agent_type}")
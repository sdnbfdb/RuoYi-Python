"""
Knowledge base API routes.
Handles knowledge management operations (CRUD, search, statistics).
"""
from flask import Flask
from knowledge.knowledge import (
    get_knowledge_list,
    get_knowledge_detail,
    create_knowledge,
    update_knowledge,
    delete_knowledge,
    upload_attachment,
    serve_attachment,
    get_statistics,
    add_qa_record
)


def register_knowledge_routes(app: Flask):
    """Register knowledge-related routes.
    
    Args:
        app: Flask application instance
    """
    
    @app.route('/api/knowledge/list', methods=['GET'])
    def api_knowledge_list():
        """Get knowledge list with pagination and filtering."""
        return get_knowledge_list()
    
    @app.route('/api/knowledge/<knowledge_id>', methods=['GET'])
    def api_knowledge_detail(knowledge_id: str):
        """Get knowledge detail by ID."""
        return get_knowledge_detail(knowledge_id)
    
    @app.route('/api/knowledge/create', methods=['POST'])
    def api_knowledge_create():
        """Create new knowledge entry."""
        return create_knowledge()
    
    @app.route('/api/knowledge/update/<knowledge_id>', methods=['PUT', 'POST'])
    def api_knowledge_update(knowledge_id: str):
        """Update existing knowledge entry."""
        return update_knowledge(knowledge_id)
    
    @app.route('/api/knowledge/delete/<knowledge_id>', methods=['DELETE', 'POST'])
    def api_knowledge_delete(knowledge_id: str):
        """Delete knowledge entry."""
        return delete_knowledge(knowledge_id)
    
    @app.route('/api/knowledge/upload', methods=['POST'])
    def api_knowledge_upload():
        """Upload knowledge attachment."""
        return upload_attachment()
    
    @app.route('/uploads/knowledge/<filename>')
    def api_serve_knowledge_file(filename: str):
        """Serve knowledge attachment file."""
        return serve_attachment(filename)
    
    @app.route('/api/knowledge/statistics', methods=['GET'])
    def api_knowledge_statistics():
        """Get knowledge base statistics."""
        return get_statistics()
    
    @app.route('/api/knowledge/<knowledge_id>/qa', methods=['POST'])
    def api_knowledge_add_qa(knowledge_id: str):
        """Add Q&A record for knowledge entry."""
        return add_qa_record(knowledge_id)

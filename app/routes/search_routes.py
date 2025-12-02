"""
Search Routes - Global search functionality
"""
from flask import Blueprint, render_template, request, jsonify, current_app
from flask_login import login_required
from app.services.search_service import SearchService

search_bp = Blueprint('search', __name__, url_prefix='/search')

@search_bp.route('', methods=['GET'])
@login_required
def search_page():
    """Main search results page"""
    query = request.args.get('q', '').strip()
    filter_type = request.args.get('type', 'all')
    
    if not query:
        return render_template('search_results_page.html', 
                             query='', 
                             results=[], 
                             filter_type='all')
    
    try:
        # Perform search
        results = SearchService.global_search(query, filter_type)
        
        return render_template('search_results_page.html',
                             query=query,
                             results=results,
                             filter_type=filter_type)
        
    except Exception as e:
        current_app.logger.error(f"Search error: {e}")
        return render_template('search_results_page.html',
                             query=query,
                             results=[],
                             filter_type=filter_type)

@search_bp.route('/api/suggestions', methods=['GET'])
@login_required
def get_suggestions():
    """API endpoint for live search suggestions"""
    query = request.args.get('q', '').strip()
    
    if not query or len(query) < 2:
        return jsonify({'suggestions': []})
    
    try:
        suggestions = SearchService.get_search_suggestions(query, limit=5)
        return jsonify({'suggestions': suggestions})
    
    except Exception as e:
        current_app.logger.error(f"Suggestion error: {e}")
        return jsonify({'suggestions': []})

@search_bp.route('/api/live-search', methods=['GET'])
@login_required
def live_search():
    """API endpoint for live search results"""
    query = request.args.get('q', '').strip()
    filter_type = request.args.get('type', 'all')
    
    if not query or len(query) < 2:
        return jsonify({'results': []})
    
    try:
        # Get limited results for live search
        results = SearchService.global_search(query, filter_type, limit=10)
        
        # Format for JSON response
        formatted_results = []
        for result in results:
            formatted_results.append({
                'type': result['type'],
                'title': result['title'],
                'description': result['description'][:150] + '...' if len(result['description']) > 150 else result['description'],
                'url': result['url'],
                'date': result['date'],
                'status': result.get('status', '')
            })
        
        return jsonify({'results': formatted_results})
    
    except Exception as e:
        current_app.logger.error(f"Live search error: {e}")
        return jsonify({'results': []})
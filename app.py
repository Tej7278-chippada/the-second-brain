# backend/app.py
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables
load_dotenv()

# Add the Second Brain project to path
second_brain_path = Path(__file__).parent.parent / "second-brain"
sys.path.append(str(second_brain_path))

from main import SecondBrain
from auth.routes import auth_bp
from auth.utils import token_required

app = Flask(__name__)
CORS(app, origins=["http://localhost:3001", "http://192.168.96.172:3001", "http://127.0.0.1:3001", "http://localhost:8000", "https://thesecondbrain.netlify.app/"])

# Set maximum file upload size (50MB)
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024

# Register auth blueprint
app.register_blueprint(auth_bp)

# Initialize Second Brain
try:
    brain = SecondBrain()
    print(f"✅ Second Brain initialized successfully at {datetime.now()}")
except Exception as e:
    print(f"❌ Failed to initialize Second Brain: {e}")
    brain = None

# ==================== PUBLIC ROUTES ====================

@app.route('/status', methods=['GET'])
def get_status():
    if not brain:
        return jsonify({'error': 'Second Brain not initialized'}), 500
    
    # stats = brain.vector_store.get_collection_stats()
    # memory_stats = brain.memory_manager.get_memory_stats()
    
    return jsonify({
        # 'documents': stats['count'],
        # 'memories': memory_stats['total_memories'],
        'is_connected': True
    })

# ==================== PROTECTED ROUTES ====================

@app.route('/query', methods=['POST'])
@token_required
def query():
    """Protected query endpoint - User isolated"""
    if not brain:
        return jsonify({'error': 'Second Brain not initialized'}), 500
    
    data = request.json
    question = data.get('question', '')
    use_history = data.get('use_history', True)
    
    if not question:
        return jsonify({'error': 'No question provided'}), 400
    
    try:
        # Get user ID from auth middleware,  Pass user ID to Second Brain for user-specific processing
        user_id = request.user_id
        print(f"🔍 User {user_id} querying: {question[:50]}...")
        
        # Pass user_id to query for user isolation
        response = brain.query(question, use_history=use_history, user_id=user_id)
        return jsonify(response)
    except Exception as e:
        print(f"❌ Query error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/ingest', methods=['POST'])
@token_required
def ingest_file():
    """Protected file upload endpoint - User isolated"""
    if not brain:
        return jsonify({'error': 'Second Brain not initialized'}), 500
    
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    # Get user ID from auth middleware
    user_id = request.user_id
    
    # Save file temporarily with user ID in path
    upload_dir = Path(f"data/uploads/user_{user_id}")
    upload_dir.mkdir(parents=True, exist_ok=True)
    
    # Secure filename
    from werkzeug.utils import secure_filename
    filename = secure_filename(file.filename)
    file_path = upload_dir / filename
    
    try:
        file.save(file_path)
        
        # Ingest with user context
        brain.ingest_data(str(file_path), user_id=user_id)
        
        # Get the result to return chunk count
        result = brain.data_ingestor.ingest_file(str(file_path))
        if result:
            return jsonify({
                'success': True,
                'filename': filename,
                'chunks': len(result['chunks']),
                'message': f'Successfully ingested {filename}'
            })
        else:
            return jsonify({'error': 'Failed to process file'}), 500
            
    except Exception as e:
        print(f"❌ Ingest error: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        # Clean up
        if file_path.exists():
            file_path.unlink()

@app.route('/memories', methods=['GET'])
@token_required
def get_memories():
    """Get user's memories - User isolated"""
    if not brain:
        return jsonify({'error': 'Second Brain not initialized'}), 500
    
    try:
        user_id = request.user_id
        memories_data = brain.memory_manager.list_memories(user_id)
        
        memories = []
        for category, items in memories_data.items():
            for key, memory in items.items():
                memories.append({
                    'category': category,
                    'key': key,
                    'original_key': memory.get('original_key', key),
                    'memory': memory
                })
        
        # Get memory statistics
        memory_stats = brain.memory_manager.get_memory_stats(user_id)
        
        return jsonify({
            'memories': memories,
            'stats': memory_stats
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/memories', methods=['POST'])
@token_required
def add_memory():
    """Add a new memory - User isolated"""
    if not brain:
        return jsonify({'error': 'Second Brain not initialized'}), 500
    
    data = request.json
    command = data.get('command', '')
    category = data.get('category', '')
    key = data.get('key', '')
    value = data.get('value', '')
    description = data.get('description', '')
    
    if not command and not (category and key and value):
        return jsonify({'error': 'No command or memory data provided'}), 400
    
    try:
        user_id = request.user_id
        
        if command:
            # Handle natural language memory command
            response = brain.query(command, use_history=False, user_id=user_id)
            return jsonify({
                'success': 'memory' in response.get('sources', []),
                'response': response.get('response', ''),
                'sources': response.get('sources', [])
            })
        else:
            # Handle direct memory storage
            success = brain.memory_manager.memorize(user_id, category, key, value, description)
            if success:
                # Export to vector store for immediate availability
                brain.memory_manager.export_memories_to_vector(brain.vector_store, user_id)
            
            return jsonify({'success': success, 'message': 'Memory stored successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/memories/<memory_key>', methods=['DELETE'])
@token_required
def delete_memory(memory_key):
    """Delete a memory - User isolated"""
    if not brain:
        return jsonify({'error': 'Second Brain not initialized'}), 500
    
    try:
        user_id = request.user_id
        category = request.args.get('category', None)
        
        success = brain.memory_manager.forget(user_id, memory_key, category)
        return jsonify({'success': success, 'message': 'Memory deleted' if success else 'Memory not found'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/memories/search', methods=['GET'])
@token_required
def search_memories():
    """Search user's memories - User isolated"""
    if not brain:
        return jsonify({'error': 'Second Brain not initialized'}), 500
    
    query = request.args.get('q', '')
    if not query:
        return jsonify({'error': 'No search query provided'}), 400
    
    try:
        user_id = request.user_id
        results = brain.memory_manager.search_memories(user_id, query)
        
        return jsonify({
            'results': results,
            'count': len(results)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/documents', methods=['GET'])
@token_required
def get_documents():
    """Get user's documents - User isolated"""
    if not brain:
        return jsonify({'error': 'Second Brain not initialized'}), 500
    
    try:
        user_id = request.user_id
        
        # Get all documents for this user
        results = brain.vector_store.get_user_documents(user_id)
        
        # Process and organize documents
        documents_by_file = {}
        if results and results['documents']:
            for doc_id, document, metadata in zip(results['ids'], results['documents'], results['metadatas']):
                file_name = metadata.get('file_name', 'Unknown')
                if file_name not in documents_by_file:
                    documents_by_file[file_name] = {
                        'file_name': file_name,
                        'file_type': metadata.get('file_type', 'Unknown'),
                        'file_size': metadata.get('file_size', 0),
                        'ingestion_time': metadata.get('ingestion_time', ''),
                        'chunks': [],
                        'total_chunks': metadata.get('chunk_count', 1)
                    }
                
                documents_by_file[file_name]['chunks'].append({
                    'chunk_id': doc_id,
                    'chunk_index': metadata.get('chunk_index', 0),
                    'content_preview': document[:100] + '...' if len(document) > 100 else document
                })
        
        documents = list(documents_by_file.values())
        
        return jsonify({
            'documents': documents,
            'count': len(documents),
            'total_chunks': len(results['documents']) if results else 0
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/documents/<filename>', methods=['DELETE'])
@token_required
def delete_document(filename):
    """Delete a document - User isolated"""
    if not brain:
        return jsonify({'error': 'Second Brain not initialized'}), 500
    
    try:
        user_id = request.user_id
        success = brain.manager.delete_document(filename, user_id)
        return jsonify({'success': success, 'message': 'Document deleted' if success else 'Document not found'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/search', methods=['GET'])
@token_required
def search_documents():
    """Search user's documents - User isolated"""
    if not brain:
        return jsonify({'error': 'Second Brain not initialized'}), 500
    
    query = request.args.get('q', '')
    if not query:
        return jsonify({'error': 'No search query provided'}), 400
    
    try:
        user_id = request.user_id
        
        # Search in vector store with user filter
        results = brain.vector_store.search(query, n_results=10, user_id=user_id)
        
        # Organize results by file
        files_found = {}
        for result in results:
            file_name = result['metadata'].get('file_name', 'Unknown')
            if file_name not in files_found:
                files_found[file_name] = {
                    'file_name': file_name,
                    'file_type': result['metadata'].get('file_type', 'Unknown'),
                    'matches': [],
                    'relevance_score': 1 - (result['distance'] if result['distance'] else 0)
                }
            
            files_found[file_name]['matches'].append({
                'content': result['content'][:200] + '...' if len(result['content']) > 200 else result['content'],
                'chunk_index': result['metadata'].get('chunk_index', 0),
                'distance': result['distance']
            })
        
        search_results = list(files_found.values())
        search_results.sort(key=lambda x: x['relevance_score'], reverse=True)
        
        return jsonify({
            'results': search_results,
            'count': len(search_results)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/documents/upload-url', methods=['GET'])
@token_required
def get_upload_url():
    """Get a pre-signed upload URL if needed (for future S3 integration)"""
    user_id = request.user_id
    return jsonify({
        'upload_url': f'/ingest',  # Current endpoint
        'user_id': user_id,
        'max_size': 50 * 1024 * 1024  # 50MB
    })

@app.route('/export/memories', methods=['GET'])
@token_required
def export_memories():
    """Export user's memories as JSON"""
    if not brain:
        return jsonify({'error': 'Second Brain not initialized'}), 500
    
    try:
        user_id = request.user_id
        memories_data = brain.memory_manager.list_memories(user_id)
        
        return jsonify({
            'user_id': user_id,
            'exported_at': datetime.now().isoformat(),
            'memories': memories_data
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/stats', methods=['GET'])
@token_required
def get_user_stats():
    """Get user-specific statistics"""
    if not brain:
        return jsonify({'error': 'Second Brain not initialized'}), 500
    
    try:
        user_id = request.user_id
        
        # Get vector store stats for this user
        vector_results = brain.vector_store.get_user_documents(user_id)
        total_chunks = len(vector_results['documents']) if vector_results else 0
        
        # Count unique files
        unique_files = set()
        if vector_results and vector_results['metadatas']:
            for metadata in vector_results['metadatas']:
                unique_files.add(metadata.get('file_name', 'Unknown'))
        
        # Get memory stats
        memory_stats = brain.memory_manager.get_memory_stats(user_id)
        
        # Get conversation history length
        conversation_length = len(brain.get_user_history(user_id))
        
        return jsonify({
            'user_id': user_id,
            'vector_store': {
                'total_chunks': total_chunks,
                'unique_files': len(unique_files)
            },
            'memories': memory_stats,
            'conversation': {
                'history_length': conversation_length
            }
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
@app.route('/conversation/history', methods=['GET'])
@token_required
def get_conversation_history():
    """Get user's conversation history"""
    if not brain:
        return jsonify({'error': 'Second Brain not initialized'}), 500
    
    try:
        user_id = request.user_id
        
        # Get conversation history for this user
        history = brain.get_user_history(user_id)
        
        return jsonify({
            'history': history,
            'count': len(history),
            'user_id': user_id
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/conversation/history', methods=['DELETE'])
@token_required
def clear_conversation_history():
    """Clear user's conversation history"""
    if not brain:
        return jsonify({'error': 'Second Brain not initialized'}), 500
    
    try:
        user_id = request.user_id
        
        # Clear conversation history for this user
        brain.clear_user_history(user_id)
        
        return jsonify({
            'success': True,
            'message': 'Conversation history cleared',
            'user_id': user_id
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/conversation/history/export', methods=['GET'])
@token_required
def export_conversation_history():
    """Export user's conversation history"""
    if not brain:
        return jsonify({'error': 'Second Brain not initialized'}), 500
    
    try:
        user_id = request.user_id
        
        # Get conversation history for this user
        history = brain.get_user_history(user_id)
        
        return jsonify({
            'user_id': user_id,
            'exported_at': datetime.now().isoformat(),
            'history': history,
            'format': 'json',
            'message': f'Exported {len(history)} messages'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
# ==================== ERROR HANDLERS ====================

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

@app.errorhandler(413)
def too_large(error):
    return jsonify({'error': 'File too large (max 50MB)'}), 413

# ==================== MAIN ====================

if __name__ == '__main__':
    # Check required environment variables
    required_vars = ['MONGO_URI', 'JWT_SECRET', 'GOOGLE_CLIENT_ID']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"❌ Missing environment variables: {missing_vars}")
        print("💡 Create a .env file with these variables")
        sys.exit(1)
    
    # Create necessary directories
    Path("data/uploads").mkdir(parents=True, exist_ok=True)
    Path("data/processed").mkdir(parents=True, exist_ok=True)
    Path("data/chroma_db").mkdir(parents=True, exist_ok=True)
    
    print(f"🚀 Starting Second Brain API on http://0.0.0.0:8000")
    print(f"📁 Data directory: {Path('data').absolute()}")
    print(f"🔐 Auth enabled: Yes")
    
    app.run(debug=True, port=8000, host='0.0.0.0')
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
    
    stats = brain.vector_store.get_collection_stats()
    memory_stats = brain.memory_manager.get_memory_stats()
    
    return jsonify({
        'documents': stats['count'],
        'memories': memory_stats['total_memories'],
        'is_connected': True
    })

# ==================== PROTECTED ROUTES ====================

@app.route('/query', methods=['POST'])
@token_required
def query():
    """Protected query endpoint"""
    if not brain:
        return jsonify({'error': 'Second Brain not initialized'}), 500
    
    data = request.json
    question = data.get('question', '')
    use_history = data.get('use_history', True)
    
    if not question:
        return jsonify({'error': 'No question provided'}), 400
    
    try:
        # Pass user ID to Second Brain for user-specific processing, Get user ID from auth middleware
        user_id = request.user_id
        print(f"🔍 User {user_id} querying: {question[:50]}...")
        response = brain.query(question, use_history=use_history, user_id=user_id)
        return jsonify(response)
    except Exception as e:
        print(f"❌ Query error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/ingest', methods=['POST'])
@token_required
def ingest_file():
    """Protected file upload endpoint"""
    if not brain:
        return jsonify({'error': 'Second Brain not initialized'}), 500
    
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    # Save file temporarily with user ID in path
    user_id = request.user_id
    upload_dir = Path(f"data/uploads/user_{user_id}")
    upload_dir.mkdir(parents=True, exist_ok=True)
    
    # Secure filename
    from werkzeug.utils import secure_filename
    filename = secure_filename(file.filename)
    file_path = upload_dir / filename
    
    try:
        file.save(file_path)
        
        # Ingest with user context
        brain.ingest_data(str(file_path))
        # Get the result to return chunk count
        result = brain.data_ingestor.ingest_file(str(file_path))
        return jsonify({
            'success': True,
            'filename': filename,
            'chunks': len(result['chunks']) if result else 0,
            'message': f'Successfully ingested {filename}'
        })
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
    """Get user's memories"""
    if not brain:
        return jsonify({'error': 'Second Brain not initialized'}), 500
    
    try:
        memories_data = brain.memory_manager.list_memories()
        memories = []
        
        for category, items in memories_data.items():
            for key, memory in items.items():
                memories.append({
                    'category': category,
                    'original_key': key,
                    'memory': memory
                })
        
        return jsonify({'memories': memories})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/memories', methods=['POST'])
@token_required
def add_memory():
    """Add a new memory"""
    if not brain:
        return jsonify({'error': 'Second Brain not initialized'}), 500
    
    data = request.json
    command = data.get('command', '')
    
    if not command:
        return jsonify({'error': 'No command provided'}), 400
    
    try:
        success = brain.memorize_information(command)
        return jsonify({'success': success})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/memories/<memory_key>', methods=['DELETE'])
@token_required
def delete_memory(memory_key):
    """Delete a memory"""
    if not brain:
        return jsonify({'error': 'Second Brain not initialized'}), 500
    
    try:
        brain.memory_manager.forget(memory_key)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/documents', methods=['GET'])
@token_required
def get_documents():
    """Get user's documents"""
    if not brain:
        return jsonify({'error': 'Second Brain not initialized'}), 500
    
    try:
        data = brain.visualizer.show_all_documents()
        return jsonify(data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/documents/<filename>', methods=['DELETE'])
@token_required
def delete_document(filename):
    """Delete a document"""
    if not brain:
        return jsonify({'error': 'Second Brain not initialized'}), 500
    
    try:
        success = brain.manager.delete_document(filename)
        return jsonify({'success': success})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/search', methods=['GET'])
@token_required
def search_documents():
    """Search documents"""
    if not brain:
        return jsonify({'error': 'Second Brain not initialized'}), 500
    
    query = request.args.get('q', '')
    if not query:
        return jsonify({'error': 'No search query provided'}), 400
    
    try:
        results = brain.visualizer.search_documents(query)
        return jsonify({'results': results})
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
# backend/app.py
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import os
import sys
from pathlib import Path

# Add the Second Brain project to path
second_brain_path = Path(__file__).parent.parent / "second-brain"
sys.path.append(str(second_brain_path))

from main import SecondBrain

app = Flask(__name__)
CORS(app, origins=["http://localhost:3000", "http://192.168.192.172:3000", "http://127.0.0.1:3000"])

# Initialize Second Brain
try:
    brain = SecondBrain()
    print("✅ Second Brain initialized successfully")
except Exception as e:
    print(f"❌ Failed to initialize Second Brain: {e}")
    brain = None

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

@app.route('/query', methods=['POST'])
def query():
    if not brain:
        return jsonify({'error': 'Second Brain not initialized'}), 500
    
    data = request.json
    question = data.get('question', '')
    use_history = data.get('use_history', True)
    
    if not question:
        return jsonify({'error': 'No question provided'}), 400
    
    try:
        response = brain.query(question, use_history=use_history)
        return jsonify(response)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/ingest', methods=['POST'])
def ingest_file():
    if not brain:
        return jsonify({'error': 'Second Brain not initialized'}), 500
    
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    # Save file temporarily
    upload_dir = Path("uploads")
    upload_dir.mkdir(exist_ok=True)
    file_path = upload_dir / file.filename
    file.save(file_path)
    
    try:
        brain.ingest_data(str(file_path))
        # Get the result to return chunk count
        result = brain.data_ingestor.ingest_file(str(file_path))
        return jsonify({
            'success': True,
            'filename': file.filename,
            'chunks': len(result['chunks']) if result else 0
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        # Clean up
        if file_path.exists():
            file_path.unlink()

@app.route('/memories', methods=['GET'])
def get_memories():
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
def add_memory():
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
def delete_memory(memory_key):
    if not brain:
        return jsonify({'error': 'Second Brain not initialized'}), 500
    
    try:
        brain.memory_manager.forget(memory_key)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/documents', methods=['GET'])
def get_documents():
    if not brain:
        return jsonify({'error': 'Second Brain not initialized'}), 500
    
    try:
        data = brain.visualizer.show_all_documents()
        return jsonify(data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/documents/<filename>', methods=['DELETE'])
def delete_document(filename):
    if not brain:
        return jsonify({'error': 'Second Brain not initialized'}), 500
    
    try:
        success = brain.manager.delete_document(filename)
        return jsonify({'success': success})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/search', methods=['GET'])
def search_documents():
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

if __name__ == '__main__':
    app.run(debug=True, port=8000, host='0.0.0.0')
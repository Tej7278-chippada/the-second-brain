import os
import sys
from typing import Dict, Any
from core.data_ingestor import DataIngestor
from core.vector_store import VectorStore
from core.ai_engine import AIEngine
from interfaces.chat_interface import ChatInterface
from config.settings import settings

class SecondBrain:
    def __init__(self):
        # Validate settings
        settings.validate()
        
        # Initialize core components
        self.data_ingestor = DataIngestor(settings)
        self.vector_store = VectorStore(settings)
        self.ai_engine = AIEngine(settings)
        
        # Initialize interfaces
        self.chat_interface = ChatInterface(self)
        
        # Conversation history
        self.conversation_history = []
        
        print("🚀 The Second Brain initialized successfully!")
        stats = self.vector_store.get_collection_stats()
        print(f"📊 Vector store contains {stats['count']} document chunks")
    
    def ingest_data(self, file_path: str, metadata: Dict = None):
        """Ingest new data into the system"""
        if not os.path.exists(file_path):
            print(f"❌ File not found: {file_path}")
            return
            
        print(f"📥 Ingesting: {file_path}")
        result = self.data_ingestor.ingest_file(file_path, metadata)
        
        if result:
            success = self.vector_store.add_documents([result])
            if success:
                print(f"✅ Successfully ingested: {file_path}")
                print(f"📝 Extracted {len(result['chunks'])} chunks of knowledge")
            else:
                print(f"❌ Failed to add to vector store: {file_path}")
        else:
            print(f"❌ Failed to process: {file_path}")
    
    def query(self, question: str, use_history: bool = True) -> Dict[str, Any]:
        """Query The Second Brain"""
        print(f"🔍 Searching knowledge base...")
        
        # Search vector store
        search_results = self.vector_store.search(question, n_results=5)
        
        # Generate response
        history = self.conversation_history if use_history else None
        response = self.ai_engine.generate_response(question, search_results, history)
        
        # Update conversation history
        self.conversation_history.append({"role": "user", "content": question})
        self.conversation_history.append({"role": "assistant", "content": response['response']})
        
        # Keep history manageable
        if len(self.conversation_history) > 20:
            self.conversation_history = self.conversation_history[-20:]
        
        return response
    
    def interactive_chat(self):
        """Start interactive chat mode"""
        self.chat_interface.start_chat()

def main():
    # Create necessary directories
    os.makedirs("data/uploads", exist_ok=True)
    os.makedirs("data/processed", exist_ok=True)
    os.makedirs("data/chroma_db", exist_ok=True)
    
    try:
        # Initialize The Second Brain
        brain = SecondBrain()
        
        # Demo: Create a sample text file to ingest
        sample_content = """My Project Details:
Project Name: Alpha Initiative
Team Members: John Smith, Sarah Johnson, Mike Chen
Timeline: Q1 2024 - Q3 2024
Budget: $150,000
Key Objectives: 
1. Develop new customer portal
2. Implement AI features
3. Improve user engagement by 40%

Recent Meeting Notes:
We decided to use React for the frontend and Python FastAPI for the backend.
Database will be PostgreSQL with Redis for caching."""
        
        with open("sample_project.txt", "w") as f:
            f.write(sample_content)
        
        print("\n📝 Adding sample project data...")
        brain.ingest_data("sample_project.txt")
        
        # Start interactive chat
        brain.interactive_chat()
        
    except Exception as e:
        print(f"❌ Failed to initialize The Second Brain: {e}")
        print("\n💡 Troubleshooting tips:")
        print("1. Check your API keys in .env file")
        print("2. Run 'pip install -r requirements.txt'")
        print("3. Ensure you have Python 3.9+ installed")

if __name__ == "__main__":
    main()
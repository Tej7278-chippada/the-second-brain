import os
import sys
from typing import Dict, Any
from core.data_ingestor import DataIngestor
from core.vector_store import VectorStore
from core.ai_engine import AIEngine
from interfaces.chat_interface import ChatInterface
from utils.data_visualizer import DataVisualizer
from utils.data_manager import DataManager
from config.settings import settings

class SecondBrain:
    def __init__(self):
        # Validate settings
        settings.validate()
        
        # Initialize core components
        self.data_ingestor = DataIngestor(settings)
        self.vector_store = VectorStore(settings)
        self.ai_engine = AIEngine(settings)
        
        # Initialize management tools
        self.visualizer = DataVisualizer(self.vector_store)
        self.manager = DataManager(self.vector_store, self.data_ingestor)
        
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
                
                # Track this action in AI engine
                file_name = os.path.basename(file_path)
                file_ext = os.path.splitext(file_path)[1].lower()
                self.ai_engine.add_recent_action('ingest', {
                    'file_name': file_name,
                    'file_type': file_ext,
                    'content_preview': result['content'][:100] + '...' if len(result['content']) > 100 else result['content']
                })
            else:
                print(f"❌ Failed to add to vector store: {file_path}")
        else:
            print(f"❌ Failed to process: {file_path}")
    
    def query(self, question: str, use_history: bool = True) -> Dict[str, Any]:
        """Query The Second Brain"""
        print(f"🔍 Searching knowledge base...")
        
        # Track this query action
        self.ai_engine.add_recent_action('query', {
            'query': question,
            'timestamp': 'now'
        })
        
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
    
    def show_data(self):
        """Show all ingested data"""
        self.visualizer.show_document_statistics()
    
    def manage_data(self):
        """Start data management interface"""
        self._data_management_interface()
    
    def _data_management_interface(self):
        """Interactive data management interface"""
        while True:
            print("\n🔧 DATA MANAGEMENT MENU")
            print("=" * 40)
            print("1. Show all documents")
            print("2. Search documents")
            print("3. Delete specific document")
            print("4. Update document")
            print("5. Show document details")
            print("6. Export to CSV")
            print("7. Delete ALL documents")
            print("8. Back to main menu")
            
            choice = input("\nEnter your choice (1-8): ").strip()
            
            if choice == '1':
                self.visualizer.show_document_statistics()
            elif choice == '2':
                search_term = input("Enter search term: ")
                results = self.visualizer.search_documents(search_term)
                if results:
                    print(f"\n🔍 Found {len(results)} matching documents:")
                    for doc in results:
                        print(f"   📄 {doc['file_name']} - {doc['content_preview']}")
                else:
                    print("❌ No matching documents found")
            elif choice == '3':
                filename = input("Enter filename to delete: ")
                self.manager.delete_document(filename)
            elif choice == '4':
                file_path = input("Enter file path to update: ")
                self.manager.update_document(file_path)
            elif choice == '5':
                filename = input("Enter filename to show details: ")
                self.manager.show_document_details(filename)
            elif choice == '6':
                self.visualizer.export_to_csv()
            elif choice == '7':
                self.manager.delete_all_documents()
            elif choice == '8':
                break
            else:
                print("❌ Invalid choice")

    def interactive_chat_with_management(self):
        """Enhanced chat interface with management commands"""
        print("\n" + "="*60)
        print("🤖 The Second Brain - Enhanced Chat Mode")
        print("="*60)
        print("Chat Commands:")
        print("  - 'exit', 'quit', 'bye' to exit")
        print("  - 'ingest <file_path>' to add files")
        print("  - 'show data' to view all documents")
        print("  - 'manage data' to open management menu")
        print("  - 'delete <filename>' to delete specific file")
        print("  - 'search <term>' to search documents")
        print("  - 'clear' to clear conversation history")
        print("="*60)
        
        while True:
            try:
                user_input = input("\n🧠 You: ").strip()
                
                if user_input.lower() in ['exit', 'quit', 'bye']:
                    print("👋 Goodbye! Your knowledge is safely stored.")
                    break
                elif user_input.lower() == 'clear':
                    self.conversation_history = []
                    print("🗑️ Conversation history cleared.")
                elif user_input.lower() == 'show data':
                    self.show_data()
                elif user_input.lower() == 'manage data':
                    self.manage_data()
                elif user_input.startswith('ingest '):
                    file_path = user_input[7:].strip()
                    self.ingest_data(file_path)
                elif user_input.startswith('delete '):
                    filename = user_input[7:].strip()
                    self.manager.delete_document(filename)
                elif user_input.startswith('search '):
                    search_term = user_input[7:].strip()
                    results = self.visualizer.search_documents(search_term)
                    if results:
                        print(f"\n🔍 Found {len(results)} matching documents:")
                        for doc in results:
                            print(f"   📄 {doc['file_name']} - {doc['content_preview']}")
                    else:
                        print("❌ No matching documents found")
                elif user_input:
                    response = self.query(user_input)
                    print(f"\n🤖 Second Brain: {response['response']}")
                    if response.get('sources'):
                        print(f"📚 Sources: {', '.join(response['sources'])}")
                        
            except KeyboardInterrupt:
                print("\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"❌ Error: {str(e)}")
    
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
        
        # Show initial data
        brain.show_data()
        
        # Start interactive chat with management options
        brain.interactive_chat_with_management()
        # brain.interactive_chat()
        
    except Exception as e:
        print(f"❌ Failed to initialize The Second Brain: {e}")
        print("\n💡 Troubleshooting tips:")
        print("1. Check your API keys in .env file")
        print("2. Run 'pip install -r requirements.txt'")
        print("3. Ensure you have Python 3.9+ installed")

if __name__ == "__main__":
    main()
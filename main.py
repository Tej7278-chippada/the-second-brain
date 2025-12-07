# main.py
import os
import sys
from typing import Dict, Any
from core.data_ingestor import DataIngestor
from core.vector_store import VectorStore
from core.ai_engine import AIEngine
from core.memory_manager import MemoryManager
from interfaces.chat_interface import ChatInterface
from utils.data_visualizer import DataVisualizer
from utils.data_manager import DataManager
from config.settings import settings

class SecondBrain:
    def __init__(self):
        # Validate settings
        settings.validate()
        
        # Initialize core components in correct order
        self.data_ingestor = DataIngestor(settings)
        self.vector_store = VectorStore(settings)
        self.memory_manager = MemoryManager(settings)
        
        # Initialize AI Engine with memory manager
        self.ai_engine = AIEngine(settings)
        self.ai_engine.memory_manager = self.memory_manager  # Set memory manager after initialization
        self.ai_engine.vector_store = self.vector_store  # Set vector store for memory exports
        
        # Initialize management tools
        self.visualizer = DataVisualizer(self.vector_store)
        self.manager = DataManager(self.vector_store, self.data_ingestor)
        
        # Initialize interfaces
        self.chat_interface = ChatInterface(self)
        
        # Conversation history
        # self.conversation_history = []

        # User-specific conversation history
        self.user_conversations = {}
        
        print("🚀 The Second Brain initialized successfully!")
        stats = self.vector_store.get_collection_stats()
        memory_stats = self.memory_manager.get_memory_stats()
        print(f"📊 Vector store contains {stats['count']} document chunks")
        print(f"💾 Memory system contains {memory_stats['total_memories']} personal memories")
    
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

    def get_user_history(self, user_id):
        """Get conversation history for a specific user"""
        if user_id not in self.user_conversations:
            self.user_conversations[user_id] = []
        return self.user_conversations[user_id]
    
    def query(self, question: str, use_history: bool = True, user_id: str = None) -> Dict[str, Any]:
        """Query The Second Brain with user context"""
        print(f"🔍 {'User ' + user_id if user_id else 'Anonymous'} querying: {question[:50]}...")

        # Get user-specific conversation history
        if user_id and use_history:
            conversation_history = self.get_user_history(user_id)
        else:
            conversation_history = None
        
        # Track this query action
        self.ai_engine.add_recent_action('query', {
            'query': question,
            'user_id': user_id,
            'timestamp': 'now'
        })

        # Export memories to vector store BEFORE searching
        # This ensures both documents and memories are available for context
        self.memory_manager.export_memories_to_vector(self.vector_store)
        
        # Search vector store
        search_results = self.vector_store.search(question, n_results=5)
        
        # Generate response
        # history = self.conversation_history if use_history else None
        response = self.ai_engine.generate_response(question, search_results, conversation_history)
        
        # Update conversation history
        # self.conversation_history.append({"role": "user", "content": question})
        # self.conversation_history.append({"role": "assistant", "content": response['response']})
        
        # Update user-specific conversation history
        if user_id:
            self.user_conversations[user_id].append({"role": "user", "content": question})
            self.user_conversations[user_id].append({"role": "assistant", "content": response['response']})
            
            # Keep history manageable
            if len(self.user_conversations[user_id]) > 20:
                self.user_conversations[user_id] = self.user_conversations[user_id][-20:]
        
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
    
    def show_memories(self):
        """Show all stored memories with better organization"""
        memories = self.memory_manager.list_memories()
        stats = self.memory_manager.get_memory_stats()
        
        print("\n💾 PERSONAL MEMORIES")
        print("=" * 60)
        print(f"Total memories: {stats['total_memories']}")
        
        # Show borrowed items
        items_to_return = self.memory_manager.get_items_to_return()
        items_to_receive = self.memory_manager.get_items_to_receive()
        
        if items_to_return:
            print(f"\n📦 ITEMS YOU NEED TO RETURN:")
            for item in items_to_return:
                item_name = item['original_key'].split('_')[0]
                person = item['original_key'].split('_')[1]
                print(f"   • {item_name} to {person.title()}")
        
        if items_to_receive:
            print(f"\n📥 ITEMS OTHERS NEED TO RETURN TO YOU:")
            for item in items_to_receive:
                item_name = item['original_key'].split('_')[0]
                person = item['original_key'].split('_')[1]
                print(f"   • {item_name} from {person.title()}")
        
        # Show debts separately
        debts = self.memory_manager.get_all_debts()
        if debts:
            print(f"\n💰 DEBTS OWED TO YOU:")
            for debt in debts:
                person = debt['original_key'].replace('_debt', '')
                amount = debt['memory']['value']
                print(f"   • {person.title()}: {amount} rupees")
        
        # Show contacts separately
        contacts = self.memory_manager.get_all_contacts()
        if contacts:
            print(f"\n📞 CONTACTS:")
            for contact in contacts:
                name = contact['original_key'].replace('_phone', '')
                phone = contact['memory']['value']
                print(f"   • {name.title()}: {phone}")
        
        # Show other memories by category
        for category, items in memories.items():
            if items and category not in ['financial', 'contacts', 'borrowed_items']:
                print(f"\n📁 {category.upper()}:")
                for key, memory in items.items():
                    display_key = memory.get('original_key', key)
                    print(f"   🔑 {display_key}: {memory['value']}")
                    if memory.get('description'):
                        print(f"      📝 {memory['description']}")
        # Instructions to delete memories
        print("\n🗑️ To delete any memory: forget <memory_key> (ex: forget reminder_3230)")
        # print(f"To delete any memory: forget <memory_key> (ex: forget john_phone)")
    
    def memorize_information(self, command: str) -> bool:
        """Handle memorize commands directly"""
        return self.ai_engine._handle_memorize_command(command) is not None

    def interactive_chat_with_memory_management(self):
        """Enhanced chat interface with memory management commands"""
        print("\n" + "="*70)
        print("🤖 The Second Brain - Memory Enhanced Chat Mode")
        print("="*70)
        print("Chat Commands:")
        print("  - 'exit', 'quit', 'bye' to exit")
        print("  - 'ingest <file_path>' to add files")
        print("  - 'show data' to view all documents")
        print("  - 'show memories' to view personal memories")
        print("  - 'manage data' to open management menu")
        print("  - 'delete <filename>' to delete specific file")
        print("  - 'forget <memory_key>' to remove memory")
        print("  - 'search <term>' to search documents")
        print("  - 'clear' to clear conversation history")
        print("\nMemory Commands:")
        print("  - 'memorize my phone number as 1234567890'")
        print("  - 'remember that my Aadhaar is 1234-5678-9012'")
        print("  - 'store this: my license plate is ABC123'")
        print("  - 'what's my phone number?'")
        print("  - 'show me my Aadhaar details'")
        print("="*70)
        
        while True:
            try:
                user_input = input("\n🧠 You: ").strip()
                
                if user_input.lower() in ['exit', 'quit', 'bye']:
                    print("👋 Goodbye! Your knowledge and memories are safely stored.")
                    break
                elif user_input.lower() == 'clear':
                    self.conversation_history = []
                    print("🗑️ Conversation history cleared.")
                elif user_input.lower() == 'show data':
                    self.show_data()
                elif user_input.lower() == 'show memories':
                    self.show_memories()
                elif user_input.lower() == 'manage data':
                    self.manage_data()
                elif user_input.startswith('ingest '):
                    file_path = user_input[7:].strip()
                    self.ingest_data(file_path)
                elif user_input.startswith('delete '):
                    filename = user_input[7:].strip()
                    self.manager.delete_document(filename)
                elif user_input.startswith('forget '):
                    memory_key = user_input[7:].strip()
                    self.memory_manager.forget(memory_key)
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
        
        # Start interactive chat with memory management features
        brain.interactive_chat_with_memory_management()
        # brain.interactive_chat()
        
    except Exception as e:
        print(f"❌ Failed to initialize The Second Brain: {e}")
        print("\n💡 Troubleshooting tips:")
        print("1. Check your API keys in .env file")
        print("2. Run 'pip install -r requirements.txt'")
        print("3. Ensure you have Python 3.9+ installed")

if __name__ == "__main__":
    main()
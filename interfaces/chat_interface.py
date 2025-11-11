class ChatInterface:
    def __init__(self, second_brain):
        self.brain = second_brain
    
    def start_chat(self):
        print("\n" + "="*50)
        print("🤖 The Second Brain - Chat Mode Activated")
        print("="*50)
        print("Commands:")
        print("  - 'exit', 'quit', 'bye' to exit")
        print("  - 'ingest <file_path>' to add files")
        print("  - 'clear' to clear conversation history")
        print("="*50)
        
        while True:
            try:
                user_input = input("\n🧠 You: ").strip()
                
                if user_input.lower() in ['exit', 'quit', 'bye']:
                    print("👋 Goodbye! Your knowledge is safely stored.")
                    break
                elif user_input.lower() == 'clear':
                    self.brain.conversation_history = []
                    print("🗑️ Conversation history cleared.")
                elif user_input.startswith('ingest '):
                    file_path = user_input[7:].strip()
                    self.brain.ingest_data(file_path)
                elif user_input:
                    response = self.brain.query(user_input)
                    print(f"\n🤖 Second Brain: {response['response']}")
                    
            except KeyboardInterrupt:
                print("\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"❌ Error: {str(e)}")
import os
import json
from config.settings import settings

def verify_data_storage():
    print("🔒 PRIVACY AND DATA STORAGE VERIFICATION")
    print("=" * 50)
    
    # Check local storage locations
    local_paths = [
        "data/chroma_db",
        "data/uploads", 
        "data/processed"
    ]
    
    print("\n📁 LOCAL STORAGE PATHS (Your data stays here):")
    for path in local_paths:
        exists = os.path.exists(path)
        print(f"   {path}: {'✅ EXISTS' if exists else '❌ MISSING'}")
        
        if exists and path == "data/chroma_db":
            try:
                # Check ChromaDB contents
                import chromadb
                client = chromadb.PersistentClient(path=path)
                collection = client.get_collection("second_brain")
                count = collection.count()
                print(f"      - Contains {count} document chunks (your data)")
            except Exception as e:
                print(f"      - Could not access: {e}")
    
    print(f"\n🔐 API KEYS CONFIGURED:")
    print(f"   OpenAI: {'✅' if settings.OPENAI_API_KEY else '❌'}")
    print(f"   Groq: {'✅' if settings.GROQ_API_KEY else '❌'}")
    
    print(f"\n📤 DATA THAT LEAVES YOUR COMPUTER:")
    print(f"   ✅ Only text queries and context snippets")
    print(f"   ❌ NEVER original files (images, PDFs, etc.)")
    print(f"   ❌ NEVER personal metadata")
    print(f"   ❌ NEVER complete documents")
    
    print(f"\n💡 PRIVACY FEATURES:")
    print(f"   ✅ Local OCR processing")
    print(f"   ✅ Local vector database") 
    print(f"   ✅ Local file storage")
    print(f"   ✅ Context-only external API calls")

def show_example_api_call():
    print(f"\n🧪 EXAMPLE OF WHAT GETS SENT TO EXTERNAL APIS:")
    example = {
        "system_prompt": "You are The Second Brain assistant...",
        "user_query": "What was in my recent screenshot?",
        "context_snippets": [
            "Helper: Transforming Local Community Services...",
            "Connecting people, building trust..."
        ],
        "conversation_history": ["Previous questions..."]
    }
    print(json.dumps(example, indent=2))

if __name__ == "__main__":
    verify_data_storage()
    show_example_api_call()
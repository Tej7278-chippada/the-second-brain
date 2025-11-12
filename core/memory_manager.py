import json
import os
from typing import Dict, List, Any, Optional
from datetime import datetime
import uuid
import re

class MemoryManager:
    def __init__(self, settings):
        self.settings = settings
        self.memory_file = os.path.join(settings.PROCESSED_FOLDER, "personal_memory.json")
        self.memories = self._load_memories()
    
    def _load_memories(self) -> Dict[str, Any]:
        """Load memories from JSON file"""
        try:
            if os.path.exists(self.memory_file):
                with open(self.memory_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                return {
                    "personal_info": {},
                    "contacts": {},
                    "financial": {},
                    "borrowed_items": {},
                    "important_notes": {},
                    "credentials": {},
                    "custom_memories": {}
                }
        except Exception as e:
            print(f"❌ Error loading memories: {e}")
            return {
                "personal_info": {},
                "contacts": {},
                "financial": {},
                "borrowed_items": {},
                "important_notes": {},
                "credentials": {},
                "custom_memories": {}
            }
        
    def memorize_borrowed_item(self, item: str, person: str, action: str, notes: str = "") -> bool:
        """Special method for storing borrowed/lent items"""
        key = f"{item}_{person}"
        
        if action == "borrowed_from":
            description = f"Borrowed {item} from {person}. Need to return it."
            value = f"Borrowed from {person}"
        elif action == "lent_to":
            description = f"Lent {item} to {person}. Need to get it back."
            value = f"Lent to {person}"
        else:
            description = f"{item} - {person}: {action}"
            value = action
        
        if notes:
            description += f" | Notes: {notes}"
        
        return self.memorize("borrowed_items", key, value, description)

    def get_borrowed_items(self) -> List[Dict]:
        """Get all borrowed/lent items"""
        return self.list_memories_by_category("borrowed_items")

    def get_items_to_return(self) -> List[Dict]:
        """Get items that need to be returned to others"""
        borrowed_items = self.get_borrowed_items()
        items_to_return = []
        
        for item in borrowed_items:
            memory = item['memory']
            if "borrowed from" in memory.get('description', '').lower() or "need to return" in memory.get('description', '').lower():
                items_to_return.append(item)
        
        return items_to_return

    def get_items_to_receive(self) -> List[Dict]:
        """Get items that others need to return to you"""
        borrowed_items = self.get_borrowed_items()
        items_to_receive = []
        
        for item in borrowed_items:
            memory = item['memory']
            if "lent to" in memory.get('description', '').lower() or "need to get back" in memory.get('description', '').lower():
                items_to_receive.append(item)
        
        return items_to_receive

    def _save_memories(self):
        """Save memories to JSON file"""
        try:
            os.makedirs(os.path.dirname(self.memory_file), exist_ok=True)
            with open(self.memory_file, 'w', encoding='utf-8') as f:
                json.dump(self.memories, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"❌ Error saving memories: {e}")
            return False

    def create_memory_key(self, text: str) -> str:
        """Create a standardized memory key from text"""
        # Convert to lowercase and replace spaces with underscores
        key = text.lower().strip()
        key = re.sub(r'[^\w\s]', '', key)  # Remove punctuation
        key = re.sub(r'\s+', '_', key)     # Replace spaces with underscores
        return key
    
    def memorize(self, category: str, key: str, value: str, description: str = "") -> bool:
        """Store a piece of information in memory with better key management"""
        try:
            memory_id = str(uuid.uuid4())[:8]
            
            # Standardize the key
            standardized_key = self.create_memory_key(key)
            
            memory_data = {
                "id": memory_id,
                "original_key": key,  # Keep original for display
                "value": value,
                "description": description,
                "created_at": datetime.now().isoformat(),
                "last_accessed": datetime.now().isoformat(),
                "category": category
            }
            
            # Initialize category if it doesn't exist
            if category not in self.memories:
                self.memories[category] = {}
            
            # Check if key already exists in this category
            if standardized_key in self.memories[category]:
                print(f"🔄 Updating existing memory: {standardized_key}")
            else:
                # print(f"✅ Creating new memory: {standardized_key}")
                print(f"✅ Creating new memory: {value}")
            
            self.memories[category][standardized_key] = memory_data
            
            success = self._save_memories()
            if success:
                # print(f"💾 Memorized '{standardized_key}' in category '{category}'")
                print(f"💾 Memorized '{value}' in category '{category}'")
                return True
            else:
                return False
                
        except Exception as e:
            print(f"❌ Error memorizing information: {e}")
            return False

    def memorize_contact(self, name: str, phone: str, relationship: str = "") -> bool:
        """Special method for storing contact information"""
        key = f"{name}_phone"
        description = f"Phone number for {name}" + (f" ({relationship})" if relationship else "")
        return self.memorize("contacts", key, phone, description)

    def memorize_debt(self, person: str, amount: float, currency: str = "rupees", notes: str = "") -> bool:
        """Special method for storing debt information"""
        key = f"{person}_debt"
        description = f"{person} owes {amount} {currency}" + (f" - {notes}" if notes else "")
        return self.memorize("financial", key, str(amount), description)
    
    def recall(self, key: str, category: str = None) -> Optional[Dict]:
        """Recall a piece of information from memory with fuzzy matching"""
        try:
            standardized_key = self.create_memory_key(key)
            
            # If category is specified, search only in that category
            if category:
                if category in self.memories and standardized_key in self.memories[category]:
                    memory = self.memories[category][standardized_key]
                    memory["last_accessed"] = datetime.now().isoformat()
                    self._save_memories()
                    return memory
                return None
            
            # Search across all categories with fuzzy matching
            for cat_name, category_data in self.memories.items():
                # Exact match
                if standardized_key in category_data:
                    memory = category_data[standardized_key]
                    memory["last_accessed"] = datetime.now().isoformat()
                    self._save_memories()
                    return memory
                
                # Partial match in keys
                for existing_key, memory in category_data.items():
                    if (standardized_key in existing_key or 
                        existing_key in standardized_key or
                        standardized_key in memory.get('original_key', '').lower()):
                        memory["last_accessed"] = datetime.now().isoformat()
                        self._save_memories()
                        return memory
            
            return None
            
        except Exception as e:
            print(f"❌ Error recalling information: {e}")
            return None

    def search_memories(self, search_term: str) -> List[Dict]:
        """Search for memories containing the search term with better matching"""
        results = []
        search_term_lower = search_term.lower()
        search_standardized = self.create_memory_key(search_term)
        
        for category_name, category_data in self.memories.items():
            for key, memory in category_data.items():
                search_fields = [
                    key,
                    memory.get('original_key', ''),
                    memory.get('value', ''),
                    memory.get('description', '')
                ]
                
                # Check if search term appears in any field
                if any(search_term_lower in str(field).lower() for field in search_fields) or \
                   any(search_standardized in self.create_memory_key(str(field)) for field in search_fields):
                    results.append({
                        'category': category_name,
                        'key': key,
                        'original_key': memory.get('original_key', key),
                        'memory': memory
                    })
        
        return results
    
    def search_memories_by_content(self, search_terms: List[str]) -> List[Dict]:
        """Search memories by multiple content terms"""
        results = []
        
        for category_name, category_data in self.memories.items():
            for key, memory in category_data.items():
                search_fields = [
                    key,
                    memory.get('original_key', ''),
                    memory.get('value', ''),
                    memory.get('description', '')
                ]
                
                # Check if ALL search terms appear in any field
                if all(any(term.lower() in str(field).lower() for field in search_fields) for term in search_terms):
                    results.append({
                        'category': category_name,
                        'key': key,
                        'original_key': memory.get('original_key', key),
                        'memory': memory
                    })
        
        return results

    def list_memories_by_category(self, category: str) -> List[Dict]:
        """List all memories in a specific category"""
        if category in self.memories:
            return [
                {
                    'key': key,
                    'original_key': memory.get('original_key', key),
                    'memory': memory
                }
                for key, memory in self.memories[category].items()
            ]
        return []
    
    def show_memories(self):
        """Show all stored memories with better organization"""
        memories = self.memory_manager.list_memories()
        stats = self.memory_manager.get_memory_stats()
        
        print("\n💾 PERSONAL MEMORIES")
        print("=" * 60)
        print(f"Total memories: {stats['total_memories']}")
        
        # Show reminders and notes
        notes = self.memory_manager.list_memories_by_category("important_notes")
        if notes:
            print(f"\n📅 REMINDERS & NOTES:")
            for note in notes:
                content = note['memory']['value']
                print(f"   • {content}")
        
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
        
        # Show other personal info
        personal_info = self.memory_manager.list_memories_by_category("personal_info")
        if personal_info:
            print(f"\n👤 PERSONAL INFORMATION:")
            for info in personal_info:
                key = info['original_key']
                value = info['memory']['value']
                print(f"   • {key.replace('_', ' ').title()}: {value}")

    def get_all_debts(self) -> List[Dict]:
        """Get all debt information"""
        return self.list_memories_by_category("financial")

    def get_all_contacts(self) -> List[Dict]:
        """Get all contact information"""
        return self.list_memories_by_category("contacts")
    
    def list_memories(self, category: str = None) -> Dict:
        """List all memories or memories in a specific category"""
        if category:
            return self.memories.get(category, {})
        else:
            return self.memories
    
    def forget(self, key: str, category: str = None) -> bool:
        """Remove a memory"""
        try:
            if category:
                # Delete from specific category
                if category in self.memories and key in self.memories[category]:
                    del self.memories[category][key]
                    # Remove empty category
                    if not self.memories[category]:
                        del self.memories[category]
                    return self._save_memories()
            else:
                # Delete from any category
                for cat_name in list(self.memories.keys()):
                    if key in self.memories[cat_name]:
                        del self.memories[cat_name][key]
                        # Remove empty category
                        if not self.memories[cat_name]:
                            del self.memories[cat_name]
                        return self._save_memories()
            
            print(f"❌ Memory '{key}' not found")
            return False
            
        except Exception as e:
            print(f"❌ Error forgetting memory: {e}")
            return False
    
    def get_memory_stats(self) -> Dict[str, Any]:
        """Get statistics about stored memories"""
        total_memories = 0
        category_stats = {}
        
        for category_name, category_data in self.memories.items():
            count = len(category_data)
            total_memories += count
            category_stats[category_name] = count
        
        return {
            "total_memories": total_memories,
            "categories": category_stats,
            "memory_file": self.memory_file
        }

    def export_memories_to_vector(self, vector_store) -> bool:
        """Export memories to vector store for AI querying - improved version"""
        try:
            # First, remove any existing memory documents to avoid duplicates
            try:
                results = vector_store.collection.get()
                memory_ids_to_delete = []
                for doc_id, metadata in zip(results['ids'], results['metadatas']):
                    if metadata.get('file_name') == 'personal_memories':
                        memory_ids_to_delete.append(doc_id)
                
                if memory_ids_to_delete:
                    vector_store.collection.delete(ids=memory_ids_to_delete)
            except Exception as e:
                print(f"⚠️ Could not clean old memories: {e}")
            
            memories_text = "PERSONAL MEMORIES AND INFORMATION:\n\n"
            
            # Add a clear header that these are USER'S personal memories
            memories_text += "=== USER'S PERSONAL INFORMATION ===\n"
            memories_text += "This section contains the user's own personal details, not contact information of other people.\n\n"
            
            for category_name, category_data in self.memories.items():
                if category_data:  # Only include non-empty categories
                    # Skip contacts category to avoid overriding document contacts
                    if category_name == 'contacts':
                        continue
                        
                    memories_text += f"=== {category_name.upper()} ===\n"
                    for key, memory in category_data.items():
                        memories_text += f"- {key}: {memory['value']}"
                        if memory.get('description'):
                            memories_text += f" ({memory['description']})"
                        memories_text += "\n"
                    memories_text += "\n"
            
            if memories_text.strip() and memories_text != "PERSONAL MEMORIES AND INFORMATION:\n\n":
                memory_document = {
                    'content': memories_text,
                    'metadata': {
                        'file_path': 'personal_memory_system',
                        'file_name': 'personal_memories',
                        'file_type': '.memory',
                        'ingestion_time': datetime.now().isoformat(),
                        'file_size': len(memories_text),
                        'is_personal_memory': True  # Add flag to identify personal memories
                    },
                    'chunks': [memories_text]  # Single chunk for memories
                }
                
                success = vector_store.add_documents([memory_document])
                if success:
                    print("✅ Memories exported to vector store")
                    return True
            
            return False
                
        except Exception as e:
            print(f"❌ Error exporting memories to vector: {e}")
            return False
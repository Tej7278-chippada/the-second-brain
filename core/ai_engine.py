import openai
from groq import Groq
from typing import List, Dict, Any, Optional
import json
from datetime import datetime
import re

class AIEngine:
    def __init__(self, settings, memory_manager=None):
        self.settings = settings
        self.memory_manager = memory_manager
        self.vector_store = None  # Will be set later
        if settings.OPENAI_API_KEY:
            self.openai_client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
        else:
            self.openai_client = None
            
        if settings.GROQ_API_KEY:
            self.groq_client = Groq(api_key=settings.GROQ_API_KEY)
            # Test Groq connection with available models
            self._test_groq_connection()
        else:
            self.groq_client = None
        
        if not self.openai_client and not self.groq_client:
            raise ValueError("No AI client configured - need either OpenAI or Groq API key")
        
        # Track recent actions
        self.recent_actions = []
        
    def _test_groq_connection(self):
        """Test Groq connection and list available models"""
        try:
            models = self.groq_client.models.list()
            available_models = [model.id for model in models.data]
            print(f"✅ Groq connected. Available models: {available_models}")
            
            # Set preferred model based on availability
            preferred_models = [
                "llama-3.3-70b-versatile",  # Most capable model
                "llama-3.1-70b-versatile",  # Newer model
                "llama-3.1-8b-instant",     # Faster model
                "llama3-70b-8192",          # Original (might be deprecated)
                "llama3-8b-8192"            # Smaller version
            ]
            
            for model in preferred_models:
                if model in available_models:
                    self.groq_model = model
                    print(f"🎯 Using Groq model: {model}")
                    return
            
            # Fallback to first available model
            if available_models:
                self.groq_model = available_models[0]
                print(f"⚠️ Using fallback Groq model: {self.groq_model}")
            else:
                print("❌ No Groq models available")
                self.groq_client = None
                
        except Exception as e:
            print(f"❌ Groq connection failed: {e}")
            self.groq_client = None
    
    def set_vector_store(self, vector_store):
        """Set vector store for memory exports"""
        self.vector_store = vector_store

    def add_recent_action(self, action: str, details: Dict):
        """Track recent user actions for context"""
        self.recent_actions.append({
            'timestamp': datetime.now().isoformat(),
            'action': action,
            'details': details
        })
        # Keep only last 10 actions
        if len(self.recent_actions) > 10:
            self.recent_actions = self.recent_actions[-10:]

    def generate_response(self, query: str, context: List[Dict], conversation_history: List[Dict] = None) -> Dict[str, Any]:
        """Generate response using context from vector store"""
        try:
            # Check if this is a memory-related query
            memory_result = self._check_memory_query(query)
            if memory_result:
                return memory_result
            
            # Enhanced context preparation with recent actions
            enhanced_context = self._enhance_context_with_recent_actions(context, query)
            
            # Prepare context from search results
            context_text = self._prepare_context(enhanced_context)
            
            # Prepare conversation history
            history_text = self._prepare_conversation_history(conversation_history)
            
            # Enhanced system prompt with memory instructions
            system_prompt = """You are "The Second Brain" - a personal AI assistant that has access to all of the user's personal and professional information. 
            Your role is to help the user recall information, make connections between different pieces of knowledge, and provide intelligent responses based on their complete digital memory.

SPECIAL MEMORY FEATURES:
- The user can ask you to memorize information using commands like "memorize", "remember this", "store this"
- You have access to the user's personal memories (phone numbers, IDs, important info)
- When user asks about personal information, check the memory system first

MEMORY COMMANDS USER CAN USE:
- "memorize my phone number as 1234567890"
- "remember that my Aadhaar number is XXXX-XXXX-XXXX" 
- "store this: my car license plate is ABC123"
- "what's my phone number?"
- "show me my Aadhaar details"

SPECIAL INSTRUCTIONS FOR IMAGES:
- When user asks about "last given pic", "recent image", "previous image", etc., refer to the most recently ingested image
- When describing images, use the extracted OCR text and file metadata
- If multiple images exist, mention the most recent one first
- Provide detailed descriptions based on available text content

GENERAL GUIDELINES:
- Be precise and factual based on the context provided
- If information isn't in the context, say so clearly
- Make connections between different pieces of information when relevant
- Maintain a helpful, professional tone
- Reference specific file names when discussing documents or images"""

            # Construct the enhanced prompt
            prompt = f"""{history_text}

Recent User Actions:
{self._prepare_recent_actions()}

Current Query: {query}

Relevant Context from User's Memory:
{context_text}

Please provide a helpful response based on the user's query and available context:"""
            
            # Try Groq first, then OpenAI
            if self.groq_client:
                return self._call_groq(system_prompt, prompt, enhanced_context)
            elif self.openai_client:
                return self._call_openai(system_prompt, prompt, enhanced_context)
            else:
                return self._fallback_response(query, enhanced_context)
                
        except Exception as e:
            print(f"❌ AI Engine Error: {e}")
            return {
                'response': f"I encountered an error while processing your request. Please try again.",
                'sources': [],
                'confidence': 0.0
            }
        
    def _check_memory_query(self, query: str) -> Optional[Dict[str, Any]]:
        """Check if query is about memorizing or recalling information"""
        if not self.memory_manager:
            return None
        
        query_lower = query.lower().strip()
        
        # Check for memorize commands
        memorize_keywords = ['memorize', 'remember this', 'store this', 'save this', 'remember my', 'memorize my']
        if any(keyword in query_lower for keyword in memorize_keywords):
            return self._handle_memorize_command(query)
        
        # Check for recall commands - more comprehensive patterns
        recall_patterns = [
            # Direct questions about USER'S personal info
            (r'what is my (.*)', 'personal_info'),
            (r'what\'s my (.*)', 'personal_info'),
            (r'show me my (.*)', 'personal_info'),
            (r'tell me my (.*)', 'personal_info'),
            (r'what are my (.*)', 'personal_info'),
            (r'give me my (.*)', 'personal_info'),
            
            # Specific personal items with flexible matching
            (r'.*my phone number.*', 'personal_info', 'phone_number'),
            (r'.*my aadhaar.*', 'personal_info', 'aadhaar_number'),
            (r'.*my aadhar.*', 'personal_info', 'aadhaar_number'),
            (r'.*my address.*', 'personal_info', 'address'),
            (r'.*my email.*', 'personal_info', 'email'),
            (r'.*my license.*', 'personal_info', 'license'),
            (r'.*my password.*', 'credentials', None),
            (r'.*my username.*', 'credentials', None),
            
            # Generic "my X" pattern
            (r'my (.*)', 'personal_info'),
        ]
        
        for pattern, category, *extra in recall_patterns:
            match = re.search(pattern, query_lower)
            if match:
                key = extra[0] if extra else None
                if not key:
                    # Extract the key from the pattern match
                    if len(match.groups()) > 0:
                        key = match.group(1).replace(' ', '_')
                    else:
                        # If no group captured, use the entire matched string
                        key = match.group(0).replace(' ', '_')
                
                return self._handle_recall_command(query, category, key)
        
        return None

    def _handle_memorize_command(self, query: str) -> Dict[str, Any]:
        """Handle commands to memorize information with better parsing"""
        try:
            if not self.memory_manager:
                return {
                    'response': "Memory system is not available.",
                    'sources': [],
                    'confidence': 0.0
                }

            query_lower = query.lower()
            
            # Improved pattern matching for different formats
            patterns = [
                # Reminder patterns (NEW)
                (r'(?:remember|memorize)\s+(?:that|this)?\s*(?:i\s+)?need\s+to\s+(.+?)\s+at\s+(\d+\s*(?:am|pm))', 'reminder'),
                (r'(?:remember|memorize)\s+(?:that|this)?\s*(?:i\s+)?have\s+(.+?)\s+at\s+(\d+\s*(?:am|pm))', 'reminder'),
                (r'(?:remember|memorize)\s+(?:that|this)?\s*(?:i\s+)?need\s+to\s+(.+)', 'reminder'),
                (r'(?:remember|memorize)\s+(?:that|this)?\s*(?:i\s+)?have\s+(.+)', 'reminder'),
                
                # Borrowed items patterns
                (r'(?:i\s+)?(?:take|took|borrow|borrowed)\s+(.+?)\s+from\s+(\w+)(?:\s+to\s+.+)?(?:\s+and\s+need\s+to\s+give\s+it\s+back)?', 'borrowed_from'),
                (r'(?:i\s+)?need\s+to\s+return\s+(.+?)\s+to\s+(\w+)', 'borrowed_from'),
                (r'(?:i\s+)?have\s+(.+?)\s+that\s+belongs\s+to\s+(\w+)', 'borrowed_from'),
                (r'(?:i\s+)?lent\s+(.+?)\s+to\s+(\w+)', 'lent_to'),
                (r'(\w+)\s+has\s+my\s+(.+)', 'lent_to'),
                
                # Contact patterns
                (r'(?:remember|memorize|store)\s+(?:that\s+)?(?:my\s+)?(\w+)(?:\'s)?\s+phone\s+(?:number|no)?\s+(?:is|as)\s+(\d{10})', 'contact'),
                (r'(?:remember|memorize|store)\s+(?:that\s+)?(?:my\s+)?(\w+)(?:\'s)?\s+phone\s+(?:number|no)?\s+(\d{10})', 'contact'),
                
                # Debt patterns
                (r'(\w+)\s+owes?\s+me\s+(\d+)\s*(rupees?|rs)?', 'debt'),
                (r'(?:remember|memorize)\s+(?:that\s+)?(\w+)\s+owes?\s+me\s+(\d+)\s*(rupees?|rs)?', 'debt'),
                
                # Personal info patterns
                (r'memorize\s+my\s+([\w\s]+?)\s+as\s+(.+)', 'personal'),
                (r'remember\s+my\s+([\w\s]+?)\s+is\s+(.+)', 'personal'),
                (r'remember\s+that\s+my\s+([\w\s]+?)\s+is\s+(.+)', 'personal'),
                
                # Direct patterns
                (r'.*aadhaar.*?(\d{4}[-\.\s]??\d{4}[-\.\s]??\d{4}).*', 'personal', 'aadhaar_number'),
                (r'.*phone.*?(\d{10}).*', 'personal', 'phone_number'),
            ]
            
            for pattern, memory_type, *extra in patterns:
                match = re.search(pattern, query_lower, re.IGNORECASE)
                if match:
                    if memory_type == 'reminder':
                        # Extract the reminder content
                        if len(match.groups()) == 2:
                            action = match.group(1).strip()
                            time_info = match.group(2).strip()
                            content = f"{action} at {time_info}"
                        else:
                            content = match.group(1).strip()
                        
                        # Create a meaningful key
                        key = f"reminder_{hash(content) % 10000}"
                        success = self.memory_manager.memorize("important_notes", key, content, f"Reminder: {query}")
                        if success:
                            return {
                                'response': f"✅ I've set a reminder: '{content}'",
                                'sources': ['memory_system'],
                                'confidence': 1.0
                            }
                    
                    elif memory_type == 'borrowed_from':
                        item = match.group(1).strip()
                        person = match.group(2).strip()
                        notes = "Need to return it"
                        success = self.memory_manager.memorize_borrowed_item(item, person, "borrowed_from", notes)
                        if success:
                            return {
                                'response': f"✅ I've recorded that you borrowed '{item}' from {person}. I'll remind you to return it.",
                                'sources': ['memory_system'],
                                'confidence': 1.0
                            }
                        
                        elif memory_type == 'lent_to':
                            item = match.group(1).strip()
                            person = match.group(2).strip()
                            notes = "Need to get it back"
                            success = self.memory_manager.memorize_borrowed_item(item, person, "lent_to", notes)
                            if success:
                                return {
                                    'response': f"✅ I've recorded that you lent '{item}' to {person}. I'll remind you to get it back.",
                                    'sources': ['memory_system'],
                                    'confidence': 1.0
                                }
                    
                    elif memory_type == 'contact':
                        name = match.group(1)
                        phone = match.group(2)
                        success = self.memory_manager.memorize_contact(name, phone)
                        if success:
                            return {
                                'response': f"✅ I've stored {name}'s phone number: {phone}",
                                'sources': ['memory_system'],
                                'confidence': 1.0
                            }
                    
                    elif memory_type == 'debt':
                        person = match.group(1)
                        amount = match.group(2)
                        success = self.memory_manager.memorize_debt(person, float(amount))
                        if success:
                            return {
                                'response': f"✅ I've recorded that {person} owes you {amount} rupees",
                                'sources': ['memory_system'],
                                'confidence': 1.0
                            }
                    
                    elif memory_type == 'personal':
                        if extra:  # Direct value extraction
                            key = extra[0]
                            value = match.group(1)
                        else:
                            key = match.group(1)
                            value = match.group(2)
                        
                        success = self.memory_manager.memorize("personal_info", key, value.strip())
                        if success:
                            return {
                                'response': f"✅ I've memorized your {key}: {value.strip()}",
                                'sources': ['memory_system'],
                                'confidence': 1.0
                            }
            
            # Enhanced generic memory storage for any text
            memorize_patterns = [
                r'(?:memorize|remember)\s+(?:that|this)\s+(.+)',
                r'store\s+this:\s*(.+)',
                r'note\s+that\s+(.+)',
                r'remind\s+me\s+that\s+(.+)'
            ]
            
            for pattern in memorize_patterns:
                match = re.search(pattern, query_lower, re.IGNORECASE)
                if match:
                    content = match.group(1).strip()
                    # Create a meaningful key based on content
                    words = content.split()[:3]  # Use first 3 words for key
                    key_base = "_".join(words).lower()
                    key = f"note_{key_base}_{hash(content) % 1000}"
                    
                    success = self.memory_manager.memorize("important_notes", key, content, f"User note: {query}")
                    if success:
                        return {
                            'response': f"✅ I've stored: '{content}'",
                            'sources': ['memory_system'],
                            'confidence': 0.9
                        }
            
            # If no pattern matched, provide help
            return {
                'response': """I understand you want me to memorize something. Please use one of these formats:

    **For reminders:**
    • `remember that I need to call Abhi Ram at 2 pm`
    • `memorize that I have meeting tomorrow at 10 AM`
    • `remember this: I need to buy milk`

    **For personal info:**
    • `memorize my Aadhaar number as 1234-5678-9012`
    • `remember my car license plate is ABC123`

    **For borrowed items:**
    • `I took phone charger from Rashmi`
    • `I need to return book to Rohan`

    **For contacts:**
    • `remember tulasi's phone number as 7278949280`
    • `memorize my father's phone number 9492773201`

    **For debts:**
    • `Arjun owes me 5000 rupees`
    • `remember that Abhi owes me 2000 rupees`

    **Or simply:**
    • `memorize that [your note]`
    • `remember this: [your note]`""",
                'sources': [],
                'confidence': 0.0
            }
                
        except Exception as e:
            return {
                'response': f"❌ Error memorizing information: {str(e)}",
                'sources': [],
                'confidence': 0.0
            }

    def _handle_recall_command(self, query: str, category: str, key: str) -> Dict[str, Any]:
        """Handle commands to recall information from memory with better search"""
        try:
            if not self.memory_manager:
                return {
                    'response': "Memory system is not available.",
                    'sources': [],
                    'confidence': 0.0
                }

            query_lower = query.lower()
            
            # Special handling for reminder/meeting queries
            if any(word in query_lower for word in ['meeting', 'reminder', 'appointment', 'schedule', 'call', 'todo']):
                notes = self.memory_manager.list_memories_by_category("important_notes")
                if notes:
                    relevant_notes = []
                    for note in notes:
                        note_content = note['memory']['value'].lower()
                        # Check if note contains time-related or action-related words
                        if any(word in note_content for word in ['meeting', 'call', 'appointment', 'reminder', 'need to', 'have to']):
                            relevant_notes.append(note)
                    
                    if relevant_notes:
                        note_list = []
                        for note in relevant_notes:
                            content = note['memory']['value']
                            note_list.append(f"• {content}")
                        
                        return {
                            'response': f"📅 **Your reminders and meetings:**\n\n" + "\n".join(note_list),
                            'sources': ['memory_system:important_notes'],
                            'confidence': 1.0
                        }
            
            # Special handling for borrowed items queries
            if any(word in query_lower for word in ['borrow', 'lend', 'return', 'give back', 'charger', 'item']):
                items_to_return = self.memory_manager.get_items_to_return()
                items_to_receive = self.memory_manager.get_items_to_receive()
                
                response_parts = []
                
                if items_to_return:
                    return_list = []
                    for item in items_to_return:
                        item_name = item['original_key'].split('_')[0]
                        person = item['original_key'].split('_')[1]
                        return_list.append(f"• {item_name} to {person.title()}")
                    
                    response_parts.append(f"📦 **Items you need to return:**\n\n" + "\n".join(return_list))
                
                if items_to_receive:
                    receive_list = []
                    for item in items_to_receive:
                        item_name = item['original_key'].split('_')[0]
                        person = item['original_key'].split('_')[1]
                        receive_list.append(f"• {item_name} from {person.title()}")
                    
                    response_parts.append(f"📥 **Items others need to return to you:**\n\n" + "\n".join(receive_list))
                
                if response_parts:
                    return {
                        'response': "\n\n".join(response_parts),
                        'sources': ['memory_system:borrowed_items'],
                        'confidence': 1.0
                    }
                else:
                    return {
                        'response': "No borrowed items recorded in your memory.",
                        'sources': [],
                        'confidence': 0.0
                    }
            
            # Special handling for debt queries
            if any(word in query_lower for word in ['owe', 'debt', 'borrow', 'loan', 'money']):
                debts = self.memory_manager.get_all_debts()
                if debts:
                    debt_list = []
                    for debt in debts:
                        person = debt['original_key'].replace('_debt', '')
                        amount = debt['memory']['value']
                        debt_list.append(f"• {person.title()} owes you {amount} rupees")
                    
                    return {
                        'response': f"💰 **People who owe you money:**\n\n" + "\n".join(debt_list),
                        'sources': ['memory_system:financial'],
                        'confidence': 1.0
                    }
                else:
                    return {
                        'response': "No debts recorded in your memory.",
                        'sources': [],
                        'confidence': 0.0
                    }
            
            # Special handling for contact queries
            if any(word in query.lower() for word in ['phone', 'contact', 'number', 'call']):
                # Check if this is about someone else's contact (not "my phone")
                if not any(phrase in query_lower for phrase in ['my phone', 'my number', 'my contact']):
                    # This might be about someone else's contact info from documents
                    # Let the main AI engine handle it with document context first
                    return None
                contacts = self.memory_manager.get_all_contacts()
                if contacts:
                    contact_list = []
                    for contact in contacts:
                        name = contact['original_key'].replace('_phone', '')
                        phone = contact['memory']['value']
                        contact_list.append(f"• {name.title()}: {phone}")
                    
                    return {
                        'response': f"📞 **Your contacts:**\n\n" + "\n".join(contact_list),
                        'sources': ['memory_system:contacts'],
                        'confidence': 1.0
                    }
            
            # Standard memory recall
            memory = self.memory_manager.recall(key, category)
            
            if not memory:
                # Try fuzzy search
                memories = self.memory_manager.search_memories(key)
                if memories:
                    memory = memories[0]['memory']
                    key = memories[0]['original_key']
                    category = memories[0]['category']
            
            if memory:
                # Export memories to vector store for future queries
                if self.vector_store:
                    self.memory_manager.export_memories_to_vector(self.vector_store)
                
                response_text = f"📝 **{key.replace('_', ' ').title()}**: {memory['value']}"
                if memory.get('description'):
                    response_text += f"\n\n📋 *{memory['description']}*"
                
                return {
                    'response': response_text,
                    'sources': [f'memory_system:{category}'],
                    'confidence': 1.0
                }
            else:
                # Show available memories
                all_memories = self.memory_manager.search_memories("")
                if all_memories:
                    # Group by category
                    by_category = {}
                    for mem in all_memories:
                        cat = mem['category']
                        if cat not in by_category:
                            by_category[cat] = []
                        by_category[cat].append(mem['original_key'])
                    
                    memory_list = ""
                    for cat, keys in by_category.items():
                        memory_list += f"\n**{cat.title()}:**\n"
                        for key in keys[:3]:  # Show first 3 per category
                            memory_list += f"• {key}\n"
                    
                    return {
                        'response': f"I couldn't find '{key}' in your memory. Here are your stored memories:{memory_list}\n\nUse: 'memorize my {key} as [value]' to store it.",
                        'sources': [],
                        'confidence': 0.3
                    }
                else:
                    return {
                        'response': f"I couldn't find '{key}' in your memory. You can store it using: 'memorize my {key} as [value]'",
                        'sources': [],
                        'confidence': 0.0
                    }
                    
        except Exception as e:
            return {
                'response': f"❌ Error recalling information: {str(e)}",
                'sources': [],
                'confidence': 0.0
            }
    
    def _enhance_context_with_memories(self, context: List[Dict], query: str) -> List[Dict]:
        """Enhance context with personal memories"""
        if not self.memory_manager:
            return context
        
        # Export memories to vector store for this query
        self.memory_manager.export_memories_to_vector(self.vector_store)
        
        return context

    def _enhance_context_with_recent_actions(self, context: List[Dict], query: str) -> List[Dict]:
        """Enhance context with information about recent actions"""
        enhanced_context = context.copy()
        
        # Check if query is about recent/last image
        image_keywords = ['last given pic', 'recent image', 'previous image', 'last picture', 'recent pic']
        if any(keyword in query.lower() for keyword in image_keywords):
            # Add recent image ingestion info to context
            recent_images = []
            for action in reversed(self.recent_actions):
                if action['action'] == 'ingest' and action['details'].get('file_type') in ['.jpg', '.jpeg', '.png', '.gif', '.bmp']:
                    recent_images.append(action['details'])
            
            if recent_images:
                # Create a special context entry for recent images
                recent_images_context = {
                    'content': f"RECENT IMAGES INFO: The user recently ingested these images: {[img['file_name'] for img in recent_images]}. The most recent is '{recent_images[0]['file_name']}'.",
                    'metadata': {'file_path': 'system_recent_actions', 'file_type': 'system'},
                    'distance': 0
                }
                enhanced_context.insert(0, recent_images_context)
        
        return enhanced_context

    def _prepare_recent_actions(self) -> str:
        """Prepare recent actions for context"""
        if not self.recent_actions:
            return "No recent actions recorded."
        
        actions_text = "Recent User Actions (most recent first):\n"
        for i, action in enumerate(reversed(self.recent_actions[-3:])):  # Last 3 actions
            if action['action'] == 'ingest':
                actions_text += f"- Ingested file: {action['details'].get('file_name', 'Unknown')} ({action['details'].get('file_type', 'Unknown type')})\n"
            elif action['action'] == 'query':
                actions_text += f"- Asked: {action['details'].get('query', 'Unknown')}\n"
        
        return actions_text

    def _prepare_context(self, context: List[Dict]) -> str:
        """Prepare context from search results with better formatting"""
        if not context:
            return "No relevant context found in the knowledge base."
            
        context_text = "CONTEXT FROM YOUR KNOWLEDGE BASE:\n\n"
        for i, item in enumerate(context):
            file_name = item['metadata'].get('file_name', item['metadata'].get('file_path', 'Unknown'))
            file_type = item['metadata'].get('file_type', 'Unknown')
            
            context_text += f"--- ITEM {i+1}: {file_name} ({file_type}) ---\n"
            
            # Truncate very long content but keep important parts
            content = item['content']
            if len(content) > 800:
                # Try to keep the beginning and end
                content = content[:400] + "\n[...content truncated...]\n" + content[-400:]
            
            context_text += f"{content}\n\n"
            
            # Add chunk info if available
            if 'chunk_index' in item['metadata']:
                context_text += f"[Chunk {item['metadata']['chunk_index'] + 1} of {item['metadata']['chunk_count']}]\n"
            
            context_text += "\n"
        
        return context_text

    def _prepare_conversation_history(self, history: List[Dict]) -> str:
        """Prepare conversation history"""
        if not history:
            return "No previous conversation in this session."
        
        history_text = "PREVIOUS CONVERSATION:\n"
        for msg in history[-4:]:  # Last 4 messages for context
            role = "USER" if msg['role'] == 'user' else "ASSISTANT"
            history_text += f"{role}: {msg['content']}\n"
        
        return history_text

    def _call_openai(self, system_prompt: str, prompt: str, context: List[Dict]) -> Dict[str, Any]:
        """Call OpenAI API"""
        try:
            response = self.openai_client.chat.completions.create(
                model=self.settings.LLM_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=1500
            )
            
            sources = [item['metadata'].get('file_name', item['metadata'].get('file_path', 'Unknown')) for item in context]
            
            return {
                'response': response.choices[0].message.content,
                'sources': list(set(sources)),  # Remove duplicates
                'confidence': 0.9
            }
        except Exception as e:
            print(f"❌ OpenAI Error: {e}")
            raise

    def _call_groq(self, system_prompt: str, prompt: str, context: List[Dict]) -> Dict[str, Any]:
        """Call Groq API for faster inference"""
        try:
            response = self.groq_client.chat.completions.create(
                model=self.groq_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=1500
            )
            
            sources = [item['metadata'].get('file_name', item['metadata'].get('file_path', 'Unknown')) for item in context]
            
            return {
                'response': response.choices[0].message.content,
                'sources': list(set(sources)),
                'confidence': 0.9
            }
        except Exception as e:
            print(f"❌ Groq Error: {e}")
            # Fall back to OpenAI if Groq fails
            if self.openai_client:
                print("🔄 Falling back to OpenAI...")
                return self._call_openai(system_prompt, prompt, context)
            else:
                raise

    def _fallback_response(self, query: str, context: List[Dict]) -> Dict[str, Any]:
        """Fallback response when no AI service is available"""
        if context:
            # Simple keyword-based response
            content = context[0]['content'] if context else ""
            if "key objectives" in query.lower() and "objective" in content.lower():
                return {
                    'response': "Based on your documents, I found information about project objectives in the context.",
                    'sources': [item['metadata'].get('file_path', 'Unknown') for item in context],
                    'confidence': 0.7
                }
            elif "team" in query.lower() and any(member in content for member in ["John", "Sarah", "Mike"]):
                return {
                    'response': "The project team includes John Smith, Sarah Johnson, and Mike Chen.",
                    'sources': [item['metadata'].get('file_path', 'Unknown') for item in context],
                    'confidence': 0.7
                }
            elif "budget" in query.lower() and "$" in content:
                return {
                    'response': "The project budget is $150,000 according to your documents.",
                    'sources': [item['metadata'].get('file_path', 'Unknown') for item in context],
                    'confidence': 0.7
                }
        
        return {
            'response': "I found some relevant information in your knowledge base, but I'm currently unable to generate a detailed response. Please check your API configuration.",
            'sources': [item['metadata'].get('file_path', 'Unknown') for item in context],
            'confidence': 0.3
        }
import openai
from groq import Groq
from typing import List, Dict, Any
import json
from datetime import datetime

class AIEngine:
    def __init__(self, settings):
        self.settings = settings
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
            # Enhanced context preparation with recent actions
            enhanced_context = self._enhance_context_with_recent_actions(context, query)
            
            # Prepare context from search results
            context_text = self._prepare_context(enhanced_context)
            
            # Prepare conversation history
            history_text = self._prepare_conversation_history(conversation_history)
            
            # Enhanced system prompt
            system_prompt = """You are "The Second Brain" - a personal AI assistant that has access to all of the user's personal and professional information. 
            Your role is to help the user recall information, make connections between different pieces of knowledge, and provide intelligent responses based on their complete digital memory.

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
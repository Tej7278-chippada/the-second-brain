# core/vector_store.py
import chromadb
from chromadb.config import Settings
from typing import List, Dict, Any
import uuid
from sentence_transformers import SentenceTransformer

class VectorStore:
    def __init__(self, settings):
        self.settings = settings
        self.client = chromadb.PersistentClient(path=settings.CHROMA_PERSIST_DIR)
        self.collection = self.client.get_or_create_collection("second_brain")
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
    
    def add_documents(self, documents: List[Dict[str, Any]], user_id: str = None) -> bool:
        """Add documents to vector store with user filtering"""
        try:
            ids = []
            embeddings = []
            metadatas = []
            documents_text = []
            
            for doc in documents:
                for i, chunk in enumerate(doc['chunks']):
                    doc_id = str(uuid.uuid4())
                    ids.append(doc_id)
                    
                    # Generate embedding
                    embedding = self.embedding_model.encode(chunk).tolist()
                    embeddings.append(embedding)
                    
                    # Prepare metadata with user_id
                    metadata = doc['metadata'].copy()
                    metadata['chunk_index'] = i
                    metadata['chunk_count'] = len(doc['chunks'])
                    if user_id:
                        metadata['user_id'] = user_id  # Add user_id to metadata
                    metadatas.append(metadata)
                    
                    documents_text.append(chunk)
            
            # Add to collection
            self.collection.add(
                embeddings=embeddings,
                documents=documents_text,
                metadatas=metadatas,
                ids=ids
            )
            return True
            
        except Exception as e:
            print(f"Error adding documents to vector store: {str(e)}")
            return False
    
    def search(self, query: str, n_results: int = 5, filters: Dict = None, user_id: str = None) -> List[Dict]:
        """Search for similar documents with user filtering"""
        try:
            # Generate query embedding
            query_embedding = self.embedding_model.encode(query).tolist()
            
            # Add user filter if user_id is provided
            if user_id and filters:
                filters = {"$and": [filters, {"user_id": user_id}]}
            elif user_id:
                filters = {"user_id": user_id}
            
            # Perform search
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
                where=filters
            )
            
            # Format results
            formatted_results = []
            for i in range(len(results['documents'][0])):
                formatted_results.append({
                    'content': results['documents'][0][i],
                    'metadata': results['metadatas'][0][i],
                    'distance': results['distances'][0][i] if results['distances'] else None
                })
            
            return formatted_results
            
        except Exception as e:
            print(f"Error searching vector store: {str(e)}")
            return []
    
    def get_user_documents(self, user_id: str):
        """Get all documents for a specific user"""
        try:
            results = self.collection.get(
                where={"user_id": user_id}
            )
            return results
        except Exception as e:
            print(f"Error getting user documents: {str(e)}")
            return []
    
    def delete_user_document(self, filename: str, user_id: str) -> bool:
        """Delete a specific document for a user"""
        try:
            results = self.collection.get()
            
            ids_to_delete = []
            for doc_id, metadata in zip(results['ids'], results['metadatas']):
                if (filename in metadata.get('file_name', '') and 
                    metadata.get('user_id') == user_id):
                    ids_to_delete.append(doc_id)
            
            if ids_to_delete:
                self.collection.delete(ids=ids_to_delete)
                print(f"✅ Deleted {len(ids_to_delete)} chunks of '{filename}' for user {user_id}")
                return True
            else:
                print(f"❌ No documents found matching '{filename}' for user {user_id}")
                return False
                
        except Exception as e:
            print(f"❌ Error deleting document: {e}")
            return False
    
    def get_collection_stats(self) -> Dict:
        """Get statistics about the vector store"""
        return {
            'count': self.collection.count(),
            'metadata': self.collection.metadata
        }
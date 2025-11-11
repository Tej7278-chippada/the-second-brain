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
    
    def add_documents(self, documents: List[Dict[str, Any]]) -> bool:
        """Add documents to vector store"""
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
                    
                    # Prepare metadata
                    metadata = doc['metadata'].copy()
                    metadata['chunk_index'] = i
                    metadata['chunk_count'] = len(doc['chunks'])
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
    
    def search(self, query: str, n_results: int = 5, filters: Dict = None) -> List[Dict]:
        """Search for similar documents"""
        try:
            # Generate query embedding
            query_embedding = self.embedding_model.encode(query).tolist()
            
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
    
    def get_collection_stats(self) -> Dict:
        """Get statistics about the vector store"""
        return {
            'count': self.collection.count(),
            'metadata': self.collection.metadata
        }
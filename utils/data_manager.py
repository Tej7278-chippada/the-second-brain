# utils/data_manager.py
import os
import chromadb
from typing import List, Dict, Any
import uuid

class DataManager:
    def __init__(self, vector_store, data_ingestor):
        self.vector_store = vector_store
        self.data_ingestor = data_ingestor
    
    def delete_document(self, filename: str) -> bool:
        """Delete all chunks of a specific document"""
        try:
            # Get all documents to find matching ones
            results = self.vector_store.collection.get()
            
            ids_to_delete = []
            for doc_id, metadata in zip(results['ids'], results['metadatas']):
                if (filename in metadata.get('file_name', '') or 
                    filename in metadata.get('file_path', '')):
                    ids_to_delete.append(doc_id)
            
            if ids_to_delete:
                self.vector_store.collection.delete(ids=ids_to_delete)
                print(f"✅ Deleted {len(ids_to_delete)} chunks of '{filename}'")
                return True
            else:
                print(f"❌ No documents found matching '{filename}'")
                return False
                
        except Exception as e:
            print(f"❌ Error deleting document: {e}")
            return False
    
    def delete_all_documents(self) -> bool:
        """Delete all documents (reset the knowledge base)"""
        try:
            confirmation = input("⚠️  Are you sure you want to delete ALL documents? (yes/no): ")
            if confirmation.lower() == 'yes':
                # ChromaDB doesn't have a direct "delete all", so we get all and delete
                results = self.vector_store.collection.get()
                if results['ids']:
                    self.vector_store.collection.delete(ids=results['ids'])
                    print("✅ All documents deleted successfully")
                else:
                    print("ℹ️  No documents to delete")
                return True
            else:
                print("❌ Deletion cancelled")
                return False
        except Exception as e:
            print(f"❌ Error deleting all documents: {e}")
            return False
    
    def update_document(self, file_path: str) -> bool:
        """Update a document by re-ingesting it"""
        try:
            # First delete the old version
            filename = os.path.basename(file_path)
            self.delete_document(filename)
            
            # Then re-ingest
            result = self.data_ingestor.ingest_file(file_path)
            if result:
                success = self.vector_store.add_documents([result])
                if success:
                    print(f"✅ Successfully updated: {filename}")
                    return True
            return False
        except Exception as e:
            print(f"❌ Error updating document: {e}")
            return False
    
    def show_document_details(self, filename: str):
        """Show detailed information about a specific document"""
        results = self.vector_store.collection.get()
        
        matching_chunks = []
        for doc_id, document, metadata in zip(results['ids'], results['documents'], results['metadatas']):
            if (filename in metadata.get('file_name', '') or 
                filename in metadata.get('file_path', '')):
                matching_chunks.append({
                    'chunk_id': doc_id,
                    'content_preview': document[:100] + '...',
                    'chunk_number': metadata.get('chunk_index', 0) + 1,
                    'total_chunks': metadata.get('chunk_count', 1),
                    'file_size': metadata.get('file_size', 'Unknown'),
                    'ingestion_time': metadata.get('ingestion_time', 'Unknown')
                })
        
        if matching_chunks:
            print(f"\n📄 DOCUMENT DETAILS: {filename}")
            print("=" * 50)
            print(f"Total chunks: {len(matching_chunks)}")
            
            # Sort by chunk number
            matching_chunks.sort(key=lambda x: x['chunk_number'])
            
            for chunk in matching_chunks:
                print(f"\nChunk {chunk['chunk_number']}/{chunk['total_chunks']}:")
                print(f"  Content: {chunk['content_preview']}")
                print(f"  Ingested: {chunk['ingestion_time']}")
        else:
            print(f"❌ No document found with name: {filename}")
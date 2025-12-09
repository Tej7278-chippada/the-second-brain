# utils/data_visualizer.py
import os
import json
from typing import List, Dict, Any
from datetime import datetime
import pandas as pd
from chromadb.config import Settings
import chromadb

class DataVisualizer:
    def __init__(self, vector_store):
        self.vector_store = vector_store
    
    def show_all_documents(self, user_id: str = None) -> List[Dict]:
        """Show all ingested documents with statistics for a specific user"""
        try:
            # Get all documents from ChromaDB with optional user filter
            if user_id:
                results = self.vector_store.collection.get(where={"user_id": user_id})
            else:
                results = self.vector_store.collection.get()
            
            documents = []
            if results['documents']:
                for i, (doc_id, document, metadata) in enumerate(zip(
                    results['ids'], 
                    results['documents'], 
                    results['metadatas']
                )):
                    documents.append({
                        'id': doc_id,
                        'content_preview': document[:200] + '...' if len(document) > 200 else document,
                        'file_name': metadata.get('file_name', metadata.get('file_path', 'Unknown')),
                        'file_type': metadata.get('file_type', 'Unknown'),
                        'file_size': metadata.get('file_size', 'Unknown'),
                        'ingestion_time': metadata.get('ingestion_time', 'Unknown'),
                        'chunk_index': metadata.get('chunk_index', 0),
                        'total_chunks': metadata.get('chunk_count', 1),
                        'user_id': metadata.get('user_id', 'unknown')
                    })
            
            return {
                'total_chunks': len(documents),
                'unique_files': len(set(doc['file_name'] for doc in documents)),
                'documents': documents
            }
            
        except Exception as e:
            print(f"❌ Error retrieving documents: {e}")
            return {'total_chunks': 0, 'unique_files': 0, 'documents': []}
    
    def show_document_statistics(self):
        """Show detailed statistics about ingested data"""
        data = self.show_all_documents()
        
        print("\n📊 DOCUMENT STATISTICS")
        print("=" * 60)
        print(f"Total Chunks: {data['total_chunks']}")
        print(f"Unique Files: {data['unique_files']}")
        
        if data['documents']:
            # Group by file type
            file_types = {}
            for doc in data['documents']:
                file_type = doc['file_type']
                file_types[file_type] = file_types.get(file_type, 0) + 1
            
            print(f"\n📁 FILE TYPE DISTRIBUTION:")
            for file_type, count in file_types.items():
                print(f"   {file_type}: {count} chunks")
            
            # Show most recent files
            print(f"\n🕒 RECENTLY INGESTED FILES:")
            sorted_docs = sorted(data['documents'], 
                               key=lambda x: x.get('ingestion_time', ''), 
                               reverse=True)
            for doc in sorted_docs[:5]:  # Show last 5
                print(f"   📄 {doc['file_name']} ({doc['file_type']})")
    
    def search_documents(self, search_term: str) -> List[Dict]:
        """Search for specific documents by filename or content"""
        data = self.show_all_documents()
        results = []
        
        for doc in data['documents']:
            if (search_term.lower() in doc['file_name'].lower() or 
                search_term.lower() in doc['content_preview'].lower()):
                results.append(doc)
        
        return results

    def export_to_csv(self, filename: str = "second_brain_data.csv"):
        """Export all document metadata to CSV"""
        data = self.show_all_documents()
        
        if data['documents']:
            df = pd.DataFrame(data['documents'])
            df.to_csv(filename, index=False)
            print(f"✅ Data exported to {filename}")
            return True
        else:
            print("❌ No data to export")
            return False
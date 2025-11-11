import os
import PyPDF2
import docx
from PIL import Image
import pytesseract
import json
from datetime import datetime
from typing import List, Dict, Any

class DataIngestor:
    def __init__(self, settings):
        self.settings = settings
        self.supported_formats = {
            'text': ['.txt', '.md'],
            'documents': ['.pdf', '.docx', '.doc'],
            'images': ['.jpg', '.jpeg', '.png', '.gif'],
            'audio': ['.mp3', '.wav', '.m4a'],
            'video': ['.mp4', '.mov', '.avi'],
            'data': ['.json', '.csv']
        }
    
    def ingest_file(self, file_path: str, metadata: Dict = None) -> Dict[str, Any]:
        """Ingest a single file and return processed content"""
        file_ext = os.path.splitext(file_path)[1].lower()
        base_metadata = {
            'file_path': file_path,
            'file_type': file_ext,
            'ingestion_time': datetime.now().isoformat(),
            'file_size': os.path.getsize(file_path)
        }
        
        if metadata:
            base_metadata.update(metadata)
        
        content = ""
        
        try:
            if file_ext in self.supported_formats['text']:
                content = self._process_text_file(file_path)
            elif file_ext in self.supported_formats['documents']:
                content = self._process_document(file_path)
            elif file_ext in self.supported_formats['images']:
                content = self._process_image(file_path)
            elif file_ext in self.supported_formats['audio']:
                content = self._process_audio(file_path)
            elif file_ext in self.supported_formats['video']:
                content = self._process_video(file_path)
            elif file_ext in self.supported_formats['data']:
                content = self._process_data_file(file_path)
            else:
                print(f"Unsupported file format: {file_ext}")
                return None
                
            return {
                'content': content,
                'metadata': base_metadata,
                'chunks': self._chunk_content(content)
            }
            
        except Exception as e:
            print(f"Error processing {file_path}: {str(e)}")
            return None
    
    def _process_text_file(self, file_path: str) -> str:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    
    def _process_document(self, file_path: str) -> str:
        content = ""
        if file_path.endswith('.pdf'):
            with open(file_path, 'rb') as f:
                pdf_reader = PyPDF2.PdfReader(f)
                for page in pdf_reader.pages:
                    content += page.extract_text() + "\n"
        elif file_path.endswith(('.docx', '.doc')):
            doc = docx.Document(file_path)
            content = "\n".join([paragraph.text for paragraph in doc.paragraphs])
        return content
    
    def _process_image(self, file_path: str) -> str:
        # OCR processing
        try:
            image = Image.open(file_path)
            text = pytesseract.image_to_string(image)
            return text
        except Exception as e:
            print(f"OCR Error: {e}")
            return f"[Image file: {os.path.basename(file_path)} - OCR failed]"
    
    def _process_audio(self, file_path: str) -> str:
        # Placeholder for audio processing
        return f"[Audio file: {os.path.basename(file_path)} - transcription not implemented]"
    
    def _process_video(self, file_path: str) -> str:
        # Placeholder for video processing
        return f"[Video file: {os.path.basename(file_path)} - processing not implemented]"
    
    def _process_data_file(self, file_path: str) -> str:
        if file_ext.endswith('.json'):
            with open(file_path, 'r') as f:
                data = json.load(f)
                return json.dumps(data, indent=2)
        elif file_ext.endswith('.csv'):
            import pandas as pd
            df = pd.read_csv(file_path)
            return df.to_string()
        return ""
    
    def _chunk_content(self, content: str, chunk_size: int = 1000) -> List[str]:
        """Split content into manageable chunks for embedding"""
        words = content.split()
        chunks = []
        current_chunk = []
        current_size = 0
        
        for word in words:
            if current_size + len(word) > chunk_size and current_chunk:
                chunks.append(" ".join(current_chunk))
                current_chunk = [word]
                current_size = len(word)
            else:
                current_chunk.append(word)
                current_size += len(word) + 1
        
        if current_chunk:
            chunks.append(" ".join(current_chunk))
        
        return chunks
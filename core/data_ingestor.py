# core/data_ingestor.py
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
            'images': ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff'],
            'audio': ['.mp3', '.wav', '.m4a'],
            'video': ['.mp4', '.mov', '.avi'],
            'data': ['.json', '.csv']
        }
        self._check_ocr_availability()
    
    def _check_ocr_availability(self):
        """Check if OCR is available and provide helpful messages"""
        try:
            pytesseract.get_tesseract_version()
            self.ocr_available = True
            print("✅ OCR (Tesseract) is available")
        except Exception as e:
            self.ocr_available = False
            print("❌ OCR (Tesseract) is not available")
            print("💡 To enable image text extraction:")
            print("   - Install Tesseract OCR: https://github.com/UB-Mannheim/tesseract/wiki")
            print("   - Make sure it's added to your PATH")
    
    def ingest_file(self, file_path: str, metadata: Dict = None) -> Dict[str, Any]:
        """Ingest a single file and return processed content"""
        file_ext = os.path.splitext(file_path)[1].lower()
        base_metadata = {
            'file_path': file_path,
            'file_type': file_ext,
            'ingestion_time': datetime.now().isoformat(),
            'file_size': os.path.getsize(file_path),
            'file_name': os.path.basename(file_path)
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
                print(f"❌ Unsupported file format: {file_ext}")
                return None
                
            return {
                'content': content,
                'metadata': base_metadata,
                'chunks': self._chunk_content(content)
            }
            
        except Exception as e:
            print(f"❌ Error processing {file_path}: {str(e)}")
            return None
    
    def _process_text_file(self, file_path: str) -> str:
        """Process text files with encoding fallback"""
        encodings = ['utf-8', 'latin-1', 'windows-1252', 'iso-8859-1']
        for encoding in encodings:
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    return f.read()
            except UnicodeDecodeError:
                continue
        raise ValueError(f"Could not decode {file_path} with any common encoding")
    
    def _process_document(self, file_path: str) -> str:
        """Process PDF and Word documents"""
        content = ""
        if file_path.endswith('.pdf'):
            with open(file_path, 'rb') as f:
                pdf_reader = PyPDF2.PdfReader(f)
                for page_num, page in enumerate(pdf_reader.pages):
                    page_text = page.extract_text()
                    if page_text.strip():
                        content += f"Page {page_num + 1}:\n{page_text}\n\n"
        elif file_path.endswith(('.docx', '.doc')):
            doc = docx.Document(file_path)
            content = "\n".join([paragraph.text for paragraph in doc.paragraphs if paragraph.text.strip()])
        return content
    
    def _process_image(self, file_path: str) -> str:
        """Process images with OCR"""
        if not self.ocr_available:
            return f"[Image: {os.path.basename(file_path)} - OCR not available. Install Tesseract for text extraction]"
        
        try:
            # Open and preprocess image
            image = Image.open(file_path)
            
            # Convert to RGB if necessary
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Get image info
            width, height = image.size
            image_info = f"Image: {os.path.basename(file_path)} ({width}x{height}, {image.mode})"
            
            # Try OCR with different configurations
            extracted_text = ""
            
            # Configuration 1: Default
            try:
                default_text = pytesseract.image_to_string(image)
                if default_text.strip():
                    extracted_text = default_text
            except Exception as e:
                print(f"   Default OCR failed: {e}")
            
            # Configuration 2: Single text block
            if not extracted_text.strip():
                try:
                    config = '--psm 6'  # Assume uniform block of text
                    psm6_text = pytesseract.image_to_string(image, config=config)
                    if psm6_text.strip():
                        extracted_text = psm6_text
                except Exception as e:
                    print(f"   PSM6 OCR failed: {e}")
            
            if extracted_text.strip():
                print(f"   ✅ Extracted {len(extracted_text)} characters from image")
                return f"{image_info}\n\nExtracted Text:\n{extracted_text}"
            else:
                print(f"   ⚠️ No text found in image")
                return f"{image_info}\n\nNo text could be extracted from this image."
                
        except Exception as e:
            error_msg = f"Error processing image {os.path.basename(file_path)}: {str(e)}"
            print(f"   ❌ {error_msg}")
            return f"[Image: {os.path.basename(file_path)} - Processing failed: {str(e)}]"
    
    def _process_audio(self, file_path: str) -> str:
        """Process audio files - placeholder for future implementation"""
        return f"[Audio file: {os.path.basename(file_path)} - Audio transcription not yet implemented]"
    
    def _process_video(self, file_path: str) -> str:
        """Process video files - placeholder for future implementation"""
        return f"[Video file: {os.path.basename(file_path)} - Video processing not yet implemented]"
    
    def _process_data_file(self, file_path: str) -> str:
        """Process JSON and CSV files"""
        file_ext = os.path.splitext(file_path)[1].lower()
        try:
            if file_ext.endswith('.json'):
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return f"JSON Data from {os.path.basename(file_path)}:\n{json.dumps(data, indent=2)}"
            elif file_ext.endswith('.csv'):
                import pandas as pd
                df = pd.read_csv(file_path)
                return f"CSV Data from {os.path.basename(file_path)}:\n{df.to_string()}"
        except Exception as e:
            return f"[Data file: {os.path.basename(file_path)} - Error: {str(e)}]"
        return ""
    
    def _chunk_content(self, content: str, chunk_size: int = 800) -> List[str]:
        """Split content into manageable chunks for embedding"""
        if not content or len(content) < chunk_size:
            return [content] if content else []
        
        # Split by paragraphs first
        paragraphs = content.split('\n\n')
        chunks = []
        current_chunk = ""
        
        for paragraph in paragraphs:
            # If adding this paragraph would exceed chunk size and we have content
            if len(current_chunk) + len(paragraph) > chunk_size and current_chunk:
                chunks.append(current_chunk.strip())
                current_chunk = paragraph
            else:
                if current_chunk:
                    current_chunk += "\n\n" + paragraph
                else:
                    current_chunk = paragraph
        
        # Add the last chunk
        if current_chunk.strip():
            chunks.append(current_chunk.strip())
        
        # If still too large, split by sentences
        if chunks and any(len(chunk) > chunk_size * 1.5 for chunk in chunks):
            refined_chunks = []
            for chunk in chunks:
                if len(chunk) > chunk_size * 1.5:
                    sentences = chunk.split('. ')
                    current_sentence_chunk = ""
                    for sentence in sentences:
                        if len(current_sentence_chunk) + len(sentence) > chunk_size and current_sentence_chunk:
                            refined_chunks.append(current_sentence_chunk.strip() + ".")
                            current_sentence_chunk = sentence
                        else:
                            if current_sentence_chunk:
                                current_sentence_chunk += ". " + sentence
                            else:
                                current_sentence_chunk = sentence
                    if current_sentence_chunk.strip():
                        refined_chunks.append(current_sentence_chunk.strip())
                else:
                    refined_chunks.append(chunk)
            chunks = refined_chunks
        
        return chunks
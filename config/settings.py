import os
from dataclasses import dataclass
from typing import Dict, Any
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

@dataclass
class Settings:
    # API Keys (use environment variables in production)
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    
    # Vector Database
    VECTOR_DB_PATH: str = "data/vector_store"
    CHROMA_PERSIST_DIR: str = "data/chroma_db"

    # Memory System
    MEMORY_ENCRYPTION: bool = False  # For future encryption feature
    MEMORY_BACKUP: bool = True
    AUTO_EXPORT_MEMORIES: bool = True  # Auto export memories to vector store
    
    # File Storage
    UPLOAD_FOLDER: str = "data/uploads"
    PROCESSED_FOLDER: str = "data/processed"
    
    # AI Model Settings
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    LLM_MODEL: str = "gpt-4"
    # GROQ_MODEL: str = "llama-3.1-70b-versatile"  # to set default model for GROQ API usage
    
    # Real-time Processing
    REAL_TIME_ENABLED: bool = True
    MEETING_ASSISTANT_ENABLED: bool = False  # Disabled by default for now
    
    @classmethod
    def validate(cls):
        if not cls.OPENAI_API_KEY and not cls.GROQ_API_KEY:
            raise ValueError("Either OPENAI_API_KEY or GROQ_API_KEY must be set")

settings = Settings()
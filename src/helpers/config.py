from pydantic_settings import BaseSettings , SettingsConfigDict
from typing import List
class Settings(BaseSettings):
    APP_NAME : str
    APP_VERSION : str
    
    FILE_ALLOWED_TYPES: list
    FILE_MAX_SIZE: int
    FILE_DEFAULT_CHUNK_SIZE: int
    
    JWT_SECRET_KEY : str
    JWT_ALGORITHM : str
    ACCESS_TOKEN_EXPIRE_MINUTES : int
    REFRESH_TOKEN_EXPIRE_DAYS : int
    
    
    POSTGRES_USERNAME: str
    POSTGRES_PASSWORD: str
    POSTGRES_HOST: str
    POSTGRES_PORT: int
    POSTGRES_MAIN_DATABASE: str
    POSTGRES_URL: str
    POSTGRES_SYNC_URL: str
    
    GENERATION_BACKEND: str 
    EMBEDDING_BACKEND: str 

    # Gemini
    GEMINI_API_KEY: str
    GEMINI_API_URL: str 
    #Ollama
    OLLAMA_API_URL: str
    # Cohere
    COHERE_API_KEY: str

    # Models
    GENERATION_MODEL_ID: str
    EMBEDDING_MODEL_ID: str 
    EMBEDDING_MODEL_SIZE: int 

    
    INPUT_DEFAULT_MAX_CHARACTERS: int 
    GENERATION_DEFAULT_MAX_TOKENS: int 
    GENERATION_DEFAULT_TEMPERATURE: float 

    VECTOR_DB_BACKEND_LITERAL : list[str] = None
    VECTOR_DB_BACKEND : str
    VECTOR_DB_PATH : str
    VECTOR_DB_DISTANCE_METHOD : str
    VECTOR_DB_PGVEC_INDEX_THRESHOLD : int
    
    PRIMARY_LANG: str = "en"
    DEFAULT_LANG: str = "en"
    
    CELERY_BROKER_URL : str
    CELERY_RESULT_BACKEND : str
    CELERY_TASK_SERIALIZER : str
    CELERY_TASK_ACKS_LATE : bool
    CELERY_TASK_TIME_LIMIT : int
    CELERY_WORKER_CONCURRENCY : int
    
    RERANK_ENABLED : bool
    RERANK_API_KEY : str
    RERANK_MODEL_ID : str
    RERANK_API_URL : str
    RERANK_TIMEOUT_SECONDS : int
    RERANK_MAX_DOCUMENTS : int
    
    QUERY_REWRITE_ENABLED : bool 
    QUERY_REWRITE_MAX_HISTORY : int 
    QUERY_REWRITE_MAX_CHARACTERS : int
    QUERY_REWRITE_FALLBACK : bool
    
    DATABASE_CREDENTIALS_ENCRYPTION_KEY: str

    class Config:
        env_file = ".env"

def get_settings():
    
    return Settings()
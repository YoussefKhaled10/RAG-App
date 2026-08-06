APP_NAME="RAG App"
APP_VERSION="0.1"

# =========================
# FIle settings
# =========================
FILE_ALLOWED_TYPES=["application/pdf","text/plain"] 
FILE_MAX_SIZE=10485760
FILE_DEFAULT_CHUNK_SIZE=512000 # 512KB

# =========================
# Authentication settings
# =========================
JWT_SECRET_KEY=""
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# =========================
# DB URL and settings
# =========================
POSTGRES_USERNAME=""
POSTGRES_PASSWORD=""
POSTGRES_HOST=""
POSTGRES_PORT=5433
POSTGRES_MAIN_DATABASE=""


POSTGRES_URL=""
POSTGRES_SYNC_URL=""

# =========================
# AI Providers
# =========================
GENERATION_BACKEND="GEMINI"
EMBEDDING_BACKEND="COHERE"
# =========================
# Gemini - Generation
# =========================
GEMINI_API_KEY=""
GEMINI_API_URL=""
# =========================
# OLLAMA - Generation
# =========================
OLLAMA_API_URL=""
GENERATION_MODEL_ID="models/gemini-2.5-flash"
# =========================
# Cohere - Embeddings
# =========================
COHERE_API_KEY=""
#EMBEDDING_MODEL_ID="nomic-embed-text"
EMBEDDING_MODEL_ID="embed-multilingual-light-v3.0"
EMBEDDING_MODEL_SIZE=384

# =========================
# Generation Settings
# =========================
INPUT_DEFAULT_MAX_CHARACTERS=10000
GENERATION_DEFAULT_MAX_TOKENS=1000
GENERATION_DEFAULT_TEMPERATURE=0.2

# =========================
# Qdrant - Vector DB
# =========================
VECTOR_DB_BACKEND_LITERAL=["QDRANT", "PGVECTOR"]
VECTOR_DB_BACKEND = "PGVECTOR"
VECTOR_DB_PATH="/home/youssef/pgvector_db"
VECTOR_DB_DISTANCE_METHOD="cosine"
VECTOR_DB_PGVEC_INDEX_THRESHOLD=100
# =========================
# Language settings
# =========================
PRIMARY_LANG = "en"
DEFAULT_LANG = "en"


# =========================
# Celery settings
# =========================

CELERY_BROKER_URL=
CELERY_RESULT_BACKEND=

CELERY_TASK_SERIALIZER=json
CELERY_TASK_TIME_LIMIT=600
CELERY_TASK_ACKS_LATE=true
CELERY_WORKER_CONCURRENCY=1

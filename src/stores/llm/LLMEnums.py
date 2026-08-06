from enum import Enum


class LLMEnums(Enum):
    GEMINI = "GEMINI"
    COHERE = "COHERE"
    OLLAMA = "OLLAMA"
    GLM = "GLM"


class GeminiEnums(Enum):
    SYSTEM = "system"
    USER = "user"
    MODEL = "model"
    ASSISTANT = "model"


class CoHereEnums(Enum):
    SYSTEM = "SYSTEM"
    USER = "USER"
    ASSISTANT = "CHATBOT"
    DOCUMENT = "search_document"
    QUERY = "search_query"


class OllamaEnums(Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


class GLMEnums(Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


class DocumentTypeEnum(Enum):
    DOCUMENT = "document"
    QUERY = "query"

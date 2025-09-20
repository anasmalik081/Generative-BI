from langchain_groq import ChatGroq
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from sentence_transformers import SentenceTransformer
from config.settings import settings
import logging

logger = logging.getLogger(__name__)

class LLMFactory:
    @staticmethod
    def get_chat_model():
        """Get the configured chat model"""
        if settings.ai_provider == "openai":
            if not settings.openai_api_key:
                raise ValueError("OpenAI API key not configured")
            return ChatOpenAI(
                api_key=settings.openai_api_key,
                model=settings.openai_model,
                temperature=0.0
            )
        else:  # groq
            if not settings.groq_api_key:
                raise ValueError("Groq API key not configured")
            return ChatGroq(
                groq_api_key=settings.groq_api_key,
                model_name=settings.groq_model,
                temperature=0.0
            )
    
    @staticmethod
    def get_embedding_model():
        """Get the configured embedding model"""
        if settings.ai_provider == "openai":
            if not settings.openai_api_key:
                raise ValueError("OpenAI API key not configured")
            return OpenAIEmbeddings(
                api_key=settings.openai_api_key,
                model=settings.openai_embedding_model
            )
        else:  # Use sentence transformers for Groq
            return SentenceTransformer(settings.embedding_model)

llm_factory = LLMFactory()

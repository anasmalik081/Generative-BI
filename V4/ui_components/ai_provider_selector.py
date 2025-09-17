import streamlit as st
from config.settings import settings
import os

def render_ai_provider_selector():
    """Render AI provider selection in sidebar"""
    with st.sidebar:
        st.header("🤖 AI Configuration")
        
        current_provider = settings.ai_provider
        
        provider = st.selectbox(
            "AI Provider",
            ["groq", "openai"],
            index=0 if current_provider == "groq" else 1,
            help="Choose your AI provider for chat and embeddings"
        )
        
        if provider == "openai":
            st.info("🔑 Make sure to set OPENAI_API_KEY in your .env file")
            if not settings.openai_api_key:
                st.error("❌ OpenAI API key not configured")
        else:
            st.info("🔑 Using Groq API")
            if not settings.groq_api_key:
                st.error("❌ Groq API key not configured")
        
        # Update environment variable if changed
        if provider != current_provider:
            os.environ["AI_PROVIDER"] = provider
            st.success(f"✅ Switched to {provider.upper()}")
            st.info("🔄 Please restart the app to apply changes")
        
        # Show current model info
        st.subheader("📋 Current Configuration")
        if provider == "openai":
            st.write(f"**Chat Model:** {settings.openai_model}")
            st.write(f"**Embedding Model:** {settings.openai_embedding_model}")
        else:
            st.write(f"**Chat Model:** {settings.groq_model}")
            st.write(f"**Embedding Model:** {settings.embedding_model}")

ai_provider_selector = render_ai_provider_selector

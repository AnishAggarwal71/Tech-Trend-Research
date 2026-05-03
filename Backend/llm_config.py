# """
# LLM Configuration Module - Production Ready with Rate Limiting
# """

# from typing import Literal, Optional, Any
# from langchain_google_genai import ChatGoogleGenerativeAI
# from langchain_anthropic import ChatAnthropic
# from langchain_core.language_models.chat_models import BaseChatModel
# from langchain_core.messages import BaseMessage
# import os
# from dotenv import load_dotenv

# load_dotenv()


# class RateLimitedLLM:
#     """
#     Wrapper for LLM that enforces rate limiting.
#     """
    
#     def __init__(self, llm: BaseChatModel, rate_limiter=None):
#         self.llm = llm
#         self.rate_limiter = rate_limiter
    
#     def invoke(self, input: Any, **kwargs) -> Any:
#         """Rate-limited invoke."""
#         if self.rate_limiter:
#             # Estimate tokens (rough heuristic)
#             if isinstance(input, str):
#                 estimated_tokens = len(input.split()) * 2
#             elif isinstance(input, list):
#                 estimated_tokens = sum(len(str(m).split()) * 2 for m in input)
#             else:
#                 estimated_tokens = 5000  # Default estimate
            
#             self.rate_limiter.wait_if_needed(estimated_tokens)
        
#         return self.llm.invoke(input, **kwargs)
    
#     def with_structured_output(self, schema, **kwargs):
#         """Return a new rate-limited LLM with structured output."""
#         structured_llm = self.llm.with_structured_output(schema, **kwargs)
#         return RateLimitedStructuredLLM(structured_llm, self.rate_limiter)
    
#     def __getattr__(self, name):
#         """Delegate other methods to underlying LLM."""
#         return getattr(self.llm, name)


# class RateLimitedStructuredLLM:
#     """Wrapper for structured output LLM with rate limiting."""
    
#     def __init__(self, structured_llm, rate_limiter=None):
#         self.structured_llm = structured_llm
#         self.rate_limiter = rate_limiter
    
#     def invoke(self, input: Any, **kwargs) -> Any:
#         """Rate-limited invoke."""
#         if self.rate_limiter:
#             if isinstance(input, str):
#                 estimated_tokens = len(input.split()) * 2
#             elif isinstance(input, dict):
#                 estimated_tokens = sum(len(str(v).split()) * 2 for v in input.values())
#             else:
#                 estimated_tokens = 5000
            
#             self.rate_limiter.wait_if_needed(estimated_tokens)
        
#         return self.structured_llm.invoke(input, **kwargs)
    
#     def __getattr__(self, name):
#         """Delegate other methods."""
#         return getattr(self.structured_llm, name)


# class LLMConfig:
#     """
#     Centralized LLM configuration with rate limiting support.
#     """
    
#     PROVIDERS = Literal["google", "anthropic"]
#     ACTIVE_PROVIDER: PROVIDERS = "google"
    
#     # Updated model names (use the ones that work from your check)
#     MODELS = {
#         "google": {
#             "default": "models/gemini-2.0-flash",  # Updated to working model
#             "reasoning": "models/gemini-2.0-flash",   # Updated to working model
#             "fast": "models/gemini-2.0-flash-lite"       # Updated to working model
#         },
#         "anthropic": {
#             "default": "claude-3-5-sonnet-20241022",
#             "reasoning": "claude-3-5-sonnet-20241022",
#             "fast": "claude-3-5-haiku-20241022"
#         }
#     }
    
#     @staticmethod
#     def get_llm(
#         provider: Optional[PROVIDERS] = None,
#         model_name: Optional[str] = None,
#         temperature: float = 0.1,
#         enable_rate_limiting: bool = True,
#         **kwargs
#     ) -> BaseChatModel:
#         """
#         Initialize LLM with optional rate limiting.
        
#         Args:
#             provider: LLM provider
#             model_name: Specific model version
#             temperature: Sampling temperature
#             enable_rate_limiting: If True, wrap with rate limiter
#             **kwargs: Additional parameters
#         """
        
#         provider = provider or LLMConfig.ACTIVE_PROVIDER
        
#         if provider == "google":
#             api_key = os.getenv("GOOGLE_API_KEY")
#             if not api_key:
#                 raise ValueError("GOOGLE_API_KEY not found in .env")
            
#             model = model_name or LLMConfig.MODELS["google"]["default"]
            
#             base_llm = ChatGoogleGenerativeAI(
#                 model=model,
#                 temperature=temperature,
#                 google_api_key=api_key,
#                 convert_system_message_to_human=True,
#                 **kwargs
#             )
            
#             # Wrap with rate limiter for free tier
#             if enable_rate_limiting:
#                 from rate_limiter import gemini_rate_limiter
#                 return RateLimitedLLM(base_llm, gemini_rate_limiter)
            
#             return base_llm
            
#         elif provider == "anthropic":
#             api_key = os.getenv("ANTHROPIC_API_KEY")
#             if not api_key:
#                 raise ValueError("ANTHROPIC_API_KEY not found in .env")
            
#             model = model_name or LLMConfig.MODELS["anthropic"]["default"]
            
#             return ChatAnthropic(
#                 model=model,
#                 temperature=temperature,
#                 anthropic_api_key=api_key,
#                 max_tokens=8192,
#                 **kwargs
#             )
        
#         else:
#             raise ValueError(f"Unsupported provider: {provider}")
    
    
#     @staticmethod
#     def get_default_llm() -> BaseChatModel:
#         """Get default LLM with rate limiting."""
#         return LLMConfig.get_llm(temperature=0.1, enable_rate_limiting=True)
    
    
#     @staticmethod
#     def get_reasoning_llm() -> BaseChatModel:
#         """Get reasoning LLM with rate limiting."""
#         provider = LLMConfig.ACTIVE_PROVIDER
#         model = LLMConfig.MODELS[provider]["reasoning"]
        
#         return LLMConfig.get_llm(
#             provider=provider,
#             model_name=model,
#             temperature=0.0,
#             enable_rate_limiting=True
#         )
    
    
#     @staticmethod
#     def get_fast_llm() -> BaseChatModel:
#         """Get fast LLM with rate limiting."""
#         provider = LLMConfig.ACTIVE_PROVIDER
#         model = LLMConfig.MODELS[provider]["fast"]
        
#         return LLMConfig.get_llm(
#             provider=provider,
#             model_name=model,
#             temperature=0.2,
#             enable_rate_limiting=True
#         )
    
    
#     @staticmethod
#     def get_embedding_model():
#         """Get embedding model (no rate limiting needed - different quota)."""
#         from langchain_google_genai import GoogleGenerativeAIEmbeddings
        
#         api_key = os.getenv("GOOGLE_API_KEY")
#         if not api_key:
#             raise ValueError("GOOGLE_API_KEY required")
        
#         return GoogleGenerativeAIEmbeddings(
#             model="models/embedding-001",
#             google_api_key=api_key
#         )


# # Convenience instances
# print(f"🤖 Active LLM Provider: {LLMConfig.ACTIVE_PROVIDER.upper()}")
# print(f"📊 Rate Limiting: ENABLED (15 RPM, 1500 RPD, 1M TPM)")

# default_llm = LLMConfig.get_default_llm()
# reasoning_llm = LLMConfig.get_reasoning_llm()
# fast_llm = LLMConfig.get_fast_llm()
# embedding_model = LLMConfig.get_embedding_model()


"""LLM Config - Groq"""
from typing import Literal, Optional, Any
from langchain_groq import ChatGroq
from langchain_core.language_models.chat_models import BaseChatModel
import os
from dotenv import load_dotenv
load_dotenv()

class LLMConfig:
    PROVIDERS = Literal["groq"]
    ACTIVE_PROVIDER: PROVIDERS = "groq"
    MODELS = {"groq": {"default": "llama-3.3-70b-versatile", "reasoning": "llama-3.3-70b-versatile", "fast": "llama-3.1-8b-instant"}}
    
    @staticmethod
    def get_llm(provider: Optional[PROVIDERS] = None, model_name: Optional[str] = None, temperature: float = 0.1, enable_rate_limiting: bool = False, **kwargs) -> BaseChatModel:
        provider = provider or LLMConfig.ACTIVE_PROVIDER
        if provider == "groq":
            api_key = os.getenv("GROQ_API_KEY")
            if not api_key:
                raise ValueError("GROQ_API_KEY not found")
            model = model_name or LLMConfig.MODELS["groq"]["default"]
            return ChatGroq(model=model, temperature=temperature, groq_api_key=api_key, **kwargs)
    
    @staticmethod
    def get_default_llm() -> BaseChatModel:
        return LLMConfig.get_llm(temperature=0.1)
    
    @staticmethod
    def get_reasoning_llm() -> BaseChatModel:
        return LLMConfig.get_llm(model_name="llama-3.3-70b-versatile", temperature=0.0)
    
    @staticmethod
    def get_fast_llm() -> BaseChatModel:
        return LLMConfig.get_llm(model_name="llama-3.1-8b-instant", temperature=0.2)
    
    @staticmethod
    def get_embedding_model():
        from langchain_community.embeddings import HuggingFaceEmbeddings
        return HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

print(f"🤖 Active: GROQ")
default_llm = LLMConfig.get_default_llm()
reasoning_llm = LLMConfig.get_reasoning_llm()
fast_llm = LLMConfig.get_fast_llm()
embedding_model = LLMConfig.get_embedding_model()
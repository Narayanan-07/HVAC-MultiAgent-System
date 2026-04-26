# backend/llm.py

from crewai import LLM
import os
from dotenv import load_dotenv
import litellm
import time
from typing import Optional
from functools import wraps
import logging

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================================================
# LITELLM AGGRESSIVE RETRY CONFIGURATION
# ============================================================================
litellm.num_retries = 20
litellm.request_timeout = 180
litellm.retry_policy = True

# Custom retry settings for rate limits
litellm.success_callback = []
litellm.failure_callback = []

# ============================================================================
# API KEY ROTATION SYSTEM
# ============================================================================
class APIKeyRotator:
    """Rotates between multiple API keys to avoid rate limits"""
    
    def __init__(self):
        # Load multiple Groq keys (create multiple accounts if needed)
        self.groq_keys = [
            os.getenv("GROQ_API_KEY"),
            os.getenv("GROQ_API_KEY_2"),
            os.getenv("GROQ_API_KEY_3"),
        ]
        
        # Load multiple Gemini keys as fallback
        self.gemini_keys = [
            os.getenv("GEMINI_API_KEY"),
            os.getenv("GEMINI_API_KEY_2"),
        ]
        
        # Remove None values
        self.groq_keys = [k for k in self.groq_keys if k]
        self.gemini_keys = [k for k in self.gemini_keys if k]
        
        self.groq_index = 0
        self.gemini_index = 0
        
        logger.info(f"Loaded {len(self.groq_keys)} Groq keys and {len(self.gemini_keys)} Gemini keys")
    
    def get_next_groq_key(self) -> str:
        """Get next Groq API key in rotation"""
        if not self.groq_keys:
            raise ValueError("No Groq API keys available")
        
        key = self.groq_keys[self.groq_index]
        self.groq_index = (self.groq_index + 1) % len(self.groq_keys)
        return key
    
    def get_next_gemini_key(self) -> str:
        """Get next Gemini API key in rotation"""
        if not self.gemini_keys:
            raise ValueError("No Gemini API keys available")
        
        key = self.gemini_keys[self.gemini_index]
        self.gemini_index = (self.gemini_index + 1) % len(self.gemini_keys)
        return key

# ============================================================================
# RATE LIMITER
# ============================================================================
class RateLimiter:
    """Controls request rate to avoid hitting API limits"""
    
    def __init__(self, requests_per_minute: int = 15):
        self.rpm = requests_per_minute
        self.min_delay = 60.0 / requests_per_minute  # seconds between requests
        self.last_request_time = 0
        self.request_count = 0
    
    def wait_if_needed(self):
        """Sleep if needed to respect rate limit"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.min_delay:
            sleep_time = self.min_delay - time_since_last
            logger.info(f"Rate limiting: sleeping {sleep_time:.2f}s")
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()
        self.request_count += 1
        
        # Log every 10 requests
        if self.request_count % 10 == 0:
            logger.info(f"✓ Completed {self.request_count} requests")

# ============================================================================
# GLOBAL INSTANCES
# ============================================================================
key_rotator = APIKeyRotator()
rate_limiter = RateLimiter(requests_per_minute=12)  # Conservative: 12 RPM for safety

# ============================================================================
# PRIMARY LLM (GROQ with rotation)
# ============================================================================
def get_groq_llm() -> LLM:
    """Get Groq LLM with current rotated API key"""
    rate_limiter.wait_if_needed()
    
    return LLM(
        model="groq/llama-3.3-70b-versatile",
        temperature=0.0,
        max_retries=20,
        api_key=key_rotator.get_next_groq_key(),
        timeout=180,
    )

# ============================================================================
# FALLBACK LLM (GEMINI)
# ============================================================================
def get_gemini_llm() -> LLM:
    """Fallback to Gemini if Groq fails"""
    rate_limiter.wait_if_needed()
    
    return LLM(
        model="gemini/gemini-2.5-flash",
        temperature=0.0,
        max_retries=15,
        api_key=key_rotator.get_next_gemini_key(),
        timeout=120,
    )

# ============================================================================
# SMART LLM with AUTO-FALLBACK
# ============================================================================
class SmartLLM:
    """Wrapper that tries Groq first, falls back to Gemini on rate limit"""
    
    def __init__(self):
        self.primary = get_groq_llm()
        self.use_fallback = False
        self.consecutive_failures = 0
    
    def __getattr__(self, name):
        """Proxy all attributes to the active LLM"""
        if self.use_fallback:
            return getattr(get_gemini_llm(), name)
        return getattr(self.primary, name)
    
    def call(self, *args, **kwargs):
        """Smart call with automatic fallback"""
        try:
            rate_limiter.wait_if_needed()
            result = self.primary.call(*args, **kwargs)
            self.consecutive_failures = 0  # Reset on success
            return result
            
        except Exception as e:
            error_msg = str(e).lower()
            
            # Check if it's a rate limit error
            if "rate" in error_msg or "429" in error_msg or "quota" in error_msg:
                logger.warning(f"Groq rate limit hit. Switching to Gemini fallback.")
                self.consecutive_failures += 1
                
                # If too many failures, switch to Gemini permanently for this run
                if self.consecutive_failures >= 3:
                    logger.warning("Switching to Gemini for remainder of pipeline")
                    self.use_fallback = True
                
                # Try Gemini
                try:
                    time.sleep(5)  # Extra cooldown
                    return get_gemini_llm().call(*args, **kwargs)
                except Exception as fallback_error:
                    logger.error(f"Gemini also failed: {fallback_error}")
                    raise
            else:
                # Not a rate limit error, re-raise
                raise

# ============================================================================
# DEFAULT LLM EXPORT
# ============================================================================
llm = get_groq_llm()

# For agents that need smart fallback
smart_llm = SmartLLM()
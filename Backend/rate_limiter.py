"""
Rate Limiter for API calls
Handles Gemini Free Tier constraints: 15 RPM, 1500 RPD, 1M TPM
"""

import time
from datetime import datetime, timedelta
from collections import deque
from typing import Optional
import threading


class RateLimiter:
    """
    Thread-safe rate limiter for API calls.
    Tracks requests per minute (RPM) and requests per day (RPD).
    """
    
    def __init__(
        self,
        requests_per_minute: int = 15,
        requests_per_day: int = 1500,
        tokens_per_minute: int = 1_000_000
    ):
        self.rpm_limit = requests_per_minute
        self.rpd_limit = requests_per_day
        self.tpm_limit = tokens_per_minute
        
        # Track request timestamps
        self.minute_requests = deque()
        self.day_requests = deque()
        self.minute_tokens = deque()
        
        # Thread lock for safety
        self.lock = threading.Lock()
        
        # Stats
        self.total_requests = 0
        self.total_wait_time = 0
        
    
    def wait_if_needed(self, estimated_tokens: int = 5000) -> float:
        """
        Wait if rate limits would be exceeded.
        
        Args:
            estimated_tokens: Estimated token count for this request
            
        Returns:
            Time waited in seconds
        """
        
        with self.lock:
            now = datetime.now()
            wait_time = 0
            
            # Clean old requests (older than 1 minute)
            one_minute_ago = now - timedelta(minutes=1)
            while self.minute_requests and self.minute_requests[0] < one_minute_ago:
                self.minute_requests.popleft()
            
            while self.minute_tokens and self.minute_tokens[0][0] < one_minute_ago:
                self.minute_tokens.popleft()
            
            # Clean old requests (older than 1 day)
            one_day_ago = now - timedelta(days=1)
            while self.day_requests and self.day_requests[0] < one_day_ago:
                self.day_requests.popleft()
            
            # Check RPM limit
            if len(self.minute_requests) >= self.rpm_limit:
                oldest_request = self.minute_requests[0]
                wait_until = oldest_request + timedelta(minutes=1)
                wait_seconds = (wait_until - now).total_seconds()
                
                if wait_seconds > 0:
                    print(f"⏳ RPM limit reached. Waiting {wait_seconds:.1f}s...")
                    time.sleep(wait_seconds)
                    wait_time += wait_seconds
                    now = datetime.now()
            
            # Check TPM limit
            current_tokens = sum(tokens for _, tokens in self.minute_tokens)
            if current_tokens + estimated_tokens > self.tpm_limit:
                oldest_token_time = self.minute_tokens[0][0]
                wait_until = oldest_token_time + timedelta(minutes=1)
                wait_seconds = (wait_until - now).total_seconds()
                
                if wait_seconds > 0:
                    print(f"⏳ TPM limit reached. Waiting {wait_seconds:.1f}s...")
                    time.sleep(wait_seconds)
                    wait_time += wait_seconds
                    now = datetime.now()
            
            # Check RPD limit
            if len(self.day_requests) >= self.rpd_limit:
                print(f"⛔ Daily limit of {self.rpd_limit} requests reached!")
                oldest_request = self.day_requests[0]
                wait_until = oldest_request + timedelta(days=1)
                wait_seconds = (wait_until - now).total_seconds()
                
                if wait_seconds > 0:
                    print(f"⏳ Waiting {wait_seconds/3600:.1f} hours until quota resets...")
                    time.sleep(wait_seconds)
                    wait_time += wait_seconds
                    now = datetime.now()
            
            # Record this request
            self.minute_requests.append(now)
            self.day_requests.append(now)
            self.minute_tokens.append((now, estimated_tokens))
            
            self.total_requests += 1
            self.total_wait_time += wait_time
            
            return wait_time
    
    
    def get_stats(self) -> dict:
        """Get current rate limiter statistics."""
        
        with self.lock:
            now = datetime.now()
            one_minute_ago = now - timedelta(minutes=1)
            one_day_ago = now - timedelta(days=1)
            
            recent_minute = [r for r in self.minute_requests if r > one_minute_ago]
            recent_day = [r for r in self.day_requests if r > one_day_ago]
            recent_tokens = sum(tokens for t, tokens in self.minute_tokens if t > one_minute_ago)
            
            return {
                "total_requests": self.total_requests,
                "total_wait_time": self.total_wait_time,
                "requests_last_minute": len(recent_minute),
                "requests_last_day": len(recent_day),
                "tokens_last_minute": recent_tokens,
                "rpm_remaining": max(0, self.rpm_limit - len(recent_minute)),
                "rpd_remaining": max(0, self.rpd_limit - len(recent_day)),
                "tpm_remaining": max(0, self.tpm_limit - recent_tokens)
            }
    
    
    def print_stats(self):
        """Print formatted statistics."""
        stats = self.get_stats()
        
        print(f"\n📊 Rate Limiter Stats:")
        print(f"   Total Requests: {stats['total_requests']}")
        print(f"   Total Wait Time: {stats['total_wait_time']:.1f}s")
        print(f"   Last Minute: {stats['requests_last_minute']}/{self.rpm_limit} requests")
        print(f"   Last Day: {stats['requests_last_day']}/{self.rpd_limit} requests")
        print(f"   Tokens/Min: {stats['tokens_last_minute']:,}/{self.tpm_limit:,}")
        print(f"   Remaining RPM: {stats['rpm_remaining']}")
        print(f"   Remaining RPD: {stats['rpd_remaining']}")


# Global rate limiter instance for Gemini Free Tier
gemini_rate_limiter = RateLimiter(
    requests_per_minute=15,
    requests_per_day=1500,
    tokens_per_minute=1_000_000
)


def rate_limited_call(func, estimated_tokens: int = 5000, *args, **kwargs):
    """
    Wrapper to make a rate-limited API call.
    
    Args:
        func: Function to call
        estimated_tokens: Estimated tokens for this call
        *args, **kwargs: Arguments for the function
        
    Returns:
        Result of func(*args, **kwargs)
    """
    
    gemini_rate_limiter.wait_if_needed(estimated_tokens)
    return func(*args, **kwargs)
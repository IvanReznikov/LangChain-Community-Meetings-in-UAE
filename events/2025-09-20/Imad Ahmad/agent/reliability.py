import time
import asyncio
from typing import Callable, Any, Dict, Optional
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from datetime import datetime, timedelta
import threading
import random


class CircuitBreaker:
    """Circuit breaker pattern implementation for external service calls."""
    
    def __init__(self, failure_threshold: int = 3, recovery_timeout: int = 120, expected_exception: type = Exception):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        
        self.failure_count = 0
        self.last_failure_time = None
        self.state = 'CLOSED'  # CLOSED, OPEN, HALF_OPEN
        self._lock = threading.Lock()
    
    def __call__(self, func: Callable) -> Callable:
        def wrapper(*args, **kwargs):
            with self._lock:
                if self.state == 'OPEN':
                    if self._should_attempt_reset():
                        self.state = 'HALF_OPEN'
                    else:
                        raise Exception(f"Circuit breaker is OPEN. Service unavailable.")
                
                try:
                    result = func(*args, **kwargs)
                    self._on_success()
                    return result
                except self.expected_exception as e:
                    self._on_failure()
                    raise e
        
        return wrapper
    
    def _should_attempt_reset(self) -> bool:
        return (
            self.last_failure_time and 
            datetime.now() - self.last_failure_time >= timedelta(seconds=self.recovery_timeout)
        )
    
    def _on_success(self):
        self.failure_count = 0
        self.state = 'CLOSED'
    
    def _on_failure(self):
        self.failure_count += 1
        self.last_failure_time = datetime.now()
        
        if self.failure_count >= self.failure_threshold:
            self.state = 'OPEN'


def with_timeout_and_retry(timeout_seconds: int = 5, max_attempts: int = 3):
    """Decorator that adds timeout and retry logic to functions."""
    def decorator(func: Callable) -> Callable:
        @retry(
            stop=stop_after_attempt(max_attempts),
            wait=wait_exponential(multiplier=1, min=1, max=10),
            retry=retry_if_exception_type((Exception,))
        )
        def wrapper(*args, **kwargs):
            # Add jitter to avoid thundering herd
            if max_attempts > 1:
                time.sleep(random.uniform(0, 0.1))
            
            # Simple timeout implementation
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                elapsed = time.time() - start_time
                if elapsed > timeout_seconds:
                    raise TimeoutError(f"Function {func.__name__} exceeded timeout of {timeout_seconds}s")
                return result
            except Exception as e:
                elapsed = time.time() - start_time
                if elapsed > timeout_seconds:
                    raise TimeoutError(f"Function {func.__name__} exceeded timeout of {timeout_seconds}s")
                raise e
        
        return wrapper
    return decorator


class FallbackManager:
    """Manages fallback strategies for different services."""
    
    def __init__(self):
        self.fallback_strategies: Dict[str, Callable] = {}
    
    def register_fallback(self, service_name: str, fallback_func: Callable):
        """Register a fallback function for a service."""
        self.fallback_strategies[service_name] = fallback_func
    
    def execute_with_fallback(self, service_name: str, primary_func: Callable, *args, **kwargs) -> Any:
        """Execute primary function with fallback on failure."""
        try:
            return primary_func(*args, **kwargs)
        except Exception as e:
            if service_name in self.fallback_strategies:
                fallback_func = self.fallback_strategies[service_name]
                return fallback_func(*args, **kwargs)
            else:
                raise e


# Global instances
search_circuit_breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=120)
fallback_manager = FallbackManager()


def reliable_service_call(service_name: str, timeout: int = 5, retries: int = 2):
    """Decorator that combines circuit breaker, timeout, retry, and fallback patterns."""
    def decorator(func: Callable) -> Callable:
        # Apply circuit breaker for search service
        if service_name == "search":
            func = search_circuit_breaker(func)
        
        # Apply timeout and retry
        func = with_timeout_and_retry(timeout_seconds=timeout, max_attempts=retries + 1)(func)
        
        def wrapper(*args, **kwargs):
            return fallback_manager.execute_with_fallback(service_name, func, *args, **kwargs)
        
        return wrapper
    return decorator

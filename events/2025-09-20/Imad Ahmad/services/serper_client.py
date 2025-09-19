import requests
import os
from typing import List, Dict, Any
from agent.schemas import SearchResult
from agent.reliability import reliable_service_call
from observability.logger import setup_logger, log_tool_call, log_tool_result
import time
import uuid

logger = setup_logger()


class SerperClient:
    """Typed client for Serper API with timeouts and retries."""
    
    def __init__(self):
        self.api_key = os.getenv("SERPER_API_KEY")
        self.base_url = "https://google.serper.dev/search"
        
        if not self.api_key:
            raise ValueError("SERPER_API_KEY environment variable is required")
    
    @reliable_service_call("search", timeout=5, retries=2)
    def search(self, query: str, num_results: int = 5) -> List[SearchResult]:
        """Search using Serper API and return structured results."""
        request_id = str(uuid.uuid4())
        start_time = time.time()
        
        inputs = {"query": query, "num_results": num_results}
        inputs_hash = log_tool_call(logger, "serper_search", inputs, request_id)
        
        try:
            headers = {
                "X-API-KEY": self.api_key,
                "Content-Type": "application/json"
            }
            
            payload = {
                "q": query,
                "num": num_results
            }
            
            response = requests.post(
                self.base_url,
                headers=headers,
                json=payload,
                timeout=5
            )
            
            response.raise_for_status()
            data = response.json()
            
            # Parse results
            results = []
            organic_results = data.get("organic", [])
            
            for result in organic_results[:num_results]:
                search_result = SearchResult(
                    title=result.get("title", ""),
                    url=result.get("link", ""),
                    snippet=result.get("snippet", "")
                )
                results.append(search_result)
            
            duration_ms = int((time.time() - start_time) * 1000)
            log_tool_result(logger, "serper_search", inputs_hash, results, duration_ms, request_id, True)
            
            return results
            
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            log_tool_result(logger, "serper_search", inputs_hash, str(e), duration_ms, request_id, False)
            raise e

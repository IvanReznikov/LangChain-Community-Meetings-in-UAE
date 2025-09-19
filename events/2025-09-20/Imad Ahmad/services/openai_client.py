import os
import json
from typing import Dict, Any, List
from openai import OpenAI
from agent.schemas import ItineraryPlan
from agent.reliability import reliable_service_call
from observability.logger import setup_logger, log_tool_call, log_tool_result
import time
import uuid

logger = setup_logger()


class OpenAIClient:
    """Wrapper for OpenAI API with function calling and safe decoding."""
    
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.model = os.getenv("MODEL", "gpt-4o-mini")
        
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required")
        
        self.client = OpenAI(api_key=self.api_key)
    
    @reliable_service_call("openai", timeout=30, retries=2)
    def generate_itinerary(self, 
                          destination: str, 
                          days: int, 
                          budget_amount: float, 
                          budget_currency: str,
                          search_results: List[Dict[str, Any]] = None,
                          context: str = "") -> ItineraryPlan:
        """Generate travel itinerary using OpenAI function calling."""
        request_id = str(uuid.uuid4())
        start_time = time.time()
        
        inputs = {
            "destination": destination,
            "days": days,
            "budget_amount": budget_amount,
            "budget_currency": budget_currency,
            "search_results_count": len(search_results) if search_results else 0
        }
        inputs_hash = log_tool_call(logger, "openai_generate_itinerary", inputs, request_id)
        
        try:
            # Prepare system message
            system_message = f"""You are a travel planning assistant. Create a detailed {days}-day itinerary for {destination} 
            with a budget of {budget_amount} {budget_currency}.

            CRITICAL REQUIREMENTS:
            - MUST create activities for ALL {days} days (Day 1, Day 2, Day 3, etc.)
            - Each day should have 2-3 activities minimum
            - Distribute budget evenly across all {days} days
            - Extract ACTUAL prices from the search results provided
            - Use REAL URLs from search results as sources
            - If search results show "AED 169" or "$45", use those exact prices
            - Convert currencies accurately using the currency tool if needed
            - Stay within budget (allow 5% headroom)
            - Prioritize activities with confirmed pricing from search results
            - Include the actual source URL from search results, not placeholder URLs
            
            DAY DISTRIBUTION REQUIREMENTS:
            - Day 1: Arrival activities, major attractions
            - Day 2: Cultural experiences, local exploration
            - Day 3: Shopping, departure activities
            - Continue pattern for additional days
            - Include mix of paid and free activities on each day
            
            PRICING EXTRACTION INSTRUCTIONS:
            - Look for price patterns like "AED 169", "$45", "from $30", "starting at 25 USD"
            - Extract the numerical value and currency from search snippets
            - Use the exact URL provided in the search result as the source
            - If no price is found in search results, estimate conservatively
            - Budget per day should be approximately {budget_amount / days:.2f} {budget_currency}
            
            Budget constraint: Total cost must not exceed {budget_amount * 1.05} {budget_currency}
            """
            
            # Prepare user message with search context
            user_message = f"Plan a {days}-day trip to {destination} with budget {budget_amount} {budget_currency}."
            
            if search_results:
                search_context = "\n\nAvailable pricing information from search (USE THESE EXACT PRICES AND URLS):\n"
                for i, result in enumerate(search_results[:15], 1):  # More results for better pricing
                    title = result.get('title', '')
                    snippet = result.get('snippet', '')
                    url = result.get('url', '')
                    search_context += f"{i}. TITLE: {title}\n"
                    search_context += f"   PRICE INFO: {snippet}\n"
                    search_context += f"   SOURCE URL: {url}\n\n"
                user_message += search_context
                
                user_message += f"\nIMPORTANT: Extract exact prices from the snippets above and use the corresponding URLs as sources. Look for patterns like 'AED 169', '$45', 'from 30 USD', etc.\n\nREMINDER: You MUST create activities for ALL {days} days. Do not create only 1 day of activities."
            
            if context:
                user_message += f"\n\nAdditional context: {context}"
            
            # Define function schema for structured output
            function_schema = {
                "name": "create_itinerary",
                "description": "Create a structured travel itinerary",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "destination": {"type": "string"},
                        "days": {"type": "integer"},
                        "total_estimated_cost": {"type": "number"},
                        "currency": {"type": "string"},
                        "items": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "day": {"type": "integer"},
                                    "activity": {"type": "string"},
                                    "approx_cost": {"type": "number"},
                                    "currency": {"type": "string"},
                                    "source": {"type": "string", "description": "URL source if available"}
                                },
                                "required": ["day", "activity", "approx_cost", "currency"]
                            }
                        },
                        "under_budget": {"type": "boolean"},
                        "notes": {"type": "string"}
                    },
                    "required": ["destination", "days", "total_estimated_cost", "currency", "items", "under_budget", "notes"]
                }
            }
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": user_message}
                ],
                functions=[function_schema],
                function_call={"name": "create_itinerary"},
                temperature=0.7,
                timeout=30
            )
            
            # Extract function call result
            function_call = response.choices[0].message.function_call
            if not function_call or function_call.name != "create_itinerary":
                raise ValueError("OpenAI did not return expected function call")
            
            # Parse the JSON response
            try:
                itinerary_data = json.loads(function_call.arguments)
            except json.JSONDecodeError as e:
                raise ValueError(f"Failed to parse OpenAI response as JSON: {e}")
            
            # Create and validate the itinerary plan
            itinerary_plan = ItineraryPlan(**itinerary_data)
            
            duration_ms = int((time.time() - start_time) * 1000)
            log_tool_result(logger, "openai_generate_itinerary", inputs_hash, 
                          f"Generated {len(itinerary_plan.items)} activities", duration_ms, request_id, True)
            
            return itinerary_plan
            
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            log_tool_result(logger, "openai_generate_itinerary", inputs_hash, str(e), duration_ms, request_id, False)
            raise e
    
    @reliable_service_call("openai", timeout=15, retries=1)
    def compress_context(self, conversation_history: str) -> str:
        """Compress conversation history to a compact memo."""
        request_id = str(uuid.uuid4())
        start_time = time.time()
        
        inputs = {"history_length": len(conversation_history)}
        inputs_hash = log_tool_call(logger, "openai_compress_context", inputs, request_id)
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "Summarize the following conversation into a compact memo that preserves key travel preferences, constraints, and decisions. Keep it under 200 words."
                    },
                    {
                        "role": "user",
                        "content": conversation_history
                    }
                ],
                temperature=0.3,
                max_tokens=250,
                timeout=15
            )
            
            compressed = response.choices[0].message.content.strip()
            
            duration_ms = int((time.time() - start_time) * 1000)
            log_tool_result(logger, "openai_compress_context", inputs_hash, 
                          f"Compressed to {len(compressed)} chars", duration_ms, request_id, True)
            
            return compressed
            
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            log_tool_result(logger, "openai_compress_context", inputs_hash, str(e), duration_ms, request_id, False)
            raise e

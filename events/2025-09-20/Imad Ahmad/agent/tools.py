import json
import sympy
from typing import List, Dict, Any
from services.serper_client import SerperClient
from agent.schemas import SearchResult
from agent.reliability import reliable_service_call
from observability.logger import setup_logger, log_tool_call, log_tool_result
import time
import uuid

logger = setup_logger()


def search_tool(query: str) -> List[Dict[str, Any]]:
    """Search for travel information using Serper API."""
    try:
        serper_client = SerperClient()
        results = serper_client.search(query, num_results=5)
        return [
            {
                "title": result.title,
                "url": result.url,
                "snippet": result.snippet
            }
            for result in results
        ]
    except Exception as e:
        logger.error("Search tool failed", error=str(e), query=query)
        return []


@reliable_service_call("calculator", timeout=5, retries=1)
def calculator_tool(expression: str) -> float:
    """Safely evaluate mathematical expression."""
    request_id = str(uuid.uuid4())
    start_time = time.time()
    
    inputs = {"expression": expression}
    inputs_hash = log_tool_call(logger, "calculator", inputs, request_id)
    
    try:
        # Replace common operators that might be written in text
        expression = expression.replace("×", "*").replace("÷", "/")
        
        # Use sympy to safely evaluate
        result = float(sympy.sympify(expression, locals={}))
        
        duration_ms = int((time.time() - start_time) * 1000)
        log_tool_result(logger, "calculator", inputs_hash, result, duration_ms, request_id, True)
        
        return result
        
    except (sympy.SympifyError, ValueError, TypeError) as e:
        duration_ms = int((time.time() - start_time) * 1000)
        log_tool_result(logger, "calculator", inputs_hash, str(e), duration_ms, request_id, False)
        raise ValueError(f"Invalid mathematical expression: {expression}")


@reliable_service_call("currency", timeout=2, retries=1)
def currency_tool(amount: float, from_currency: str, to_currency: str) -> float:
    """Convert currency using fixed rates."""
    request_id = str(uuid.uuid4())
    start_time = time.time()
    
    inputs = {"amount": amount, "from_currency": from_currency, "to_currency": to_currency}
    inputs_hash = log_tool_call(logger, "currency_conversion", inputs, request_id)
    
    # Fixed exchange rates for demo predictability
    EXCHANGE_RATES = {
        ("USD", "AED"): 3.67,
        ("AED", "USD"): 1/3.67,
        ("EUR", "USD"): 1.10,
        ("USD", "EUR"): 1/1.10,
        ("EUR", "AED"): 4.04,
        ("AED", "EUR"): 1/4.04,
        ("GBP", "USD"): 1.25,
        ("USD", "GBP"): 1/1.25,
        ("GBP", "AED"): 4.59,
        ("AED", "GBP"): 1/4.59,
    }
    
    try:
        # Same currency, no conversion needed
        if from_currency.upper() == to_currency.upper():
            result = amount
        else:
            # Look up exchange rate
            rate_key = (from_currency.upper(), to_currency.upper())
            if rate_key in EXCHANGE_RATES:
                rate = EXCHANGE_RATES[rate_key]
                result = amount * rate
            else:
                # Default fallback rate (assume USD base)
                logger.warning(f"No exchange rate found for {from_currency} to {to_currency}, using 1:1")
                result = amount
        
        duration_ms = int((time.time() - start_time) * 1000)
        log_tool_result(logger, "currency_conversion", inputs_hash, result, duration_ms, request_id, True)
        
        return round(result, 2)
        
    except Exception as e:
        duration_ms = int((time.time() - start_time) * 1000)
        log_tool_result(logger, "currency_conversion", inputs_hash, str(e), duration_ms, request_id, False)
        raise e

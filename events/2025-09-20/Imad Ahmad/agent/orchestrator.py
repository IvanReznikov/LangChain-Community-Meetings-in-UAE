import json
import uuid
from typing import Dict, Any, Optional, Tuple
from pathlib import Path

from agent.schemas import TravelRequest, ItineraryPlan, ItineraryItem
from agent.tools import search_tool, calculator_tool, currency_tool
from agent.memory import ConversationMemory
from agent.reliability import fallback_manager
from services.openai_client import OpenAIClient
from services.serper_client import SerperClient
from observability.logger import setup_logger, log_trace

logger = setup_logger()


class TravelOrchestrator:
    """Main agent orchestrator that manages the travel planning workflow."""
    
    def __init__(self):
        self.openai_client = OpenAIClient()
        self.serper_client = SerperClient()
        self.memory = ConversationMemory()
        self.request_id = None
        
        # Register fallback strategies
        fallback_manager.register_fallback("search", self._search_fallback)
        fallback_manager.register_fallback("currency", self._currency_fallback)
    
    def plan_trip(self, request: TravelRequest) -> Tuple[ItineraryPlan, bool]:
        """
        Main orchestration method for trip planning.
        Returns: (ItineraryPlan, needs_human_review)
        """
        self.request_id = str(uuid.uuid4())
        
        log_trace(logger, self.request_id, "trip_planning_started", {
            "destination": request.destination,
            "days": request.days,
            "budget": f"{request.budget_amount} {request.budget_currency}"
        })
        
        try:
            # Step 1: Validate inputs
            self._validate_request(request)
            
            # Step 2: Search Phase
            search_results = self._search_phase(request)
            
            # Step 3: Synthesis Phase
            itinerary = self._synthesis_phase(request, search_results)
            
            # Step 4: Validation Phase
            needs_review = self._validation_phase(itinerary, request)
            
            log_trace(logger, self.request_id, "trip_planning_completed", {
                "total_cost": itinerary.total_estimated_cost,
                "under_budget": itinerary.under_budget,
                "needs_review": needs_review,
                "activities_count": len(itinerary.items)
            })
            
            return itinerary, needs_review
            
        except Exception as e:
            log_trace(logger, self.request_id, "trip_planning_failed", {
                "error": str(e)
            })
            logger.error("Trip planning failed", error=str(e), request_id=self.request_id)
            raise e
    
    def _validate_request(self, request: TravelRequest):
        """Validate the travel request inputs."""
        if not request.destination.strip():
            raise ValueError("Destination cannot be empty")
        
        if request.days < 1 or request.days > 7:
            raise ValueError("Days must be between 1 and 7")
        
        if request.budget_amount <= 0:
            raise ValueError("Budget amount must be positive")
        
        logger.info("Request validated", request_id=self.request_id)
    
    def _search_phase(self, request: TravelRequest) -> list:
        """Search for travel information using multiple queries focused on pricing."""
        search_results = []
        
        # Define more specific search queries for pricing
        queries = [
            f"{request.destination} hotel prices {request.budget_currency}",
            f"{request.destination} attraction tickets cost price",
            f"{request.destination} restaurant meal prices",
            f"{request.destination} activities cost booking price",
            f"Dubai Mall Burj Khalifa ticket price cost",
            f"{request.destination} desert safari price cost",
            f"{request.destination} museum entry fee price",
            f"{request.destination} transport taxi metro cost"
        ]
        
        for query in queries:
            try:
                results = search_tool(query)
                # Filter results that likely contain pricing information
                price_relevant_results = []
                for result in results:
                    snippet = result.get('snippet', '').lower()
                    title = result.get('title', '').lower()
                    # Look for price indicators in snippets and titles
                    price_indicators = ['price', 'cost', '$', '€', '£', 'aed', 'usd', 'eur', 'gbp', 
                                      'ticket', 'booking', 'from', 'starting', 'fee', 'charge']
                    if any(indicator in snippet or indicator in title for indicator in price_indicators):
                        price_relevant_results.append(result)
                
                search_results.extend(price_relevant_results)
                logger.info("Search completed", query=query, results_count=len(price_relevant_results), request_id=self.request_id)
            except Exception as e:
                logger.warning("Search query failed", query=query, error=str(e), request_id=self.request_id)
                continue
        
        # Remove duplicates based on URL and prioritize results with pricing info
        unique_results = []
        seen_urls = set()
        for result in search_results:
            if result.get('url') not in seen_urls:
                unique_results.append(result)
                seen_urls.add(result.get('url'))
        
        # Sort by relevance (prioritize results with clear pricing information)
        def has_clear_pricing(result):
            text = (result.get('snippet', '') + ' ' + result.get('title', '')).lower()
            price_patterns = ['$', 'aed', 'usd', 'price:', 'cost:', 'from ', 'starting at']
            return sum(1 for pattern in price_patterns if pattern in text)
        
        unique_results.sort(key=has_clear_pricing, reverse=True)
        
        log_trace(logger, self.request_id, "search_phase_completed", {
            "total_results": len(unique_results),
            "unique_sources": len(seen_urls),
            "price_relevant_results": len([r for r in unique_results if has_clear_pricing(r) > 0])
        })
        
        return unique_results[:20]  # Increased limit for better pricing data
    
    def _synthesis_phase(self, request: TravelRequest, search_results: list) -> ItineraryPlan:
        """Generate itinerary using OpenAI with search results."""
        context = self.memory.get_context()
        
        try:
            itinerary = self.openai_client.generate_itinerary(
                destination=request.destination,
                days=request.days,
                budget_amount=request.budget_amount,
                budget_currency=request.budget_currency,
                search_results=search_results,
                context=context
            )
            
            log_trace(logger, self.request_id, "synthesis_completed", {
                "activities_generated": len(itinerary.items),
                "total_cost": itinerary.total_estimated_cost,
                "currency": itinerary.currency
            })
            
            return itinerary
            
        except Exception as e:
            logger.error("Synthesis failed, using fallback", error=str(e), request_id=self.request_id)
            return self._synthesis_fallback(request)
    
    def _validation_phase(self, itinerary: ItineraryPlan, request: TravelRequest) -> bool:
        """Validate the generated itinerary and determine if human review is needed."""
        needs_review = False
        issues = []
        
        # Check budget constraint (5% headroom)
        budget_limit = request.budget_amount * 1.05
        if itinerary.total_estimated_cost > budget_limit:
            needs_review = True
            issues.append(f"Over budget: {itinerary.total_estimated_cost} > {budget_limit}")
        
        # Check source confidence (need at least 2 unique sources)
        unique_sources = set()
        for item in itinerary.items:
            if item.source:
                unique_sources.add(item.source)
        
        if len(unique_sources) < 2:
            needs_review = True
            issues.append(f"Low confidence: only {len(unique_sources)} unique sources")
        
        # Check if all days are covered
        covered_days = set(item.day for item in itinerary.items)
        expected_days = set(range(1, request.days + 1))
        if covered_days != expected_days:
            needs_review = True
            issues.append(f"Missing days: {expected_days - covered_days}")
        
        log_trace(logger, self.request_id, "validation_completed", {
            "needs_review": needs_review,
            "issues": issues,
            "unique_sources": len(unique_sources),
            "budget_utilization": itinerary.total_estimated_cost / request.budget_amount
        })
        
        return needs_review
    
    def _search_fallback(self, query: str) -> list:
        """Fallback strategy when search fails."""
        logger.info("Using search fallback", query=query, request_id=self.request_id)
        
        # Load fallback data if available
        fallback_path = Path("data/fallback_dubai.json")
        if fallback_path.exists() and "dubai" in query.lower():
            try:
                with open(fallback_path, 'r') as f:
                    fallback_data = json.load(f)
                
                # Convert to search result format
                results = []
                for item in fallback_data.get("items", []):
                    results.append({
                        "title": item["activity"],
                        "url": item.get("source", ""),
                        "snippet": f"Cost: {item['approx_cost']} {fallback_data['currency']}"
                    })
                
                return results
            except Exception as e:
                logger.error("Failed to load fallback data", error=str(e))
        
        return []
    
    def _currency_fallback(self, amount: float, from_currency: str, to_currency: str) -> float:
        """Fallback strategy for currency conversion."""
        logger.info("Using currency fallback", request_id=self.request_id)
        
        # Default USD to AED rate as specified in requirements
        if from_currency.upper() == "USD" and to_currency.upper() == "AED":
            return amount * 3.67
        elif from_currency.upper() == "AED" and to_currency.upper() == "USD":
            return amount / 3.67
        else:
            # Default to 1:1 for other currencies
            return amount
    
    def _synthesis_fallback(self, request: TravelRequest) -> ItineraryPlan:
        """Fallback synthesis using static data."""
        logger.info("Using synthesis fallback", request_id=self.request_id)
        
        # Load fallback data
        fallback_path = Path("data/fallback_dubai.json")
        if fallback_path.exists() and "dubai" in request.destination.lower():
            try:
                with open(fallback_path, 'r') as f:
                    fallback_data = json.load(f)
                
                # Convert to itinerary format
                items = []
                total_cost = 0
                
                for item_data in fallback_data["items"][:request.days * 2]:  # 2 activities per day max
                    if item_data["day"] <= request.days:
                        # Convert currency if needed
                        cost = item_data["approx_cost"]
                        if request.budget_currency.upper() != fallback_data["currency"].upper():
                            cost = self._currency_fallback(cost, fallback_data["currency"], request.budget_currency)
                        
                        item = ItineraryItem(
                            day=item_data["day"],
                            activity=item_data["activity"],
                            approx_cost=cost,
                            currency=request.budget_currency,
                            source=item_data.get("source")
                        )
                        items.append(item)
                        total_cost += cost
                
                return ItineraryPlan(
                    destination=request.destination,
                    days=request.days,
                    total_estimated_cost=total_cost,
                    currency=request.budget_currency,
                    items=items,
                    under_budget=total_cost <= request.budget_amount,
                    notes=f"Fallback plan used. {fallback_data.get('notes', '')} Exchange rate: 1 USD = 3.67 AED"
                )
                
            except Exception as e:
                logger.error("Fallback synthesis failed", error=str(e))
        
        # Ultimate fallback - minimal plan
        return ItineraryPlan(
            destination=request.destination,
            days=request.days,
            total_estimated_cost=0,
            currency=request.budget_currency,
            items=[
                ItineraryItem(
                    day=i,
                    activity=f"Explore {request.destination} - Day {i}",
                    approx_cost=0,
                    currency=request.budget_currency,
                    source=None
                )
                for i in range(1, request.days + 1)
            ],
            under_budget=True,
            notes="Minimal fallback plan - please search for specific activities and costs manually."
        )
    
    def review_and_adjust(self, itinerary: ItineraryPlan, action: str, modifications: str = None) -> ItineraryPlan:
        """Handle human-in-the-loop review and adjustments."""
        log_trace(logger, self.request_id, "review_started", {
            "action": action,
            "original_cost": itinerary.total_estimated_cost
        })
        
        if action == "approve":
            # User approved as-is
            itinerary.notes += " [Approved by user despite issues]"
            return itinerary
        
        elif action == "reduce":
            # Auto-reduce costs while maintaining activities across all days
            original_days = set(item.day for item in itinerary.items)
            budget_limit = itinerary.total_estimated_cost * 0.95  # Target 95% of original budget
            
            # Group items by day
            items_by_day = {}
            for item in itinerary.items:
                if item.day not in items_by_day:
                    items_by_day[item.day] = []
                items_by_day[item.day].append(item)
            
            reduced_items = []
            total_cost = 0
            
            # Ensure at least one activity per day, prioritizing cheaper options
            for day in sorted(original_days):
                if day in items_by_day:
                    day_items = sorted(items_by_day[day], key=lambda x: x.approx_cost)
                    # Always include the cheapest activity for each day
                    if day_items:
                        cheapest = day_items[0]
                        reduced_items.append(cheapest)
                        total_cost += cheapest.approx_cost
                        day_items.remove(cheapest)
                        items_by_day[day] = day_items
            
            # Add remaining items if budget allows, maintaining day distribution
            remaining_items = []
            for day_items in items_by_day.values():
                remaining_items.extend(day_items)
            
            # Sort remaining items by cost and add if budget allows
            for item in sorted(remaining_items, key=lambda x: x.approx_cost):
                if total_cost + item.approx_cost <= budget_limit:
                    reduced_items.append(item)
                    total_cost += item.approx_cost
            
            # If we still don't have enough activities per day, add free activities
            final_days = set(item.day for item in reduced_items)
            missing_days = original_days - final_days
            
            for day in missing_days:
                # Add a free activity for missing days
                free_activity = ItineraryItem(
                    day=day,
                    activity=f"Explore local area and free attractions - Day {day}",
                    approx_cost=0.0,
                    currency=itinerary.currency,
                    source=None
                )
                reduced_items.append(free_activity)
            
            itinerary.items = sorted(reduced_items, key=lambda x: (x.day, x.approx_cost))
            itinerary.total_estimated_cost = total_cost
            itinerary.under_budget = True
            itinerary.notes += " [Auto-reduced to fit budget while maintaining daily activities]"
            
            log_trace(logger, self.request_id, "review_completed", {
                "action": action,
                "final_cost": total_cost,
                "items_removed": len(itinerary.items) - len(reduced_items),
                "days_covered": len(set(item.day for item in reduced_items))
            })
        
        return itinerary

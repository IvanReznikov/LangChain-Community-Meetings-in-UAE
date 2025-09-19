from pydantic import BaseModel, Field
from typing import Optional, List


class ItineraryItem(BaseModel):
    day: int = Field(..., description="Day number of the itinerary")
    activity: str = Field(..., description="Activity description")
    approx_cost: float = Field(..., description="Approximate cost of the activity")
    currency: str = Field(..., description="Currency code (e.g., USD, AED)")
    source: Optional[str] = Field(None, description="URL source if from search")


class ItineraryPlan(BaseModel):
    destination: str = Field(..., description="Travel destination")
    days: int = Field(..., description="Number of days for the trip")
    total_estimated_cost: float = Field(..., description="Total estimated cost of all activities")
    currency: str = Field(..., description="Currency code for the budget")
    items: List[ItineraryItem] = Field(..., description="List of itinerary items")
    under_budget: bool = Field(..., description="Whether the plan is within budget")
    notes: str = Field(..., description="Assumptions, caveats, exchange rate used")


class TravelRequest(BaseModel):
    destination: str = Field(..., description="Travel destination")
    days: int = Field(..., ge=1, le=7, description="Number of days (1-7)")
    budget_currency: str = Field(..., description="Budget currency code")
    budget_amount: float = Field(..., gt=0, description="Budget amount (must be positive)")


class SearchResult(BaseModel):
    title: str = Field(..., description="Search result title")
    url: str = Field(..., description="Search result URL")
    snippet: str = Field(..., description="Search result snippet")


class ReviewRequest(BaseModel):
    request_id: str = Field(..., description="Original request ID")
    action: str = Field(..., description="User action: 'approve' or 'reduce'")
    modifications: Optional[str] = Field(None, description="Optional modifications requested")

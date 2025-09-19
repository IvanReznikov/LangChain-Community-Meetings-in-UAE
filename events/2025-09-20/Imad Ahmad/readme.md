You are a senior AI engineer. Build a minimal, reliable demo app called Travel Assistant to showcase “Building Reliable Agent Workflows with LangChain’s Message & Tool Abstractions”.

Goals

Input: destination, days, budget_currency, budget_amount.

Output: A 3-day itinerary (activities + costs) that stays within budget, with sources where applicable.

Must demonstrate reliability patterns: context management, fallbacks, timeouts & retries, circuit breaker, observability, and human-in-the-loop checkpoint.

Tech Stack

Python (fast to demo) with LangChain (stable 0.3.x) for production-readiness.
(If you add a branch using the 1.0 alpha message/tool abstractions, keep it separate and clearly labeled.)

OpenAI API (chat + function calling).

Serper API for web search (Google results).

FastAPI backend + Streamlit or minimal React/Vite frontend (choose Streamlit if time is tight).

SQLite for simple persistence (logs & cached results).

Logging: structlog or Python logging with JSON formatter.

.env
OPENAI_API_KEY=...
SERPER_API_KEY=...
MODEL=OpenAI GPT-4o Mini (or latest stable)

Architecture (Clean & Observable)

app/

main.py (FastAPI routes) or ui.py (Streamlit)

agent/

orchestrator.py (agent loop & middleware)

tools.py (search_tool, currency_tool, calculator_tool)

schemas.py (Pydantic: inputs/outputs)

reliability.py (retries, timeouts, circuit breaker, fallbacks)

memory.py (context compression/summarization)

services/

serper_client.py (typed client w/ timeouts & retries)

openai_client.py (wrapper w/ function calling + safe decoding)

data/ (fallback lists, cached responses)

tests/ (unit + e2e)

observability/ (logger + request/response traces)

Tools (LangChain)

search_tool(query: str) -> SearchResults[]

Uses Serper API.

Timeout 5s, retry 2x exponential backoff.

Returns top 5 items: {title, url, snippet}.

calculator_tool(expression: str) -> float

Safe eval (or sympy); reject unsafe input.

currency_tool(amount, from_ccy, to_ccy) -> float

Stub/mocked (or fixed AED/USD rates) for demo predictability.

Output Schema (Pydantic)
class ItineraryItem(BaseModel):
day: int
activity: str
approx_cost: float
currency: str
source: Optional[str] = None # URL if from search

class ItineraryPlan(BaseModel):
destination: str
days: int
total_estimated_cost: float
currency: str
items: list[ItineraryItem]
under_budget: bool
notes: str # assumptions, caveats, exchange rate used

Reliability Requirements (Non-negotiable)

Context Management: Summarize chat history > 8 turns; store a compact “conversation memo” (memory.py).

Fallbacks:

If search fails or times out → use data/fallback_dubai.json curated list (see below).

If currency API fails → default to 1 USD = 3.67 AED (note in notes).

Timeouts & Retries: All outbound calls have 5s timeout; 2 retries with jitter.

Circuit Breaker: If 3 consecutive Serper errors within 60s → open circuit for 2 minutes → force fallback immediately.

Observability:

Log every tool call (started, succeeded|failed, duration, inputs hash, output size).

Store traces (request_id) in SQLite for demo.

Human-in-the-Loop:

If budget is exceeded or sources are low-confidence (e.g., <2 results), pause and return a “Review Required” state for the user to approve or reduce activities.

Deterministic Demo Behavior

For Dubai demo, prefer well-known attractions to keep results stable.

Use budget guardrails: keep total_estimated_cost <= budget_amount \* 1.05 (5% headroom), else trigger HiTL.

Fallback Data (data/fallback_dubai.json)
{
"currency": "AED",
"items": [
{"day": 1, "activity": "Dubai Mall & Fountain Show", "approx_cost": 0, "source": "https://www.thedubaimall.com"},
{"day": 1, "activity": "Burj Khalifa At The Top (124/125)", "approx_cost": 169, "source": "https://www.burjkhalifa.ae"},
{"day": 2, "activity": "Old Dubai: Al Fahidi & Creek Abra Ride", "approx_cost": 2, "source": "https://www.visitdubai.com"},
{"day": 2, "activity": "Gold & Spice Souk Walk", "approx_cost": 0, "source": "https://www.visitdubai.com"},
{"day": 3, "activity": "JBR Beach Walk", "approx_cost": 0, "source": "https://www.jbr.ae"},
{"day": 3, "activity": "Desert Safari (Shared)", "approx_cost": 150, "source": "https://www.getyourguide.com"}
],
"notes": "Transport & meals not included; prices indicative."
}

Agent Orchestration (Pseudo)

Validate inputs (destination, days 1-7, budget > 0).

Generate initial plan structure.

Search Phase (Serper):

Query templates: “top attractions in {destination}”, “budget things to do {destination}”, “ticket price {attraction}”.

If timeout/CB open → skip to Fallback Phase.

Synthesis Phase (OpenAI):

Combine search snippets + calculator + currency conversions.

Enforce budget via tool calls.

Produce ItineraryPlan JSON strictly (use JSON schema/function calling).

Validation Phase:

Sum approx_cost ≤ budget\*1.05, else HiTL checkpoint.

If <2 unique sources → HiTL checkpoint.

Return final plan with under_budget, notes.

API

POST /plan → body {destination, days, budget_currency, budget_amount} → returns ItineraryPlan.

POST /review → accepts user approval/edits if HiTL triggered; re-plan then return final.

UI (Streamlit: simple but clean)

Top: Title “Travel Assistant (Reliable Agent Demo)”.

Left panel: Inputs (destination, days, currency, budget).

Main:

Spinner with “Agent running…” and live log tail (tool calls + timings).

If HiTL: show diff (over-budget or low-confidence) + “Approve Anyway” or “Auto-reduce costs” button.

Final card grid: Day-wise activities, costs, source links, total vs budget meter.

Add a minimalist “windsurfer” visual theme (blue/teal accent, wave divider, lightweight icons). Keep whitespace, large readable headings.

Tests

Unit: search_tool (timeouts, retries, parsing), calculator (edge expressions), circuit breaker.

Integration: /plan returns valid ItineraryPlan; over-budget triggers HiTL.

Determinism: with network disabled → uses fallback JSON only; still returns a valid plan.

Non-Functional

Code linting (ruff/black).

Type hints (mypy ok).

Clear README with run steps, demo script, and reliability map (where each pattern is implemented).

Deliverables

Complete repo ready to pip install -r requirements.txt && streamlit run app/ui.py (or uvicorn app.main:app if FastAPI + small HTML).

Sample .env.example.

data/fallback_dubai.json.

Screenshots/GIF for README.

Demo Script (for presenter)

Run normal query → show logs, plan under budget.

Toggle a “Simulate Search Failure” checkbox → show fallback kicks in, still returns plan.

Set an unrealistically low budget → trigger HiTL; approve reduced plan; show final result within budget.

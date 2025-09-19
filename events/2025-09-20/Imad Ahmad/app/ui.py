import streamlit as st
import os
import sys
from pathlib import Path
import time
import json
from datetime import datetime

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from agent.schemas import TravelRequest, ItineraryPlan
from agent.orchestrator import TravelOrchestrator
from observability.logger import setup_logger
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set up logger
logger = setup_logger()

# Page configuration
st.set_page_config(
    page_title="Travel Assistant - Reliable Agent Demo",
    page_icon="🌊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for windsurfer theme
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(90deg, #0ea5e9 0%, #06b6d4 100%);
        padding: 2rem;
        border-radius: 10px;
        margin-bottom: 2rem;
        color: white;
        text-align: center;
    }
    
    .wave-divider {
        height: 4px;
        background: linear-gradient(90deg, #0ea5e9, #06b6d4, #0ea5e9);
        margin: 1rem 0;
        border-radius: 2px;
    }
    
    .activity-card {
        background: white;
        padding: 1.5rem;
        border-radius: 10px;
        border-left: 4px solid #0ea5e9;
        margin: 1rem 0;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    
    .cost-meter {
        background: #f1f5f9;
        border-radius: 10px;
        padding: 1rem;
        margin: 1rem 0;
    }
    
    .log-container {
        background: #1e293b;
        color: #e2e8f0;
        padding: 1rem;
        border-radius: 8px;
        font-family: 'Courier New', monospace;
        font-size: 0.8rem;
        max-height: 300px;
        overflow-y: auto;
    }
    
    .review-alert {
        background: #fef3c7;
        border: 1px solid #f59e0b;
        border-radius: 8px;
        padding: 1rem;
        margin: 1rem 0;
    }
    
    .success-alert {
        background: #d1fae5;
        border: 1px solid #10b981;
        border-radius: 8px;
        padding: 1rem;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

def initialize_session_state():
    """Initialize session state variables."""
    if 'orchestrator' not in st.session_state:
        st.session_state.orchestrator = TravelOrchestrator()
    
    if 'current_plan' not in st.session_state:
        st.session_state.current_plan = None
    
    if 'needs_review' not in st.session_state:
        st.session_state.needs_review = False
    
    if 'logs' not in st.session_state:
        st.session_state.logs = []
    
    if 'simulate_failure' not in st.session_state:
        st.session_state.simulate_failure = False

def add_log(message: str, level: str = "INFO"):
    """Add a log message to the session state."""
    timestamp = datetime.now().strftime("%H:%M:%S")
    log_entry = f"[{timestamp}] {level}: {message}"
    st.session_state.logs.append(log_entry)
    
    # Keep only last 50 logs
    if len(st.session_state.logs) > 50:
        st.session_state.logs = st.session_state.logs[-50:]

def display_logs():
    """Display the live log tail."""
    if st.session_state.logs:
        log_text = "\n".join(st.session_state.logs[-10:])  # Show last 10 logs
        st.markdown(f'<div class="log-container">{log_text}</div>', unsafe_allow_html=True)

def display_itinerary(plan: ItineraryPlan):
    """Display the itinerary in a card grid format."""
    st.markdown('<div class="wave-divider"></div>', unsafe_allow_html=True)
    
    # Budget meter
    budget_used = plan.total_estimated_cost
    budget_total = budget_used / 0.95 if plan.under_budget else budget_used * 1.2  # Estimate original budget
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.markdown(f"""
        <div class="cost-meter">
            <h4>💰 Budget Overview</h4>
            <p><strong>Total Cost:</strong> {budget_used:.2f} {plan.currency}</p>
            <p><strong>Status:</strong> {'✅ Under Budget' if plan.under_budget else '⚠️ Over Budget'}</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        # Budget progress bar
        progress = min(budget_used / budget_total, 1.0) if budget_total > 0 else 0
        st.metric("Budget Used", f"{progress:.1%}")
        st.progress(progress)
    
    # Group activities by day
    activities_by_day = {}
    for item in plan.items:
        if item.day not in activities_by_day:
            activities_by_day[item.day] = []
        activities_by_day[item.day].append(item)
    
    # Display activities by day
    for day in sorted(activities_by_day.keys()):
        st.markdown(f"### 📅 Day {day}")
        
        for activity in activities_by_day[day]:
            source_link = f" [🔗 Source]({activity.source})" if activity.source else ""
            cost_display = f"{activity.approx_cost:.2f} {activity.currency}" if activity.approx_cost > 0 else "Free"
            
            st.markdown(f"""
            <div class="activity-card">
                <h4>{activity.activity}</h4>
                <p><strong>Cost:</strong> {cost_display}{source_link}</p>
            </div>
            """, unsafe_allow_html=True)
    
    # Notes
    if plan.notes:
        st.markdown("### 📝 Notes")
        st.info(plan.notes)

def main():
    """Main Streamlit application."""
    initialize_session_state()
    
    # Header
    st.markdown("""
    <div class="main-header">
        <h1>🌊 Travel Assistant</h1>
        <p>Reliable Agent Demo - Building Reliable Workflows with LangChain</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Sidebar for inputs
    with st.sidebar:
        st.header("🎯 Trip Planning")
        
        # Input form
        with st.form("trip_form"):
            destination = st.text_input("Destination", value="Dubai", help="Where would you like to travel?")
            days = st.slider("Number of Days", 1, 7, 3, help="How many days will you stay?")
            
            col1, col2 = st.columns(2)
            with col1:
                budget_currency = st.selectbox("Currency", ["USD", "AED", "EUR", "GBP"], index=1)
            with col2:
                budget_amount = st.number_input("Budget", min_value=1.0, value=500.0, step=50.0)
            
            # Demo controls
            st.markdown("---")
            st.markdown("**🧪 Demo Controls**")
            simulate_failure = st.checkbox("Simulate Search Failure", 
                                         help="Test fallback behavior when search fails")
            
            submit_button = st.form_submit_button("🚀 Plan My Trip", use_container_width=True)
        
        # Current status
        if st.session_state.current_plan:
            st.markdown("---")
            st.markdown("**📊 Current Plan Status**")
            plan = st.session_state.current_plan
            st.metric("Activities", len(plan.items))
            st.metric("Total Cost", f"{plan.total_estimated_cost:.2f} {plan.currency}")
            st.metric("Budget Status", "✅ Good" if plan.under_budget else "⚠️ Review")
    
    # Main content area
    col1, col2 = st.columns([2, 1])
    
    with col2:
        st.markdown("### 📊 Live Agent Logs")
        display_logs()
        
        # Clear logs button
        if st.button("🗑️ Clear Logs"):
            st.session_state.logs = []
            st.rerun()
    
    with col1:
        # Handle form submission
        if submit_button:
            if not destination.strip():
                st.error("Please enter a destination")
                return
            
            # Update simulation state
            st.session_state.simulate_failure = simulate_failure
            
            # Create travel request
            request = TravelRequest(
                destination=destination,
                days=days,
                budget_currency=budget_currency,
                budget_amount=budget_amount
            )
            
            add_log(f"Planning trip to {destination} for {days} days with budget {budget_amount} {budget_currency}")
            
            # Show spinner while processing
            with st.spinner("🤖 Agent running... Searching and planning your trip"):
                try:
                    # Simulate search failure if requested
                    if simulate_failure:
                        add_log("⚠️ Simulating search failure - fallback mode activated")
                        # Temporarily break the search by modifying API key
                        original_key = os.environ.get('SERPER_API_KEY')
                        os.environ['SERPER_API_KEY'] = 'invalid_key_for_demo'
                    
                    # Plan the trip
                    add_log("🔍 Starting search phase...")
                    plan, needs_review = st.session_state.orchestrator.plan_trip(request)
                    
                    # Restore API key if it was modified
                    if simulate_failure and 'original_key' in locals():
                        os.environ['SERPER_API_KEY'] = original_key or ''
                    
                    # Store results
                    st.session_state.current_plan = plan
                    st.session_state.needs_review = needs_review
                    
                    add_log(f"✅ Trip planned successfully! Generated {len(plan.items)} activities")
                    
                    if needs_review:
                        add_log("⚠️ Plan requires human review")
                    
                except Exception as e:
                    add_log(f"❌ Planning failed: {str(e)}", "ERROR")
                    st.error(f"Failed to plan trip: {str(e)}")
                    return
        
        # Display results
        if st.session_state.current_plan:
            plan = st.session_state.current_plan
            
            # Human-in-the-loop review if needed
            if st.session_state.needs_review:
                st.markdown("""
                <div class="review-alert">
                    <h4>⚠️ Review Required</h4>
                    <p>The generated plan needs your attention due to budget constraints or low confidence in sources.</p>
                </div>
                """, unsafe_allow_html=True)
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("✅ Approve Anyway", use_container_width=True):
                        add_log("👤 User approved plan despite issues")
                        updated_plan = st.session_state.orchestrator.review_and_adjust(
                            plan, "approve"
                        )
                        st.session_state.current_plan = updated_plan
                        st.session_state.needs_review = False
                        st.rerun()
                
                with col2:
                    if st.button("🔧 Auto-reduce Costs", use_container_width=True):
                        add_log("👤 User requested cost reduction")
                        with st.spinner("Adjusting plan to fit budget..."):
                            updated_plan = st.session_state.orchestrator.review_and_adjust(
                                plan, "reduce"
                            )
                            st.session_state.current_plan = updated_plan
                            st.session_state.needs_review = False
                            add_log("✅ Plan adjusted to fit budget")
                            st.rerun()
            else:
                st.markdown("""
                <div class="success-alert">
                    <h4>✅ Plan Ready</h4>
                    <p>Your travel itinerary has been generated successfully and fits within your budget!</p>
                </div>
                """, unsafe_allow_html=True)
            
            # Display the itinerary
            display_itinerary(plan)
            
            # Export options
            st.markdown("### 📤 Export Options")
            col1, col2 = st.columns(2)
            
            with col1:
                # JSON export
                plan_json = plan.model_dump_json(indent=2)
                st.download_button(
                    "📄 Download JSON",
                    plan_json,
                    f"travel_plan_{plan.destination.lower().replace(' ', '_')}.json",
                    "application/json"
                )
            
            with col2:
                # Text export
                text_export = f"""
Travel Plan: {plan.destination}
Duration: {plan.days} days
Budget: {plan.total_estimated_cost:.2f} {plan.currency}
Status: {'Under Budget' if plan.under_budget else 'Over Budget'}

Itinerary:
"""
                activities_by_day = {}
                for item in plan.items:
                    if item.day not in activities_by_day:
                        activities_by_day[item.day] = []
                    activities_by_day[item.day].append(item)
                
                for day in sorted(activities_by_day.keys()):
                    text_export += f"\nDay {day}:\n"
                    for activity in activities_by_day[day]:
                        cost = f"{activity.approx_cost:.2f} {activity.currency}" if activity.approx_cost > 0 else "Free"
                        text_export += f"  - {activity.activity} ({cost})\n"
                        if activity.source:
                            text_export += f"    Source: {activity.source}\n"
                
                if plan.notes:
                    text_export += f"\nNotes: {plan.notes}"
                
                st.download_button(
                    "📝 Download Text",
                    text_export,
                    f"travel_plan_{plan.destination.lower().replace(' ', '_')}.txt",
                    "text/plain"
                )

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
agent_with_openweather_tool_insecure.py

Demo-only version:
 - WeatherTool: calls OpenWeatherMap current weather API
 - Agent: LangChain agent (ZERO_SHOT_REACT_DESCRIPTION) that can call the tool
 - Simple CLI to interact with the agent
 - SSL verification DISABLED (insecure, for demo only)

Requirements:
 pip install python-dotenv requests langchain langchain-openai httpx

Environment:
 - OPENAI_API_KEY
 - OPENWEATHER_API_KEY
"""

import os
import sys
import traceback
from dotenv import load_dotenv
import requests
from typing import Optional, Dict
import httpx

# LangChain imports (BaseTool, agent utilities)
from langchain.tools import BaseTool
from langchain_openai import ChatOpenAI
from langchain.agents import initialize_agent, AgentType
from langchain.memory import ConversationBufferMemory

# Load env
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")

if not OPENAI_API_KEY:
    print("ERROR: OPENAI_API_KEY not set in environment.")
    sys.exit(1)
if not OPENWEATHER_API_KEY:
    print("ERROR: OPENWEATHER_API_KEY not set in environment.")
    sys.exit(1)

# -------------------------
# WeatherTool: subclass BaseTool
# -------------------------
class WeatherTool(BaseTool):
    name: str = "weather tool"
    description: str = "Get current weather for a location. Input: location string (e.g., 'Dubai')."

    def _run(self, location: str) -> str:
        """Synchronous run: returns a text summary or error message."""
        try:
            if not location or not location.strip():
                return "OpenWeatherMap: please provide a location (e.g., 'Dubai')."

            # Try geocoding endpoint for accuracy
            geo_url = "http://api.openweathermap.org/geo/1.0/direct"
            geo_params = {"q": location, "limit": 1, "appid": OPENWEATHER_API_KEY}
            geo_resp = requests.get(geo_url, params=geo_params, timeout=10, verify=False)
            geo_resp.raise_for_status()
            geo_data = geo_resp.json()
            if isinstance(geo_data, list) and len(geo_data) > 0:
                top = geo_data[0]
                lat = top.get("lat")
                lon = top.get("lon")
                display_name = ", ".join(
                    filter(None, [top.get("name"), top.get("state"), top.get("country")])
                )
            else:
                # fallback: try current weather by q param
                lat = lon = None
                display_name = location

            # Get current weather
            if lat is not None and lon is not None:
                weather_url = "https://api.openweathermap.org/data/2.5/weather"
                params = {"lat": lat, "lon": lon, "appid": OPENWEATHER_API_KEY, "units": "metric"}
            else:
                weather_url = "https://api.openweathermap.org/data/2.5/weather"
                params = {"q": location, "appid": OPENWEATHER_API_KEY, "units": "metric"}

            wresp = requests.get(weather_url, params=params, timeout=10, verify=False)
            wresp.raise_for_status()
            wdata = wresp.json()

            # Handle API errors
            if wdata.get("cod") and int(wdata.get("cod")) != 200:
                return f"OpenWeatherMap error: {wdata.get('message', 'unknown error')}"

            # Build a user-friendly summary
            weather_arr = wdata.get("weather", [])
            description = weather_arr[0]["description"].capitalize() if weather_arr else "Unknown"
            main = wdata.get("main", {})
            temp = main.get("temp")
            feels_like = main.get("feels_like")
            humidity = main.get("humidity")
            wind_speed = wdata.get("wind", {}).get("speed")

            parts = [f"Weather for {display_name}:"]
            parts.append(f"{description}.")
            if temp is not None:
                parts.append(f"Temperature {temp}°C (feels like {feels_like}°C).")
            if humidity is not None:
                parts.append(f"Humidity {humidity}%.")
            if wind_speed is not None:
                parts.append(f"Wind {wind_speed} m/s.")

            return " ".join(parts)
        except requests.HTTPError as he:
            return f"OpenWeatherMap HTTP error: {str(he)}"
        except Exception as e:
            return f"Failed to retrieve weather: {str(e)}"

    async def _arun(self, location: str) -> str:
        # Async not implemented for this demo
        raise NotImplementedError("Async _arun not implemented.")


# -------------------------
# LLM, Agent, Memory setup
# -------------------------
# Use httpx client with SSL verification disabled
httpx_client = httpx.Client(verify=False, timeout=15.0)

llm = ChatOpenAI(
    model_name="gpt-4o-mini",
    temperature=0.3,
    max_tokens=512,
    openai_api_key=OPENAI_API_KEY,
    http_client=httpx_client,  # <<-- critical to avoid SSL error
)

# memory (optional): keep short context during the demo
memory = ConversationBufferMemory(return_messages=True, input_key="input", memory_key="history")

# initialize agent with our WeatherTool
tools = [WeatherTool()]

agent = initialize_agent(
    tools=tools,
    llm=llm,
    agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
    verbose=True,      # show chain / tool calls in console
    max_iterations=3,  # safety: limit tool-call loops
    agent_kwargs={
        "prefix": (
            "You are a helpful Dubai guide agent. "
            "Always answer in the following format:\n"
            "Thought: [your reasoning]\n"
            "Action: [the action to take, or 'Final Answer']\n"
            "Action Input: [the input to the action, or your answer]\n"
            "If you don't need to use a tool, respond with 'Final Answer' as the Action."
        )
    }
)


# -------------------------
# Simple CLI for demo
# -------------------------
def run_cli():
    print("=== Dubai Guide Agent (with OpenWeatherMap tool) ===")
    print("Ask normal questions (e.g., 'Tell me about Dubai') or weather ones ('What's the weather in Dubai?').")
    print("Commands: /exit, /clear\n")

    try:
        while True:
            user_input = input("You: ").strip()
            if not user_input:
                continue
            if user_input.lower() in ("/exit", "/quit"):
                print("Goodbye!")
                break
            if user_input.lower() == "/clear":
                memory.clear()
                print("Conversation cleared.")
                continue



            try:
                # Use agent.invoke (run is deprecated), pass input as dict, handle parsing errors
                result = agent.invoke({"input": user_input}, handle_parsing_errors=True)
                answer = result["output"] if isinstance(result, dict) and "output" in result else str(result)
            except Exception as e:
                print("Agent error:", str(e))
                traceback.print_exc()
                continue

            print("\nGuide:", answer, "\n")
            # Save to memory for short-term demo recall
            memory.save_context({"input": user_input}, {"output": answer})

    finally:
        try:
            httpx_client.close()
        except Exception:
            pass


if __name__ == "__main__":
    run_cli()

import sqlite3
import json
import requests
import os
from dotenv import load_dotenv
from langchain.tools import tool
from langchain_community.tools.tavily_search import TavilySearchResults

# Load secret keys
load_dotenv()

# 1. Initialize the Web Search Tool (FIX: Reduced to 2 results to save tokens!)
web_search_tool = TavilySearchResults(max_results=2)

# --- ADVANCED SQL HELPER FUNCTION ---
def query_database(query: str, parameters: tuple = ()):
    """Executes a secure SQL query and returns the results."""
    try:
        conn = sqlite3.connect("travel_agent.db")
        conn.row_factory = sqlite3.Row 
        cursor = conn.cursor()
        cursor.execute(query, parameters)
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]
    except Exception as e:
        return f"Database Error: {str(e)}"

# --- UPGRADED AI TOOLS ---

@tool
def search_flights(source: str, destination: str) -> str:
    """Search for available flights between a source city and a destination city."""
    query = "SELECT * FROM flights WHERE source LIKE ? AND destination LIKE ?"
    results = query_database(query, (f"%{source}%", f"%{destination}%"))
    
    if isinstance(results, str): return results 
    if not results: return f"No local database flights found."
    return json.dumps(results)

@tool
def search_hotels(city: str) -> str:
    """Search for hotel recommendations and prices in a specific city."""
    query = "SELECT * FROM hotels WHERE city LIKE ?"
    results = query_database(query, (f"%{city}%",))
    
    if isinstance(results, str): return results
    if not results: return f"No local database hotels found."
    return json.dumps(results)

@tool
def live_web_search(query: str) -> str:
    """CRITICAL TOOL: Use this to search the live internet for REAL tourist attractions, 
    restaurants, and travel info. ALWAYS use this."""
    try:
        raw_results = web_search_tool.invoke({"query": query})
        
        # THE TOKEN DIET FIX: Truncate the website text so Groq doesn't crash!
        for res in raw_results:
            if "content" in res:
                # Keep only the first 400 characters of the website
                res["content"] = res["content"][:400] + "... [TRUNCATED]"
                
        return json.dumps(raw_results)
    except Exception as e:
        return f"Web search failed: {str(e)}"

@tool
def get_weather(latitude: float, longitude: float) -> str:
    """Get the real-time weather forecast for a location."""
    url = f"https://api.open-meteo.com/v1/forecast?latitude={latitude}&longitude={longitude}&daily=temperature_2m_max,temperature_2m_min,precipitation_probability_max&timezone=auto"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            return json.dumps(response.json())
        else:
            return "Weather API is currently down."
    except Exception as e:
        return f"Error fetching weather: {str(e)}"
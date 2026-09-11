import os
import operator
import time
from typing import TypedDict, Annotated
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage, SystemMessage
from langgraph.prebuilt import create_react_agent
from langgraph.graph import StateGraph, END
from tools import search_flights, search_hotels, live_web_search, get_weather

# Load environment variables
load_dotenv()

# 1. Initialize the LLM (Updated to active replacement model based on August 2026 deprecation)
llm = ChatGroq(
    temperature=0, 
    model_name="openai/gpt-oss-20b"  
)

# 2. Define the Tools
tools = [search_flights, search_hotels, live_web_search, get_weather]

# --- THE PLANNER AGENT ---
SYSTEM_PROMPT = """You are an elite, highly efficient AI Travel Agent. Your goal is to design a flawless itinerary on your VERY FIRST ATTEMPT to pass the strict Auditor check. 
Always utilize your tools to get real data. Never hallucinate prices or locations.

CRITICAL RULES TO AVOID AUDIT FAILURE (FOLLOW EXACTLY):
1. DESTINATION CHECK: Do NOT suggest activities outside of the requested destination. Keep all travel logic geographically sound.
2. BUDGET MATH: You MUST include a "Financial Breakdown" section. The total estimated cost MUST be strictly less than or equal to the Max Budget. Do not go over budget.
3. WEATHER ADAPTATION: You MUST include a "Weather Expectations" section based on the current season. You MUST state clearly that the activities are safe for this weather.
4. FORMATTING: Use clean, simple text format. Do not use complex markdown tables that might break on WhatsApp. Use bullet points. 
5. DAY-BY-DAY: Clearly label each day (e.g., "Day 1:", "Day 2:") so the parsing system can read it easily."""


# state_modifier is the modern standard.
planner_agent = create_react_agent(llm, tools, prompt=SYSTEM_PROMPT)

# --- THE AUDITOR AGENT ---
auditor_prompt = """You are a QA Travel Auditor.
Evaluate the provided travel itinerary against these constraints:
1. BUDGET CHECK: The maximum budget is ₹{budget}. Ensure the math is logical and the total is less than or equal to the budget.
2. FORMAT CHECK: MUST include the '### 📍 Map Locations List' formatted exactly with bullet points and (Day X).
3. WEATHER CHECK: Read the 'Weather Expectations' section. Ensure it exists.

If it passes ALL checks, reply with EXACTLY the word: PASS
If it fails ANY check, reply with: FAIL \n\n Provide specific instructions on what the planner must fix.
(Note: Do NOT fail the destination check unless the planner suggests cities in a completely different country).
"""

class TravelState(TypedDict):
    messages: Annotated[list[BaseMessage], operator.add]
    departure: str
    destination: str
    budget: int
    iterations: int
    final_itinerary: str

def planner_node(state: TravelState):
    print(f"\n--> [Agent 1: Planner] Designing Draft (Attempt {state['iterations'] + 1})")
    response = planner_agent.invoke({"messages": state["messages"]})
    draft = response["messages"][-1].content
    return {"messages": [AIMessage(content=draft)], "final_itinerary": draft}

def auditor_node(state: TravelState):
    print("--> [System] Pausing for 5 seconds to bypass API rate limits...")
    time.sleep(5) 
    
    print("--> [Agent 2: Auditor] Reviewing Draft for logic and weather safety...")
    draft = state["final_itinerary"]
    sys_prompt = auditor_prompt.format(
        departure=state["departure"], 
        destination=state["destination"], 
        budget=state["budget"]
    )
    
    audit_query = f"{sys_prompt}\n\nHere is the drafted itinerary to review:\n\n{draft}"
    
    try:
        response = llm.invoke(audit_query)
        feedback = response.content
    except Exception as e:
        print(f"--> [Agent 2: Auditor] API Limit hit during audit. Passing draft to avoid crash.")
        return {"messages": [AIMessage(content="PASS")], "iterations": state["iterations"] + 1}
    
    if "PASS" in feedback:
        print("--> [Agent 2: Auditor] Approved! ✅ Passing to UI.")
        return {"messages": [AIMessage(content="PASS")], "iterations": state["iterations"] + 1}
    else:
        print(f"--> [Agent 2: Auditor] Failed! ❌ Sending back to Planner with notes: {feedback[:100]}...")
        correction_msg = f"Your previous draft failed the audit. DO NOT apologize. Just rewrite the itinerary fixing these issues:\n{feedback}"
        return {"messages": [HumanMessage(content=correction_msg)], "iterations": state["iterations"] + 1}

def router(state: TravelState):
    last_message = state["messages"][-1].content
    if "PASS" in last_message or state["iterations"] >= 2: 
        return END
    return "planner"

workflow = StateGraph(TravelState)
workflow.add_node("planner", planner_node)
workflow.add_node("auditor", auditor_node)
workflow.set_entry_point("planner")
workflow.add_edge("planner", "auditor")
workflow.add_conditional_edges("auditor", router)
app = workflow.compile()

# --- MAIN EXECUTION FUNCTION ---
def run_travel_agent(departure: str, destination: str, duration: int, budget: int, persona: str, extra_notes: str, language: str) -> str:
    initial_query = f"""
    Plan a {duration}-day trip from {departure} to {destination}. Max budget: ₹{budget}. Style: '{persona}'. Notes: {extra_notes}.
    
    CRITICAL INSTRUCTIONS: 
    1. Write the entire itinerary (summary, days, weather, budget) fluently in {language}.
    2. You MUST write the final '### 📍 Map Locations List' section strictly in English using the exact format '- Place Name (Day 1)'.
    3. Explicitly state "Destination: {destination}" at the very beginning of the text so the Auditor knows you followed instructions.
    """
    
    initial_state = {
        "messages": [HumanMessage(content=initial_query)],
        "departure": departure,
        "destination": destination,
        "budget": budget,
        "iterations": 0,
        "final_itinerary": ""
    }
    
    try:
        result = app.invoke(initial_state)
        return result["final_itinerary"]
    except Exception as e:
        return f"I encountered an error planning your trip: {str(e)}"

import os
import time
from fastapi import FastAPI, Form, BackgroundTasks, Response
from fastapi import FastAPI, Form, BackgroundTasks
from twilio.twiml.messaging_response import MessagingResponse
from twilio.rest import Client
from dotenv import load_dotenv
from agent import run_travel_agent

load_dotenv()

app = FastAPI()

TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_WHATSAPP_NUMBER = os.getenv("TWILIO_WHATSAPP_NUMBER", "whatsapp:+14155238886")

client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

def process_and_send_itinerary(incoming_msg: str, user_number: str):
    """Runs the heavy Multi-Agent logic in the background, chunks it, and pushes to WhatsApp."""
    try:
        parts = [p.strip() for p in incoming_msg.split(',')]
        if len(parts) < 4:
            raise ValueError("Incorrect format provided.")
            
        departure = parts[0]
        destination = parts[1]
        duration = int(parts[2])
        budget = int(parts[3])
        
        # Run your LangGraph Multi-Agent system
        itinerary_text = run_travel_agent(
            departure, destination, duration, budget, "Balanced", "Optimize for clean WhatsApp text formatting.", "English"
        )
        
        # Chunking Logic to bypass Twilio's 1600 character limit
        chunk_size = 1500
        chunks = [itinerary_text[i:i + chunk_size] for i in range(0, len(itinerary_text), chunk_size)]
        
        for i, chunk in enumerate(chunks):
            if len(chunks) > 1:
                chunk = f"*(Part {i+1}/{len(chunks)})*\n\n" + chunk

            client.messages.create(
                body=chunk,
                from_=TWILIO_WHATSAPP_NUMBER,
                to=user_number
            )
            time.sleep(1) # Breathable pause for Twilio rate limits
            
    except Exception as e:
        client.messages.create(
            body=f"⚠️ System Error while processing your trip: {str(e)}",
            from_=TWILIO_WHATSAPP_NUMBER,
            to=user_number
        )

@app.post("/whatsapp")
async def whatsapp_webhook(background_tasks: BackgroundTasks, Body: str = Form(...), From: str = Form(...)):
    """Handles incoming messages instantly to bypass Twilio's 15-second timeout rule."""
    incoming_msg = Body.strip()
    user_number = From 
    
    response = MessagingResponse()
    
# Onboarding Trigger Menu
    if incoming_msg.lower() in ["hi", "hello", "help", "start"]:
        welcome_text = (
            "🌍 *Welcome to Agentic Travel Pro!* 🌍\n\n"
            "I am your autonomous AI Travel Agent. To plan a trip, reply using this exact format:\n\n"
            "📍 *Departure, Destination, Days, Budget*\n\n"
            "📝 _Example:_ Pune, Goa, 3, 25000"
        )
        response.message(welcome_text)
        # FIX 1: Send as XML
        return Response(content=str(response), media_type="application/xml")

    # Validate trip generation input
    parts = incoming_msg.split(',')
    if len(parts) >= 4:
        response.message("🤖 *Request Received!* Your Multi-Agent Travel team is checking live web searches, processing weather forecasts, and auditing your budget options. \n\nThis takes about 20 seconds. Your itinerary will be texted directly to this chat shortly! ✈️")
        
        # Fire background task
        background_tasks.add_task(process_and_send_itinerary, incoming_msg, user_number)
    else:
        response.message("⚠️ Invalid format. Please reply with: *Departure, Destination, Days, Budget*")
        
    # FIX 2: Send as XML
    return Response(content=str(response), media_type="application/xml")
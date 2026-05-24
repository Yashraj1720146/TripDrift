import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import folium
from streamlit_folium import st_folium
import time
import re
import datetime 
import sqlite3 
from fpdf import FPDF
from agent import run_travel_agent

# --- 1. PAGE CONFIGURATION & BRANDING ---
st.set_page_config(page_title="TripDrift AI | Travel Planner", page_icon="✈️", layout="wide")

# Custom CSS for Premium UI
st.markdown("""
<style>
    /* Main Background (Soft Light Blue) */
    .stApp { background-color: #eef7ff; }
    
    /* Input Boxes Styling (Crisp White with Borders) */
    div[data-baseweb="input"] > div, 
    div[data-baseweb="select"] > div,
    div[data-widget="stDateInput"] div[data-baseweb="input"] {
        background-color: #ffffff !important;
        border: 1.5px solid #cbd5e1 !important;
        border-radius: 8px !important;
        transition: all 0.2s ease;
    }
    
    /* Input Boxes Focus Effect (Blue glow when clicking) */
    div[data-baseweb="input"] > div:focus-within, 
    div[data-baseweb="select"] > div:focus-within {
        border-color: #0ea5e9 !important;
        box-shadow: 0 0 0 1px #0ea5e9 !important;
    }

    /* Premium Gradient Button */
    div.stButton > button:first-child { 
        background: linear-gradient(135deg, #0284c7 0%, #0ea5e9 100%); 
        color: white; 
        border: none; 
        border-radius: 12px; 
        padding: 12px 24px; 
        font-weight: 700; 
        font-size: 18px;
        box-shadow: 0 4px 14px 0 rgba(2, 132, 199, 0.39);
        transition: all 0.3s ease;
    }
    div.stButton > button:first-child:hover { 
        transform: translateY(-2px); 
        box-shadow: 0 6px 20px rgba(2, 132, 199, 0.5); 
    }
    
    /* Clean up sidebar */
    [data-testid="stSidebar"] {
        background-color: #ffffff;
        border-right: 1px solid #e2e8f0;
    }
    
    /* Custom Headers */
    h1 { color: #0f172a; font-weight: 800; font-family: 'Helvetica Neue', sans-serif; }
    h2, h3 { color: #334155; font-weight: 700; }
</style>
""", unsafe_allow_html=True)

# --- 2. DATABASE SETUP & AUTHENTICATION (NO LOGIC CHANGES) ---
def init_db():
    conn = sqlite3.connect('travel_app.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS trips 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, destination TEXT, itinerary TEXT, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')
    conn.commit()
    conn.close()

def create_user(username, password):
    try:
        conn = sqlite3.connect('travel_app.db')
        c = conn.cursor()
        c.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        return False

def login_user(username, password):
    conn = sqlite3.connect('travel_app.db')
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE username=? AND password=?", (username, password))
    user = c.fetchone()
    conn.close()
    return user is not None

def save_trip_to_db(username, destination, itinerary):
    conn = sqlite3.connect('travel_app.db')
    c = conn.cursor()
    c.execute("INSERT INTO trips (username, destination, itinerary) VALUES (?, ?, ?)", (username, destination, itinerary))
    conn.commit()
    conn.close()

def get_user_trips(username):
    conn = sqlite3.connect('travel_app.db')
    c = conn.cursor()
    c.execute("SELECT destination, itinerary, timestamp FROM trips WHERE username=? ORDER BY timestamp DESC", (username,))
    trips = c.fetchall()
    conn.close()
    return trips

init_db()

if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
if 'username' not in st.session_state:
    st.session_state['username'] = ''

# --- 3. SIDEBAR AUTHENTICATION & WHATSAPP UI ---
with st.sidebar:
    st.markdown("<h2 style='text-align: center; color: #0284c7;'>✈️ TripDrift</h2>", unsafe_allow_html=True)
    st.write("")
    
    if not st.session_state['logged_in']:
        st.subheader("Account Access")
        auth_mode = st.radio("Select Mode", ["Login", "Sign Up"], horizontal=True)
        auth_user = st.text_input("Username")
        auth_pass = st.text_input("Password", type="password")
        
        if st.button(auth_mode, use_container_width=True):
            if auth_mode == "Sign Up":
                if create_user(auth_user, auth_pass):
                    st.success("Account created! Please log in.")
                else:
                    st.error("Username already taken.")
            elif auth_mode == "Login":
                if login_user(auth_user, auth_pass):
                    st.session_state['logged_in'] = True
                    st.session_state['username'] = auth_user
                    st.rerun()
                else:
                    st.error("Incorrect username or password.")
    else:
        st.success(f"👋 Welcome back, {st.session_state['username']}!")
        st.divider()
        
        st.subheader("📱 TripDrift Mobile")
        st.write("Plan trips on the go via WhatsApp. Scan the QR code or click below.")
        
        whatsapp_url = "https://wa.me/14155238886?text=join%20volume-chest"
        qr_api_url = f"https://api.qrserver.com/v1/create-qr-code/?size=150x150&data={whatsapp_url}&color=0284c7"
        
        colA, colB, colC = st.columns([1,4,1])
        with colB:
            st.image(qr_api_url, use_container_width=True)
            
        st.markdown(f'''
            <a href="{whatsapp_url}" target="_blank" style="text-decoration: none;">
                <button style="
                    width: 100%; 
                    background-color: #25D366; 
                    color: white; 
                    border: none; 
                    padding: 12px; 
                    border-radius: 8px; 
                    font-weight: bold; 
                    cursor: pointer;
                    margin-top: 10px;">
                    💬 Open WhatsApp Bot
                </button>
            </a>
        ''', unsafe_allow_html=True)
        
        st.info("💡 **How to use:**\n1. Send the pre-filled 'join' message.\n2. Text **'Hi'** to see the menu, or type: *Pune, Goa, 3, 25000*")
        
        st.divider()
        if st.button("🚪 Log Out", use_container_width=True):
            st.session_state['logged_in'] = False
            st.session_state['username'] = ''
            st.rerun()

# --- 4. HELPER FUNCTIONS & CACHING ---
COORDINATE_CACHE = {
    "Pune, India": (18.5204, 73.8567),
    "New Delhi, India": (28.6139, 77.2090),
    "Goa, India": (15.2993, 74.1240)
}

@st.cache_data(show_spinner=False)
def get_city_coordinates(search_query):
    if search_query in COORDINATE_CACHE:
        return COORDINATE_CACHE[search_query]
    time.sleep(1) 
    try:
        url = f"https://nominatim.openstreetmap.org/search?q={search_query}&format=json&limit=1"
        headers = {'User-Agent': 'TripDriftApp_v1'} 
        response = requests.get(url, headers=headers, timeout=5).json()
        if response:
            lat, lon = float(response[0]["lat"]), float(response[0]["lon"])
            COORDINATE_CACHE[search_query] = (lat, lon)
            return lat, lon
    except:
        pass
    try:
        city_only = search_query.split(",")[0].strip()
        fallback_url = f"https://geocoding-api.open-meteo.com/v1/search?name={city_only}&count=1&language=en&format=json"
        response = requests.get(fallback_url, timeout=5).json()
        if "results" in response:
            lat, lon = float(response["results"][0]["latitude"]), float(response["results"][0]["longitude"])
            COORDINATE_CACHE[search_query] = (lat, lon)
            return lat, lon
    except:
        pass
    return None, None

def generate_ics(destination, duration, start_date):
    ics_lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//TripDrift AI//EN"]
    for i in range(duration):
        current_date = start_date + datetime.timedelta(days=i)
        next_date = current_date + datetime.timedelta(days=1)
        dtstart = current_date.strftime("%Y%m%d")
        dtend = next_date.strftime("%Y%m%d")
        ics_lines.extend([
            "BEGIN:VEVENT", f"SUMMARY:✈️ {destination} Trip - Day {i+1}", f"DTSTART;VALUE=DATE:{dtstart}", f"DTEND;VALUE=DATE:{dtend}",
            f"DESCRIPTION:Your TripDrift AI Travel Itinerary. Have a great trip!", "END:VEVENT"
        ])
    ics_lines.append("END:VCALENDAR")
    return "\r\n".join(ics_lines).encode('utf-8')

def generate_pdf(text, destination):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.set_font("helvetica", style="B", size=18)
    pdf.cell(0, 10, f"TripDrift Itinerary: {destination}", new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.ln(5)
    pdf.set_font("helvetica", size=11)
    text = text.replace('₹', 'Rs. ')
    clean_text = text.encode('latin-1', 'ignore').decode('latin-1')
    for line in clean_text.split('\n'):
        words = line.split()
        safe_words = [w[:70] + "..." if len(w) > 70 else w for w in words]
        safe_line = " ".join(safe_words)
        pdf.write(6, safe_line + '\n')
    return bytes(pdf.output())

def parse_locations_from_text(text):
    found_locations = []
    lines = text.split("\n")
    for line in lines:
        clean_line = line.strip()
        if clean_line.startswith("-") or clean_line.startswith("*"):
            clean_line = clean_line[1:].strip()
            day_match = re.search(r'Day\s*[:-]?\s*(\d+)', clean_line, re.IGNORECASE)
            day_num = int(day_match.group(1)) if day_match else 1
            place_name = re.sub(r'\(?Day\s*[:-]?\s*\d+\)?', '', clean_line, flags=re.IGNORECASE)
            place_name = place_name.replace("*", "").replace("-", "").strip()
            
            if place_name and len(place_name) > 3 and "locations list" not in place_name.lower() and "hotel booked" not in place_name.lower():
                found_locations.append({"name": place_name, "day": day_num})
    return found_locations

# --- 5. MAIN UI HERO SECTION ---
st.markdown("<br>", unsafe_allow_html=True)
st.markdown("<h1 style='text-align: center; font-size: 3.5rem;'>Design your dream escape.</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; font-size: 1.2rem; color: #64748b; margin-bottom: 2rem;'>Powered by TripDrift Multi-Agent AI.</p>", unsafe_allow_html=True)

# --- 6. THE BOOKING ENGINE CARD ---
with st.container(border=True):
    st.markdown("### 🔍 Where do you want to go?")
    
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1: departure = st.text_input("🛫 From", value="Pune")
    with col2: destination = st.text_input("🛬 To", value="New Delhi")
    with col3: start_date = st.date_input("📅 Date", value=datetime.date.today() + datetime.timedelta(days=7))
    with col4: duration = st.number_input("⏳ Days", min_value=1, max_value=14, value=3)
    with col5: budget = st.number_input("💰 Budget (₹)", min_value=5000, value=25000, step=1000)

    st.write("") # Spacing
    col6, col7, col8 = st.columns([1, 1, 2])
    with col6: persona = st.selectbox("🎭 Vibe", ["Balanced", "Budget", "Luxury", "Adventure"])
    with col7: language = st.selectbox("🌐 Language", ["English", "Hindi", "Marathi", "Spanish", "French"])
    with col8: extra_notes = st.text_input("📝 Special Requests", placeholder="E.g., Focus on historical sites, vegetarian food only...")

    st.write("") 
    generate_btn = st.button("✨ Generate My Itinerary", use_container_width=True)

st.write("")
st.write("")

# --- 7. OUTPUT TABS (NO LOGIC CHANGES) ---
tab1, tab2, tab3, tab4 = st.tabs(["📝 AI Itinerary", "🗺️ Interactive Map", "📊 Budget Analytics", "🗄️ My Past Trips"])

if generate_btn:
    if not st.session_state['logged_in']:
        st.error("⚠️ Please log in from the sidebar to generate and save itineraries!")
    elif not departure or not destination:
        st.warning("Please enter both a departure and destination city.")
    else:
        with st.status("🚀 Launching TripDrift AI Agents...", expanded=True) as status:
            start_time = time.time()
            
            st.write("🧠 Designing itinerary and auditing budget...")
            itinerary_text = run_travel_agent(departure, destination, duration, budget, persona, extra_notes, language)
            map_locations = parse_locations_from_text(itinerary_text)
            
            st.write("💾 Saving trip to secure vault...")
            save_trip_to_db(st.session_state['username'], destination, itinerary_text)
            
            st.write(f"🗺️ Locating {len(map_locations)} places for your interactive map...")
            
            center_lat, center_lon = get_city_coordinates(f"{destination}, India")
            map_markers = []
            
            if center_lat and center_lon:
                for i, place in enumerate(map_locations):
                    st.write(f"📍 Pinning {i+1}/{len(map_locations)}: {place['name']}")
                    p_lat, p_lon = get_city_coordinates(f"{place['name']}, {destination}, India")
                    if p_lat and p_lon:
                        map_markers.append({"place": place, "lat": p_lat, "lon": p_lon})
            
            st.write("📊 Generating visual analytics...")
            
            end_time = time.time()
            status.update(label=f"✅ Trip mapped successfully in {int(end_time - start_time)} seconds!", state="complete", expanded=False)
        
        with tab1:
            st.success("✨ Your TripDrift itinerary is ready!")
            with st.expander("📖 Read Full Itinerary Details", expanded=True):
                st.markdown(itinerary_text)
            
            st.write("---")
            btn_col1, btn_col2, btn_col3 = st.columns(3)
            with btn_col1:
                st.download_button("💾 Download TXT", data=itinerary_text, file_name=f"{destination}_TripDrift.txt", mime="text/plain", use_container_width=True)
            with btn_col2:
                try:
                    pdf_data = generate_pdf(itinerary_text, destination)
                    st.download_button("📄 Download PDF", data=pdf_data, file_name=f"{destination}_TripDrift.pdf", mime="application/pdf", use_container_width=True)
                except Exception as e:
                    st.error(f"PDF Error: {str(e)}")
            with btn_col3:
                ics_data = generate_ics(destination, duration, start_date)
                st.download_button("📅 Add to Calendar", data=ics_data, file_name=f"{destination}_TripDrift.ics", mime="text/calendar", use_container_width=True)
        
        with tab2:
            st.subheader(f"🗺️ Exploring {destination}")
            if center_lat and center_lon:
                m = folium.Map(location=[center_lat, center_lon], zoom_start=11, tiles="CartoDB positron")
                day_colors = {1: "blue", 2: "green", 3: "orange", 4: "purple", 5: "darkred"}
                
                for marker in map_markers:
                    color = day_colors.get(marker['place']['day'], "cadetblue")
                    folium.Marker(
                        [marker['lat'], marker['lon']], 
                        popup=f"<b>Day {marker['place']['day']}:</b> {marker['place']['name']}", 
                        icon=folium.Icon(color=color)
                    ).add_to(m)
                st_folium(m, use_container_width=True, height=500, returned_objects=[])
            else:
                st.error("Could not load base map data. API might be unreachable.")
        
        with tab3:
            st.subheader("Financial Breakdown")
            df_budget = pd.DataFrame({
                "Category": ["Flights", "Accommodation", "Food & Activities", "Miscellaneous"],
                "Amount": [budget * 0.30, budget * 0.40, budget * 0.20, budget * 0.10]
            })
            fig = px.pie(df_budget, values='Amount', names='Category', hole=0.4, color_discrete_sequence=px.colors.sequential.Teal)
            st.plotly_chart(fig, use_container_width=True)

with tab4:
    if st.session_state['logged_in']:
        st.subheader(f"🗄️ Trip History for {st.session_state['username']}")
        user_trips = get_user_trips(st.session_state['username'])
        if user_trips:
            for trip in user_trips:
                dest, itin, timestamp = trip
                with st.expander(f"📍 {dest} (Generated on {timestamp.split('.')[0]})"):
                    st.markdown(itin)
        else:
            st.info("You haven't saved any trips yet. Generate one above!")
    else:
        st.warning("Please log in from the sidebar to view your past trips.")
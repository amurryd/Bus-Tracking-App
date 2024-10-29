import streamlit as st
from mqtt_client import seat_data
import paho.mqtt.client as mqtt
import json
import sqlite3
import logging

# Initialize logging for error handling and debugging
logging.basicConfig(level=logging.INFO)

# Global variable to store total passenger count
total_passengers = 0

# MQTT broker settings
mqtt_broker = "test.mosquitto.org"
mqtt_topic = "rfid/totalTags"

# Load seat data from SQLite on startup for continuity
def load_seat_data_from_db():
    conn = sqlite3.connect('bus_seat_log.db')
    c = conn.cursor()
    c.execute("SELECT bus, seat_id, status FROM seat_logs ORDER BY timestamp DESC")
    rows = c.fetchall()
    seat_data = {}
    for bus, seat_id, status in rows:
        if bus not in seat_data:
            seat_data[bus] = {}
        seat_data[bus][seat_id] = status
    conn.close()
    return seat_data

seat_data = load_seat_data_from_db()

# MQTT message processing callback
def on_message(client, userdata, msg):
    global total_passengers
    try:
        total_passengers = int(msg.payload.decode())
        st.session_state['total_passengers'] = total_passengers
    except ValueError:
        logging.error("Error decoding MQTT message")

# MQTT client setup with error handling
try:
    mqtt_client = mqtt.Client()
    mqtt_client.on_message = on_message
    mqtt_client.connect(mqtt_broker, 1883, 60)
    mqtt_client.subscribe(mqtt_topic)
    mqtt_client.loop_start()
except Exception as e:
    st.error(f"Failed to connect to MQTT broker: {e}")

# Streamlit app layout setup
st.set_page_config(page_title="Bus Seat and Passenger Tracker", layout="wide")

# Sidebar navigation
page = st.sidebar.selectbox("Navigate", ["Home", "Select Bus", "Seat Availability", "Passenger Count"])

# Custom CSS for seat display themes
st.markdown("""
    <style>
    .stApp { background-color: #E6F0FA; }
    .seat-block {
        padding: 15px;
        margin: 5px;
        color: white;
        font-size: 18px;
        text-align: center;
        border-radius: 8px;
        width: 100px;
        min-width: 90px;
    }
    .seat-available { background-color: #32CD32; }
    .seat-occupied { background-color: #FF4500; }
    .seat-child { background-color: #FFD700; color: black; }
    .seat-item { background-color: #8A2BE2; }
    </style>
""", unsafe_allow_html=True)

# Page definitions
def show_home():
    st.title("🚍 Welcome to the Bus Seat and Passenger Tracker")
    st.write("Monitor real-time seat availability and total passenger count.")

def show_bus_selection():
    st.title("Select a Bus")
    if seat_data:
        bus_list = list(seat_data.keys())
        selected_bus = st.selectbox("Choose a Bus", bus_list)
        st.session_state["selected_bus"] = selected_bus
    else:
        st.write("No bus data available yet. Please wait...")

def show_seat_availability():
    st.title("Seat Availability")
    if "selected_bus" in st.session_state:
        selected_bus = st.session_state["selected_bus"]
        st.write(f"Viewing seat availability for Bus: {selected_bus}")
        seats = seat_data.get(selected_bus, {})
        if seats:
            cols = st.columns(4)
            for i, (seat_id, status) in enumerate(seats.items()):
                css_class = f"seat-{status}"
                cols[i % 4].markdown(f"<div class='seat-block {css_class}'>Seat {seat_id}</div>", unsafe_allow_html=True)
        else:
            st.write("No seat data available for this bus.")
    else:
        st.write("Please select a bus first.")

def show_passenger_count():
    st.title("Total Passengers")
    st.write("Total number of passengers on the bus based on RFID tags.")
    if "total_passengers" in st.session_state:
        st.write(f"Total Passengers: {st.session_state['total_passengers']}")
    else:
        st.write("Waiting for passenger data...")

# Render selected page
if page == "Home":
    show_home()
elif page == "Select Bus":
    show_bus_selection()
elif page == "Seat Availability":
    show_seat_availability()
elif page == "Passenger Count":
    show_passenger_count()

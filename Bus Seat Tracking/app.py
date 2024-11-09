# app.py
import os
import eventlet
eventlet.monkey_patch()

from flask import Flask, render_template
from flask_socketio import SocketIO
from flask_mqtt import Mqtt
from threading import Lock

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'

# MQTT configuration
app.config['MQTT_BROKER_URL'] = 'test.mosquitto.org'
app.config['MQTT_BROKER_PORT'] = 1883
app.config['MQTT_KEEPALIVE'] = 60
app.config['MQTT_TLS_ENABLED'] = False

# Initialize Flask extensions
socketio = SocketIO(app, logger=True, engineio_logger=True)
mqtt = Mqtt(app)
thread_lock = Lock()  # Lock to handle race conditions

seats = {}
passenger_count = 0

# Initialize 20 seats with default status and classification
def initialize_seats(num_seats=20):
    global seats
    seats = {
        f"seat{i}": {
            "status": "Kosong",  # "Available" in Bahasa Indonesia
            "classification": "N/A"  # Default classification
        }
        for i in range(1, num_seats + 1)
    }

initialize_seats()  # Initialize 20 seats

# Track completeness for seat data updates
seat_data_complete = {
    f"seat{i}": {"status": False, "classification": False} for i in range(1, 21)
}

def emit_if_seat_data_complete(seat_id):
    """Emit seat data if both status and classification are complete for the seat."""
    if seat_data_complete[seat_id]["status"] and seat_data_complete[seat_id]["classification"]:
        # Emit updated data to all connected clients
        socketio.emit('update_data', {'seats': seats, 'passenger_count': passenger_count})
        # Reset flags for the next update
        seat_data_complete[seat_id]["status"] = False
        seat_data_complete[seat_id]["classification"] = False

@mqtt.on_connect()
def handle_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Connected to MQTT broker")
        # Subscribe to each seat's status and classification topic
        for i in range(1, 21):
            mqtt.subscribe(f"sensor/status{i}")
            mqtt.subscribe(f"sensor/klasifikasi{i}")
        # Subscribe to passenger count topic
        mqtt.subscribe("rfid/totalPass")
    else:
        print("Failed to connect, return code", rc)

@mqtt.on_message()
def handle_mqtt_message(client, userdata, message):
    global seats, passenger_count
    topic = message.topic
    payload = message.payload.decode()
    
    print(f"Received MQTT message on {topic}: {payload}")

    # Lock to prevent race conditions
    with thread_lock:
        # Determine seat number from topic
        if topic.startswith("sensor/status") or topic.startswith("sensor/klasifikasi"):
            seat_num = topic.split("sensor/")[1].split("status")[1] if "status" in topic else topic.split("klasifikasi")[1]
            seat_id = f"seat{seat_num}"
            
            # Update seat status or classification based on topic
            if f"status{seat_num}" in topic:
                seats[seat_id]['status'] = payload
                seat_data_complete[seat_id]["status"] = True
                emit_if_seat_data_complete(seat_id)
            elif f"klasifikasi{seat_num}" in topic:
                seats[seat_id]['classification'] = payload
                seat_data_complete[seat_id]["classification"] = True
                emit_if_seat_data_complete(seat_id)

        # Update passenger count immediately if topic is `rfid/totalPass`
        elif topic == "rfid/totalPass":
            passenger_count = int(payload)
            socketio.emit('update_data', {'seats': seats, 'passenger_count': passenger_count})

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/seat_availability')
def seat_availability():
    return render_template('seat_availability.html', seats=seats, passenger_count=passenger_count)

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/contact')
def contact():
    return render_template('contact.html')

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))

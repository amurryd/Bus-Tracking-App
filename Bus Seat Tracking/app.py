# app.py
import os
import time
import eventlet
eventlet.monkey_patch()

from flask import Flask, render_template
from flask_socketio import SocketIO
from flask_mqtt import Mqtt

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

# Initialize seat and passenger data
seats = {
    "seat1": {"status": "Kursi Kosong", "classification": "N/A"},
    "seat2": {"status": "Kursi Kosong", "classification": "N/A"}
}
passenger_count = 0

# Track completeness of data updates for each seat
seat_data_complete = {
    "seat1": {"status": False, "classification": False},
    "seat2": {"status": False, "classification": False}
}

def emit_if_seat_data_complete(seat_id):
    """Emit seat data if both status and classification are complete for the seat."""
    if seat_data_complete[seat_id]["status"] and seat_data_complete[seat_id]["classification"]:
        socketio.emit('update_data', {'seats': seats, 'passenger_count': passenger_count})
        # Reset flags for the next update
        seat_data_complete[seat_id]["status"] = False
        seat_data_complete[seat_id]["classification"] = False

@mqtt.on_connect()
def handle_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Connected to MQTT broker")
        mqtt.subscribe("sensor/status1")
        mqtt.subscribe("sensor/klasifikasi1")
        mqtt.subscribe("sensor/status2")
        mqtt.subscribe("sensor/klasifikasi2")
        mqtt.subscribe("rfid/totalTags")
    else:
        print("Failed to connect, return code", rc)

@mqtt.on_message()
def handle_mqtt_message(client, userdata, message):
    global seats, passenger_count
    topic = message.topic
    payload = message.payload.decode()
    
    print(f"Received MQTT message on {topic}: {payload}")

    # Process seat status and classification updates with completeness tracking
    if topic == "sensor/status1":
        seats['seat1']['status'] = payload
        seat_data_complete["seat1"]["status"] = True
        emit_if_seat_data_complete("seat1")
    
    elif topic == "sensor/klasifikasi1":
        seats['seat1']['classification'] = payload
        seat_data_complete["seat1"]["classification"] = True
        emit_if_seat_data_complete("seat1")

    elif topic == "sensor/status2":
        seats['seat2']['status'] = payload
        seat_data_complete["seat2"]["status"] = True
        emit_if_seat_data_complete("seat2")

    elif topic == "sensor/klasifikasi2":
        seats['seat2']['classification'] = payload
        seat_data_complete["seat2"]["classification"] = True
        emit_if_seat_data_complete("seat2")

    # Update passenger count immediately as it does not depend on other fields
    elif topic == "rfid/totalTags":
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

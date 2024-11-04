# app.py
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
socketio = SocketIO(app)
mqtt = Mqtt(app)

# Initialize seat and passenger data
seats = {}
passenger_count = 0

def initialize_seats(num_seats):
    global seats
    seats = {
        f"seat{i}": {
            "status": "Kursi Kosong",
            "classification": "N/A"
        }
        for i in range(1, num_seats + 1)
    }

initialize_seats(10)  # Set the number of seats

@mqtt.on_connect()
def handle_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Connected to MQTT broker")
        mqtt.subscribe("sensor/seat1/status")
        mqtt.subscribe("sensor/seat1/klasifikasi")
        mqtt.subscribe("sensor/seat2/status")
        mqtt.subscribe("sensor/seat2/klasifikasi")
        mqtt.subscribe("rfid/totalTags")
    else:
        print("Failed to connect, return code", rc)

@mqtt.on_message()
def handle_mqtt_message(client, userdata, message):
    global seats, passenger_count
    topic = message.topic
    payload = message.payload.decode()

    # Process seat status and classification
    if "sensor/seat" in topic:
        seat_name = topic.split("/")[1]
        if "status" in topic:
            seats[seat_name]["status"] = payload
        elif "klasifikasi" in topic:
            seats[seat_name]["classification"] = payload
    elif topic == "rfid/totalTags":
        passenger_count = int(payload)

    # Emit updated data to all connected WebSocket clients
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

if __name__ == "__main__":
    socketio.run(app, debug=True)

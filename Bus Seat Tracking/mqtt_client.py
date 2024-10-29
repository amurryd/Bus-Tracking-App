import random
import time
import threading
import logging
import sqlite3

logging.basicConfig(level=logging.INFO)

conn = sqlite3.connect('bus_seat_log.db', check_same_thread=False)
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS seat_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                bus TEXT,
                seat_id TEXT,
                status TEXT
            )''')
conn.commit()

def log_to_database(bus, seat_id, status):
    timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
    c.execute("INSERT INTO seat_logs (timestamp, bus, seat_id, status) VALUES (?, ?, ?, ?)",
              (timestamp, bus, seat_id, status))
    conn.commit()

seat_data = {}

def simulate_mqtt():
    buses = ["bus1", "bus2", "bus3"]
    while True:
        for bus in buses:
            if bus not in seat_data:
                seat_data[bus] = {}

            for seat_id in range(1, 11):
                weight_status = random.choice([True, False])
                ir_status = random.choice([True, False])

                if weight_status and ir_status:
                    new_status = "occupied"
                elif not weight_status and ir_status:
                    new_status = "child"
                elif weight_status and not ir_status:
                    new_status = "item"
                else:
                    new_status = "available"

                if seat_data[bus].get(str(seat_id)) != new_status:
                    seat_data[bus][str(seat_id)] = new_status
                    logging.info(f"Bus {bus}, Seat {seat_id} updated to {new_status}")
                    log_to_database(bus, str(seat_id), new_status)

        time.sleep(1)

threading.Thread(target=simulate_mqtt, daemon=True).start()

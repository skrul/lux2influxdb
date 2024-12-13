import random
import sys
import paho.mqtt.client as paho
import json
import traceback
import os
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS
from metrics import METRICS
from typing import List, Dict, Any, Optional

# Get environment variables with defaults
MQTT_HOST = os.getenv('MQTT_HOST', None)
MQTT_PORT = int(os.getenv('MQTT_PORT', '1883'))
MQTT_USERNAME = os.getenv('MQTT_USERNAME', None)
MQTT_PASSWORD = os.getenv('MQTT_PASSWORD', None)
DONGLE = os.getenv('DONGLE', None)

# InfluxDB configuration
INFLUXDB_URL = os.getenv('INFLUXDB_URL', 'http://localhost:8086')
INFLUXDB_TOKEN = os.getenv('INFLUXDB_TOKEN')
INFLUXDB_ORG = os.getenv('INFLUXDB_ORG')
INFLUXDB_BUCKET = os.getenv('INFLUXDB_BUCKET')

# Create InfluxDB client
influxdb_client = InfluxDBClient(
    url=INFLUXDB_URL,
    token=INFLUXDB_TOKEN,
    org=INFLUXDB_ORG
)
write_api = influxdb_client.write_api(write_options=SYNCHRONOUS)

def on_message(client: paho.Client, userdata: Any, msg: paho.MQTTMessage) -> None:
    try:
        sent: List[Dict[str, float]] = []
        payload: Dict[str, Any] = json.loads(msg.payload.decode())
        # Prepare points for InfluxDB
        points: List[Point] = []
        
        # Iterate through all keys in the payload
        for key, value in payload["payload"].items():
            # Convert key to match metrics dictionary
            metric_key: str = key
            if metric_key in METRICS:
                try:
                    # Convert value to float
                    metric_value: float = float(value)
                    
                    # Create InfluxDB point with Point class
                    point: Point = (Point(metric_key)
                        .tag("dongle", DONGLE)
                        .field("value", metric_value))  # Convert MQTT timestamp (seconds) to nanoseconds
                    
                    points.append(point)
                    sent.append({metric_key: metric_value})
                except (ValueError, TypeError) as e:
                    print(f"Failed to convert value for metric {key}: {e}")
        
        # Write points to InfluxDB
        if points:
            write_api.write(bucket=INFLUXDB_BUCKET, record=points)
            print(f"Sent metrics: {json.dumps(sent)}")
    except json.JSONDecodeError:
        print(f"Failed to decode JSON payload: {msg.payload.decode()}")
    except Exception as e:
        print(f"Failed to process payload: {e}")

def run() -> None:
    # Print configuration settings
    print("\nCurrent Configuration:")
    print(f"MQTT Host: {MQTT_HOST}")
    print(f"MQTT Port: {MQTT_PORT}")
    print(f"MQTT Username: {MQTT_USERNAME}")
    print(f"MQTT Password: {'*' * len(MQTT_PASSWORD) if MQTT_PASSWORD else 'None'}")
    print(f"Dongle: {DONGLE}")
    print(f"InfluxDB URL: {INFLUXDB_URL}")
    print(f"InfluxDB Organization: {INFLUXDB_ORG}")
    print(f"InfluxDB Bucket: {INFLUXDB_BUCKET}\n")

    client = paho.Client(
        client_id=f"python-mqtt-{random.randint(0, 1000)}",
        callback_api_version=paho.CallbackAPIVersion.VERSION2,
    )
    client.on_message = on_message

    if MQTT_USERNAME is not None:
        client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
    if client.connect(MQTT_HOST, MQTT_PORT, 60) != 0:
        print("Couldn't connect to the mqtt broker")
        sys.exit(1)

    client.subscribe(f"{DONGLE}/inputbank1")

    try:
        print("Press CTRL+C to exit...")
        client.loop_forever()
    except Exception:
        print(traceback.format_exc())
    finally:
        print("Disconnecting from the MQTT broker")
        client.disconnect()
        print("Closing InfluxDB client")
        influxdb_client.close()

if __name__ == "__main__":
    run()
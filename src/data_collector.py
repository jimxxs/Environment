# src/data_collector.py
import paho.mqtt.client as mqtt
import json
import sqlite3
import requests
import logging
import os
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import threading
import time

# Import your config
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.settings import Config

class SensorDataCollector:
    def __init__(self):
        self.config = Config()
        self.setup_logging()
        self.setup_database()
        self.client = None
        self.is_connected = False
        self.running = False
        

    def setup_logging(self):
        """Set up logging configuration"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('sensor_collector.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
    def setup_database(self):
        """Create database and tables if they don't exist"""
        # Ensure data directory exists
        os.makedirs(os.path.dirname(self.config.DATABASE_PATH), exist_ok=True)
        
        conn = sqlite3.connect(self.config.DATABASE_PATH)
        cursor = conn.cursor()
        
        # Create main sensor data table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sensor_readings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME NOT NULL,
                temperature REAL,
                humidity REAL,
                battery_voltage REAL,
                motion_count INTEGER,
                device_id TEXT,
                raw_data TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create alerts table for future use
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME NOT NULL,
                alert_type TEXT NOT NULL,
                message TEXT NOT NULL,
                value REAL,
                threshold REAL,
                resolved BOOLEAN DEFAULT FALSE,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create index for faster queries
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_timestamp 
            ON sensor_readings(timestamp)
        ''')
        
        conn.commit()
        conn.close()
        self.logger.info("Database initialized successfully")
        
    def save_sensor_data(self, temperature: float, humidity: float, battery: float, 
                        motion: int, timestamp: str, raw_data: str) -> bool:
        """Save sensor data to database with error handling"""
        try:
            conn = sqlite3.connect(self.config.DATABASE_PATH)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO sensor_readings 
                (timestamp, temperature, humidity, battery_voltage, motion_count, device_id, raw_data)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (timestamp, temperature, humidity, battery, motion, self.config.TTN_DEVICE_ID, raw_data))
            
            conn.commit()
            conn.close()
            
            self.logger.info(f"Data saved: T={temperature:.1f}°C, H={humidity:.1f}%, B={battery:.2f}V")
            return True
            
        except Exception as e:
            self.logger.error(f"Database error: {e}")
            return False
            
    def check_alerts(self, temperature: float, humidity: float, battery: float):
        """Check for alert conditions"""
        alerts = []
        
        if temperature < self.config.TEMPERATURE_MIN:
            alerts.append(("TEMP_LOW", f"Temperature too low: {temperature:.1f}°C", temperature, self.config.TEMPERATURE_MIN))
        elif temperature > self.config.TEMPERATURE_MAX:
            alerts.append(("TEMP_HIGH", f"Temperature too high: {temperature:.1f}°C", temperature, self.config.TEMPERATURE_MAX))
            
        if humidity < self.config.HUMIDITY_MIN:
            alerts.append(("HUMIDITY_LOW", f"Humidity too low: {humidity:.1f}%", humidity, self.config.HUMIDITY_MIN))
        elif humidity > self.config.HUMIDITY_MAX:
            alerts.append(("HUMIDITY_HIGH", f"Humidity too high: {humidity:.1f}%", humidity, self.config.HUMIDITY_MAX))
            
        if battery < self.config.BATTERY_LOW:
            alerts.append(("BATTERY_LOW", f"Battery low: {battery:.2f}V", battery, self.config.BATTERY_LOW))
            
        # Save alerts to database
        if alerts:
            self.save_alerts(alerts)
            
    def save_alerts(self, alerts: list):
        """Save alerts to database"""
        try:
            conn = sqlite3.connect(self.config.DATABASE_PATH)
            cursor = conn.cursor()
            
            for alert_type, message, value, threshold in alerts:
                cursor.execute('''
                    INSERT INTO alerts (timestamp, alert_type, message, value, threshold)
                    VALUES (?, ?, ?, ?, ?)
                ''', (datetime.now().isoformat(), alert_type, message, value, threshold))
                
                self.logger.warning(f"ALERT: {message}")
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            self.logger.error(f"Error saving alerts: {e}")
            
    def fetch_historical_data(self):
        """Fetch historical data from TTN"""
        try:
            headers = {"Authorization": f"Bearer {self.config.TTN_API_KEY}"}
            params = {"last": f"{self.config.HISTORICAL_DATA_HOURS}h"}
            
            response = requests.get(self.config.get_api_url(), headers=headers, params=params, timeout=30)
            
            if response.status_code == 200:
                self.logger.info("Historical data fetched successfully")
                
                # Save raw response for debugging
                with open("data/historical_data.json", "w") as f:
                    f.write(response.text.strip())
                
                # Process each line (TTN returns newline-delimited JSON)
                lines = response.text.strip().split('\n')
                processed_count = 0
                
                for line in lines:
                    if line.strip():
                        try:
                            data = json.loads(line)
                            if self.process_message(data, is_historical=True):
                                processed_count += 1
                        except json.JSONDecodeError as e:
                            self.logger.error(f"Error parsing historical data line: {e}")
                            
                self.logger.info(f"Processed {processed_count} historical records")
                return True
                
            else:
                self.logger.error(f"Failed to fetch historical data: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            self.logger.error(f"Exception fetching historical data: {e}")
            return False
            
    def process_message(self, payload: Dict[Any, Any], is_historical: bool = False) -> bool:
        """Process a message from TTN"""
        try:
            if 'uplink_message' not in payload:
                self.logger.warning("No uplink_message in payload")
                return False
                
            uplink = payload['uplink_message']
            
            if 'decoded_payload' not in uplink:
                self.logger.warning("No decoded_payload in uplink_message")
                return False
                
            decoded = uplink['decoded_payload']
            received_at = uplink.get('received_at', datetime.now().isoformat())
            
            # Extract sensor values using field mapping
            temperature = float(decoded.get(self.config.SENSOR_FIELDS['temperature'], 0.0))
            humidity = float(decoded.get(self.config.SENSOR_FIELDS['humidity'], 0.0))
            battery = float(decoded.get(self.config.SENSOR_FIELDS['battery'], 0.0))
            motion = int(decoded.get(self.config.SENSOR_FIELDS['motion'], 0))
            
            # Save to database
            success = self.save_sensor_data(temperature, humidity, battery, motion, 
                                          received_at, json.dumps(payload))
            
            if success and not is_historical:
                # Check for alerts (only for real-time data)
                self.check_alerts(temperature, humidity, battery)
                
                # Print current readings
                self.logger.info(f"=== New Reading ===")
                self.logger.info(f"Time: {received_at}")
                self.logger.info(f"Temperature: {temperature:.1f}°C")
                self.logger.info(f"Humidity: {humidity:.1f}%")
                self.logger.info(f"Battery: {battery:.2f}V")
                self.logger.info(f"Motion: {motion}")
                
            return success
            
        except Exception as e:
            self.logger.error(f"Error processing message: {e}")
            return False
            
    def on_connect(self, client, userdata, flags, rc):
        """MQTT connect callback"""
        if rc == 0:
            self.is_connected = True
            self.logger.info("Connected to TTN MQTT broker!")
            topic = self.config.get_mqtt_topic()
            client.subscribe(topic)
            self.logger.info(f"Subscribed to topic: {topic}")
        else:
            self.is_connected = False
            self.logger.error(f"Failed to connect to MQTT broker, return code {rc}")
            
    def on_disconnect(self, client, userdata, rc):
        """MQTT disconnect callback"""
        self.is_connected = False
        self.logger.warning(f"Disconnected from MQTT broker, return code {rc}")
        
    def on_message(self, client, userdata, msg):
        """MQTT message callback"""
        try:
            payload = json.loads(msg.payload.decode())
            
            # Save latest message for debugging
            with open("data/latest_message.json", "w") as f:
                f.write(json.dumps(payload, indent=4))
                
            # Process the message
            self.process_message(payload, is_historical=False)
            
        except Exception as e:
            self.logger.error(f"Error in on_message: {e}")
            
    def start_mqtt_client(self):
        """Start the MQTT client"""
        try:
            self.client = mqtt.Client()
            self.client.username_pw_set(self.config.TTN_USERNAME, self.config.TTN_PASSWORD)
            self.client.on_connect = self.on_connect
            self.client.on_disconnect = self.on_disconnect
            self.client.on_message = self.on_message
            
            self.logger.info(f"Connecting to MQTT broker: {self.config.TTN_BROKER}:{self.config.TTN_PORT}")
            self.client.connect(self.config.TTN_BROKER, self.config.TTN_PORT, 60)
            
            # Start the loop in a separate thread
            self.client.loop_start()
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start MQTT client: {e}")
            return False
            
    def stop_mqtt_client(self):
        """Stop the MQTT client"""
        if self.client:
            self.client.loop_stop()
            self.client.disconnect()
            self.logger.info("MQTT client stopped")
            
    def run(self):
        """Main run method"""
        self.logger.info("Starting Environmental Monitoring Data Collector")
        self.running = True
        
        # Fetch historical data first
        self.logger.info("Fetching historical data...")
        self.fetch_historical_data()
        
        # Start MQTT client for real-time data
        if self.start_mqtt_client():
            try:
                while self.running:
                    time.sleep(1)  # Keep the main thread alive
                    
            except KeyboardInterrupt:
                self.logger.info("Shutting down data collector...")
            finally:
                self.stop_mqtt_client()
        else:
            self.logger.error("Failed to start MQTT client")
            
    def stop(self):
        """Stop the collector"""
        self.running = False

if __name__ == "__main__":
    collector = SensorDataCollector()
    collector.run()
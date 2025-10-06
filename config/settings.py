# config/settings.py
import os

class Config:
    # TTN Configuration
    TTN_BROKER = "eu1.cloud.thethings.network"
    TTN_PORT = 1883
    TTN_USERNAME = "bd-test-app2@ttn"
    TTN_PASSWORD = "NNSXS.NGFSXX4UXDX55XRIDQZS6LPR4OJXKIIGSZS56CQ.6O4WUAUHFUAHSTEYRWJX6DDO7TL2IBLC7EV2LS4EHWZOOEPCEUOA"
    TTN_DEVICE_ID = "lht65n-01-temp-humidity-sensor"
    TTN_APP_ID = "bd-test-app2"
    TTN_API_KEY = "NNSXS.NGFSXX4UXDX55XRIDQZS6LPR4OJXKIIGSZS56CQ.6O4WUAUHFUAHSTEYRWJX6DDO7TL2IBLC7EV2LS4EHWZOOEPCEUOA"
    
    # Database Configuration
    DATABASE_PATH = "data/sensor_data.db"
    
    # Dashboard Configuration
    FLASK_PORT = 5000
    FLASK_DEBUG = True
    
    # Data Collection Settings
    HISTORICAL_DATA_HOURS = 48  # Max 48 hours for TTN
    DATA_COLLECTION_ENABLED = True
    
    # Sensor Data Fields Mapping
    SENSOR_FIELDS = {
        'battery': 'field1',
        'humidity': 'field3', 
        'motion': 'field4',
        'temperature': 'field5'
    }
    
    # Alert Thresholds (optional for advanced features)
    TEMPERATURE_MIN = 15.0  # Celsius
    TEMPERATURE_MAX = 35.0  # Celsius
    HUMIDITY_MIN = 30.0     # Percentage
    HUMIDITY_MAX = 80.0     # Percentage
    BATTERY_LOW = 3.0       # Volts
    
    @classmethod
    def get_mqtt_topic(cls):
        return f"v3/{cls.TTN_USERNAME}/devices/{cls.TTN_DEVICE_ID}/up"
    
    @classmethod
    def get_api_url(cls):
        return f"https://{cls.TTN_BROKER}/api/v3/as/applications/{cls.TTN_APP_ID}/devices/{cls.TTN_DEVICE_ID}/packages/storage/uplink_message"
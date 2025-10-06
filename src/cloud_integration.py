# src/cloud_integration.py
import requests
import json
import logging
from typing import Optional, Dict, Any
from datetime import datetime

class ThingSpeakIntegration:
    """Integration with ThingSpeak cloud platform"""
    
    def __init__(self, write_api_key: str, channel_id: str):
        self.write_api_key = write_api_key
        self.channel_id = channel_id
        self.base_url = "https://api.thingspeak.com"
        self.logger = logging.getLogger(__name__)
        
    def send_data(self, temperature: float, humidity: float, 
                  battery: float, motion: int) -> bool:
        """Send sensor data to ThingSpeak"""
        try:
            url = f"{self.base_url}/update"
            
            # ThingSpeak field mapping
            data = {
                'api_key': self.write_api_key,
                'field1': temperature,    # Temperature
                'field2': humidity,       # Humidity  
                'field3': battery,        # Battery voltage
                'field4': motion,         # Motion count
            }
            
            response = requests.post(url, data=data, timeout=10)
            
            if response.status_code == 200:
                entry_id = response.text.strip()
                if entry_id != "0":
                    self.logger.info(f"Data sent to ThingSpeak successfully. Entry ID: {entry_id}")
                    return True
                else:
                    self.logger.error("ThingSpeak rejected the data")
                    return False
            else:
                self.logger.error(f"Failed to send data to ThingSpeak: {response.status_code}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error sending data to ThingSpeak: {e}")
            return False
            
    def get_channel_data(self, results: int = 100) -> Optional[Dict[Any, Any]]:
        """Retrieve data from ThingSpeak channel"""
        try:
            url = f"{self.base_url}/channels/{self.channel_id}/feeds.json"
            params = {'results': results}
            
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                return response.json()
            else:
                self.logger.error(f"Failed to get ThingSpeak data: {response.status_code}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error getting ThingSpeak data: {e}")
            return None




class CloudIntegrationManager:
    """Manages multiple cloud integrations"""
    
    def __init__(self):
        self.integrations = {}
        self.logger = logging.getLogger(__name__)
        
    def add_thingspeak(self, name: str, write_api_key: str, channel_id: str):
        """Add ThingSpeak integration"""
        self.integrations[name] = ThingSpeakIntegration(write_api_key, channel_id)
        
    
    def send_to_all(self, temperature: float, humidity: float,
                    battery: float, motion: int) -> Dict[str, bool]:
        """Send data to all configured cloud services"""
        results = {}
        
        for name, integration in self.integrations.items():
            try:
                success = integration.send_data(temperature, humidity, battery, motion)
                results[name] = success
                
                if success:
                    self.logger.info(f"Successfully sent data to {name}")
                else:
                    self.logger.warning(f"Failed to send data to {name}")
                    
            except Exception as e:
                self.logger.error(f"Error with {name} integration: {e}")
                results[name] = False
                
        return results
        
    def send_to_specific(self, service_name: str, temperature: float, 
                        humidity: float, battery: float, motion: int) -> bool:
        """Send data to a specific cloud service"""
        if service_name not in self.integrations:
            self.logger.error(f"Cloud service '{service_name}' not configured")
            return False
            
        try:
            return self.integrations[service_name].send_data(
                temperature, humidity, battery, motion
            )
        except Exception as e:
            self.logger.error(f"Error sending to {service_name}: {e}")
            return False


# Example usage in your data collector
def example_usage():
    """Example of how to integrate cloud services into your data collector"""
    
    # Initialize cloud manager
    cloud_manager = CloudIntegrationManager()
    
    # Add ThingSpeak (easiest to set up)
    cloud_manager.add_thingspeak(
        name="thingspeak",
        write_api_key="JWXTN9WTA90150Z3",
        channel_id="3101089"
    )
    
    # Example sensor data
    temperature = 25.5
    humidity = 60.0
    battery = 3.7
    motion = 5
    
    # Send to all configured services
    results = cloud_manager.send_to_all(temperature, humidity, battery, motion)
    
    print("Cloud integration results:")
    for service, success in results.items():
        status = "✓" if success else "✗"
        print(f"{status} {service}")


# Enhanced data collector with cloud integration
class EnhancedDataCollector:
    """Enhanced data collector with cloud integration"""
    
    def __init__(self, cloud_manager: Optional[CloudIntegrationManager] = None):
        self.cloud_manager = cloud_manager
        self.logger = logging.getLogger(__name__)
        
    def process_and_send_data(self, temperature: float, humidity: float,
                             battery: float, motion: int):
        """Process sensor data and send to cloud services"""
        
        # Save to local database first 
        # self.save_to_database(temperature, humidity, battery, motion)
        
        # Send to cloud services if configured
        if self.cloud_manager:
            try:
                results = self.cloud_manager.send_to_all(
                    temperature, humidity, battery, motion
                )
                
                # Log results
                successful = sum(1 for success in results.values() if success)
                total = len(results)
                
                self.logger.info(f"Cloud integration: {successful}/{total} services successful")
                
            except Exception as e:
                self.logger.error(f"Cloud integration error: {e}")


# Configuration for cloud services
CLOUD_CONFIG = {
    # ThingSpeak configuration
    'thingspeak': {
        'enabled': True,  
        'write_api_key': 'JWXTN9WTA90150Z3',
        'channel_id': '3101089'
    },
    
    # AWS IoT configuration
    'aws_iot': {
        'enabled': False,  
        'endpoint': 'YOUR_AWS_IOT_ENDPOINT',
        'cert_path': 'path/to/certificate.pem.crt',
        'key_path': 'path/to/private.pem.key',
        'ca_path': 'path/to/AmazonRootCA1.pem',
        'thing_name': 'your-thing-name'
    },
    
    # Azure IoT configuration
    'azure_iot': {
        'enabled': False,  
        'connection_string': 'YOUR_DEVICE_CONNECTION_STRING',
        'device_id': 'your-device-id'
    }
}

if __name__ == "__main__":
    example_usage()
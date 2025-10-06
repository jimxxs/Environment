# main.py
import threading
import time
import sys
import os
import signal
from typing import Optional

# Add src to path
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src'))

from src.data_collector import SensorDataCollector
from src.dashboard import app
from config.settings import Config

class EnvironmentalMonitoringSystem:
    def __init__(self):
        self.collector: Optional[SensorDataCollector] = None
        self.dashboard_thread: Optional[threading.Thread] = None
        self.collector_thread: Optional[threading.Thread] = None
        self.running = False
        
    def start_data_collector(self):
        """Start the data collector in a separate thread"""
        print("Starting data collector...")
        self.collector = SensorDataCollector()
        
        def run_collector():
            try:
                self.collector.run()
            except Exception as e:
                print(f"Data collector error: {e}")
                
        self.collector_thread = threading.Thread(target=run_collector, daemon=True)
        self.collector_thread.start()
        print("Data collector started")
        
    def start_dashboard(self):
        """Start the Flask dashboard in a separate thread"""
        print("Starting web dashboard...")
        
        def run_dashboard():
            try:
                app.run(
                    host='0.0.0.0',
                    port=Config.FLASK_PORT,
                    debug=False,  # Set to False when running in thread
                    use_reloader=False,
                    threaded=True
                )
            except Exception as e:
                print(f"Dashboard error: {e}")
                
        self.dashboard_thread = threading.Thread(target=run_dashboard, daemon=True)
        self.dashboard_thread.start()
        
        # Wait a moment for Flask to start
        time.sleep(2)
        print(f"Web dashboard started at http://localhost:{Config.FLASK_PORT}")
        
    def start(self):
        """Start the complete monitoring system"""
        print("=" * 60)
        print("   ENVIRONMENTAL MONITORING SYSTEM")
        print("   LoRaWAN IoT Project")
        print("=" * 60)
        
        self.running = True
        
        # Start components
        self.start_data_collector()
        self.start_dashboard()
        
        print("\nSystem Status:")
        print("✓ Data Collector: Running")
        print("✓ Web Dashboard: Running")
        print(f"✓ Database: {Config.DATABASE_PATH}")
        print(f"✓ TTN Device: {Config.TTN_DEVICE_ID}")
        print("\nAccess your dashboard at: http://localhost:5000")
        print("\nPress Ctrl+C to stop the system")
        
        try:
            # Keep main thread alive
            while self.running:
                time.sleep(1)
                
        except KeyboardInterrupt:
            self.stop()
            
    def stop(self):
        """Stop the monitoring system"""
        print("\n" + "=" * 60)
        print("Shutting down Environmental Monitoring System...")
        
        self.running = False
        
        # Stop data collector
        if self.collector:
            self.collector.stop()
            print("✓ Data collector stopped")
            
        # Note: Flask will stop when main thread ends due to daemon=True
        print("✓ Web dashboard stopped")
        print("✓ System shutdown complete")
        print("=" * 60)

def signal_handler(signum, frame):
    """Handle system signals for graceful shutdown"""
    print(f"\nReceived signal {signum}")
    sys.exit(0)

if __name__ == "__main__":
    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Check if running in development mode
    if len(sys.argv) > 1:
        mode = sys.argv[1].lower()
        
        if mode == "collector":
            # Run only data collector
            print("Running in DATA COLLECTOR mode")
            collector = SensorDataCollector()
            collector.run()
            
        elif mode == "dashboard":
            # Run only dashboard
            print("Running in DASHBOARD mode")
            app.run(
                host='0.0.0.0',
                port=Config.FLASK_PORT,
                debug=Config.FLASK_DEBUG
            )
            
        elif mode == "test":
            # Run tests (you can add test functions here)
            print("Running in TEST mode")
            from src.data_collector import SensorDataCollector
            collector = SensorDataCollector()
            
            # Test database connection
            try:
                collector.setup_database()
                print("✓ Database connection successful")
            except Exception as e:
                print(f"✗ Database error: {e}")
                
            # Test TTN API
            try:
                result = collector.fetch_historical_data()
                if result:
                    print("✓ TTN API connection successful")
                else:
                    print("✗ TTN API connection failed")
            except Exception as e:
                print(f"✗ TTN API error: {e}")
                
        else:
            print(f"Unknown mode: {mode}")
            print("Available modes: collector, dashboard, test")
    else:
        # Run complete system
        system = EnvironmentalMonitoringSystem()
        system.start()
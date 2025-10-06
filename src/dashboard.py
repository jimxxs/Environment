# src/dashboard.py
from flask import Flask, render_template, jsonify, request
import sqlite3
import json
from datetime import datetime, timedelta
import os
import sys
import logging

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.settings import Config

app = Flask(__name__, 
           template_folder=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'templates'),
           static_folder=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'static'))

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class DashboardData:
    def __init__(self):
        self.config = Config()
        
    def get_connection(self):
        """Get database connection"""
        db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), self.config.DATABASE_PATH)
        return sqlite3.connect(db_path)
        
    def get_latest_reading(self):
        """Get the most recent sensor reading"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT timestamp, temperature, humidity, battery_voltage, motion_count
                FROM sensor_readings 
                ORDER BY timestamp DESC 
                LIMIT 1
            ''')
            
            result = cursor.fetchone()
            conn.close()
            
            if result:
                return {
                    'timestamp': result[0],
                    'temperature': result[1],
                    'humidity': result[2],
                    'battery': result[3],
                    'motion': result[4]
                }
            return None
            
        except Exception as e:
            print(f"Error getting latest reading: {e}")
            return None
            
    def get_historical_data(self, hours=24):
        """Get historical sensor data"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cutoff_time = datetime.now() - timedelta(hours=hours)
            
            cursor.execute('''
                SELECT timestamp, temperature, humidity, battery_voltage, motion_count
                FROM sensor_readings 
                WHERE datetime(timestamp) >= datetime(?)
                ORDER BY timestamp
            ''', (cutoff_time.isoformat(),))
            
            results = cursor.fetchall()
            conn.close()
            
            return [
                {
                    'timestamp': row[0],
                    'temperature': row[1],
                    'humidity': row[2],
                    'battery': row[3],
                    'motion': row[4]
                }
                for row in results
            ]
            
        except Exception as e:
            print(f"Error getting historical data: {e}")
            return []
            
    def get_summary_stats(self):
        """Get summary statistics"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT 
                    COUNT(*) as total_readings,
                    MIN(temperature) as min_temp,
                    MAX(temperature) as max_temp,
                    AVG(temperature) as avg_temp,
                    MIN(humidity) as min_humidity,
                    MAX(humidity) as max_humidity,
                    AVG(humidity) as avg_humidity,
                    MIN(battery_voltage) as min_battery,
                    MAX(battery_voltage) as max_battery,
                    AVG(battery_voltage) as avg_battery,
                    MIN(timestamp) as first_reading,
                    MAX(timestamp) as last_reading
                FROM sensor_readings
                WHERE timestamp >= datetime('now', '-7 days')
            ''')
            
            result = cursor.fetchone()
            conn.close()
            
            if result and result[0] > 0:
                return {
                    'total_readings': result[0],
                    'temperature': {
                        'min': round(result[1], 1) if result[1] else 0,
                        'max': round(result[2], 1) if result[2] else 0,
                        'avg': round(result[3], 1) if result[3] else 0
                    },
                    'humidity': {
                        'min': round(result[4], 1) if result[4] else 0,
                        'max': round(result[5], 1) if result[5] else 0,
                        'avg': round(result[6], 1) if result[6] else 0
                    },
                    'battery': {
                        'min': round(result[7], 2) if result[7] else 0,
                        'max': round(result[8], 2) if result[8] else 0,
                        'avg': round(result[9], 2) if result[9] else 0
                    },
                    'period': {
                        'start': result[10],
                        'end': result[11]
                    }
                }
            return None
            
        except Exception as e:
            print(f"Error getting summary stats: {e}")
            return None
            
    def get_alerts(self, limit=10):
        """Get recent alerts"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT timestamp, alert_type, message, value, threshold, resolved
                FROM alerts 
                ORDER BY timestamp DESC 
                LIMIT ?
            ''', (limit,))
            
            results = cursor.fetchall()
            conn.close()
            
            return [
                {
                    'timestamp': row[0],
                    'type': row[1],
                    'message': row[2],
                    'value': row[3],
                    'threshold': row[4],
                    'resolved': bool(row[5])
                }
                for row in results
            ]
            
        except Exception as e:
            print(f"Error getting alerts: {e}")
            return []

# Initialize data handler
dashboard_data = DashboardData()

@app.route('/')
def index():
    """Main dashboard page"""
    return render_template('dashboard.html')

@app.route('/api/latest')
def api_latest():
    """API endpoint for latest sensor reading"""
    data = dashboard_data.get_latest_reading()
    return jsonify(data)

@app.route('/api/historical')
def api_historical():
    """API endpoint for historical data"""
    hours = request.args.get('hours', 24, type=int)
    logger.debug(f"Fetching historical data for last {hours} hours")
    data = dashboard_data.get_historical_data(hours)
    logger.debug(f"Retrieved {len(data)} records")
    return jsonify(data)

@app.route('/api/stats')
def api_stats():
    """API endpoint for summary statistics"""
    data = dashboard_data.get_summary_stats()
    return jsonify(data)

@app.route('/api/alerts')
def api_alerts():
    """API endpoint for alerts"""
    limit = request.args.get('limit', 10, type=int)
    data = dashboard_data.get_alerts(limit)
    return jsonify(data)

@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()})

@app.route('/api/debug/database')
def debug_database():
    """Debug endpoint to check database status"""
    try:
        conn = dashboard_data.get_connection()
        cursor = conn.cursor()
        
        # Check table exists
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='sensor_readings'
        """)
        tables = cursor.fetchall()
        
        # Get row count
        cursor.execute("SELECT COUNT(*) FROM sensor_readings")
        count = cursor.fetchone()[0]
        
        # Get sample data
        cursor.execute("""
            SELECT timestamp, temperature, humidity, battery_voltage, motion_count 
            FROM sensor_readings 
            ORDER BY timestamp DESC 
            LIMIT 1
        """)
        latest = cursor.fetchone()
        
        conn.close()
        
        return jsonify({
            'status': 'ok',
            'tables': tables,
            'row_count': count,
            'latest_reading': latest
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500

if __name__ == '__main__':
    app.run(debug=Config.FLASK_DEBUG, port=Config.FLASK_PORT, host='0.0.0.0')
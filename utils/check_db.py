import sqlite3
import os

def check_database():
    db_path = os.path.join('data', 'sensor_data.db')
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check table structure
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        print("Database tables:", [table[0] for table in tables])
        
        # Check sensor_readings table
        cursor.execute("PRAGMA table_info(sensor_readings);")
        columns = cursor.fetchall()
        print("\nTable structure:")
        for col in columns:
            print(f"- {col[1]} ({col[2]})")
            
        # Get sample data
        cursor.execute("""
            SELECT timestamp, temperature, humidity, battery_voltage, motion_count 
            FROM sensor_readings 
            LIMIT 5
        """)
        samples = cursor.fetchall()
        print("\nSample readings:")
        for sample in samples:
            print(sample)
            
        conn.close()
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_database()
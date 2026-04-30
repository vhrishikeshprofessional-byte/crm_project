import mysql.connector
import json


def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="root",
        database="hcp_crm_db"
    )


def init_db():
    conn = mysql.connector.connect(
        host="localhost",
        user="root",
        password="root"
    )
    cursor = conn.cursor()
    cursor.execute("CREATE DATABASE IF NOT EXISTS hcp_crm_db")
    cursor.execute("USE hcp_crm_db")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS interactions (
            id INT AUTO_INCREMENT PRIMARY KEY,
            hcp_name VARCHAR(255),
            interaction_type VARCHAR(100),
            date DATE,
            time TIME,
            attendees JSON,
            topics_discussed TEXT,
            materials_shared JSON,
            samples_distributed JSON,
            sentiment VARCHAR(50),
            outcomes TEXT,
            follow_ups JSON,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    cursor.close()
    conn.close()


def clean(value):
    """Convert string 'null' or empty string to Python None."""
    if value is None:
        return None
    if isinstance(value, str) and value.strip().lower() in ("null", "none", ""):
        return None
    return value


def clean_list(value):
    """Ensure value is a proper list, never null string."""
    if value is None:
        return json.dumps([])
    if isinstance(value, str) and value.strip().lower() in ("null", "none", ""):
        return json.dumps([])
    if isinstance(value, list):
        return json.dumps(value)
    return json.dumps([])


def save_to_mysql(data: dict):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO interactions
        (hcp_name, interaction_type, date, time, attendees, topics_discussed,
         materials_shared, samples_distributed, sentiment, outcomes, follow_ups)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, (
        clean(data.get("hcp_name")),
        clean(data.get("interaction_type")),
        clean(data.get("date")),
        clean(data.get("time")),
        clean_list(data.get("attendees")),
        clean(data.get("topics_discussed")),
        clean_list(data.get("materials_shared")),
        clean_list(data.get("samples_distributed")),
        clean(data.get("sentiment")),
        clean(data.get("outcomes")),
        clean_list(data.get("follow_ups")),
    ))

    conn.commit()
    cursor.close()
    conn.close()
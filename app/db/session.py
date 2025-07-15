import sqlite3
from app.core.config import DATABASE_FILE
from app.core.logger import logger

def init_db():
    """Initializes the database and creates the incidents table if it doesn't exist."""
    try:
        with sqlite3.connect(DATABASE_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS incidents (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    event TEXT NOT NULL,
                    severity TEXT,
                    location_x REAL,
                    location_y REAL
                )
            """)
            conn.commit()
        logger.info("Database initialized successfully.")
    except sqlite3.Error as e:
        logger.error(f"Database initialization failed: {e}")

def log_incident(event: str, severity: str | None = None, location: tuple | None = None):
    """Logs an incident to the database."""
    try:
        with sqlite3.connect(DATABASE_FILE) as conn:
            cursor = conn.cursor()
            loc_x = location[0] if location else None
            loc_y = location[1] if location else None
            cursor.execute(
                "INSERT INTO incidents (event, severity, location_x, location_y) VALUES (?, ?, ?, ?)",
                (event, severity, loc_x, loc_y)
            )
            conn.commit()
    except sqlite3.Error as e:
        logger.error(f"Failed to log incident: {e}")

def get_incident_history() -> list:
    """Retrieves all incidents from the database."""
    try:
        with sqlite3.connect(DATABASE_FILE) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM incidents ORDER BY timestamp DESC")
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
    except sqlite3.Error as e:
        logger.error(f"Failed to retrieve incident history: {e}")
        return []
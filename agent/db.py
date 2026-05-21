import sqlite3
import json
import uuid
from datetime import datetime
from agent.config import DB_PATH

def get_connection():
    """Establishes connection to the SQLite database."""
    conn = sqlite3.connect(str(DB_PATH))
    # Enable dict factory for cleaner JSON conversions
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initializes tables if they do not exist."""
    conn = get_connection()
    cursor = conn.cursor()
    
    # 1. Sessions Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS sessions (
        session_id TEXT PRIMARY KEY,
        title TEXT NOT NULL,
        created_at TEXT NOT NULL
    )
    """)
    
    # 2. Messages Table (rolling conversation logs)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS messages (
        message_id TEXT PRIMARY KEY,
        session_id TEXT NOT NULL,
        role TEXT NOT NULL,
        content TEXT NOT NULL,
        timestamp TEXT NOT NULL,
        FOREIGN KEY (session_id) REFERENCES sessions (session_id) ON DELETE CASCADE
    )
    """)
    
    # 3. Turns Table (deep research process metadata)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS turns (
        turn_id TEXT PRIMARY KEY,
        session_id TEXT NOT NULL,
        query TEXT NOT NULL,
        search_queries TEXT NOT NULL,  -- JSON string of list of queries
        urls_opened TEXT NOT NULL,     -- JSON string of list of URLs
        context_snippets TEXT NOT NULL, -- JSON string of selected snippets
        final_answer TEXT NOT NULL,
        timestamp TEXT NOT NULL,
        FOREIGN KEY (session_id) REFERENCES sessions (session_id) ON DELETE CASCADE
    )
    """)
    
    conn.commit()
    conn.close()

def create_session(session_id=None, title="New Research Session"):
    """Creates a new session in the database."""
    if not session_id:
        session_id = str(uuid.uuid4())
    created_at = datetime.now().isoformat()
    
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO sessions (session_id, title, created_at) VALUES (?, ?, ?)",
        (session_id, title, created_at)
    )
    conn.commit()
    conn.close()
    return session_id

def update_session_title(session_id, new_title):
    """Updates the title of an existing session."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE sessions SET title = ? WHERE session_id = ?",
        (new_title, session_id)
    )
    conn.commit()
    conn.close()

def get_all_sessions():
    """Retrieves all sessions ordered by creation date."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM sessions ORDER BY created_at DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_session(session_id):
    """Retrieves a single session by ID."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM sessions WHERE session_id = ?", (session_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def delete_session(session_id):
    """Deletes a session and all associated cascade records."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("PRAGMA foreign_keys = ON")
    cursor.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
    conn.commit()
    conn.close()

def save_message(session_id, role, content):
    """Persists a single message in the chat history."""
    message_id = str(uuid.uuid4())
    timestamp = datetime.now().isoformat()
    
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO messages (message_id, session_id, role, content, timestamp) VALUES (?, ?, ?, ?, ?)",
        (message_id, session_id, role, content, timestamp)
    )
    conn.commit()
    conn.close()
    return message_id

def get_messages(session_id):
    """Retrieves all messages for a session ordered by timestamp."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM messages WHERE session_id = ? ORDER BY timestamp ASC", (session_id,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def save_turn(session_id, query, search_queries, urls_opened, context_snippets, final_answer):
    """Persists detailed telemetry of an orchestrator turn execution loop."""
    turn_id = str(uuid.uuid4())
    timestamp = datetime.now().isoformat()
    
    # Serialize JSON fields
    search_queries_str = json.dumps(search_queries)
    urls_opened_str = json.dumps(urls_opened)
    context_snippets_str = json.dumps(context_snippets)
    
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO turns (turn_id, session_id, query, search_queries, urls_opened, context_snippets, final_answer, timestamp)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (turn_id, session_id, query, search_queries_str, urls_opened_str, context_snippets_str, final_answer, timestamp)
    )
    conn.commit()
    conn.close()
    return turn_id

def get_turns(session_id):
    """Retrieves all telemetry turns for a session."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM turns WHERE session_id = ? ORDER BY timestamp ASC", (session_id,))
    rows = cursor.fetchall()
    conn.close()
    
    turns = []
    for row in rows:
        turn = dict(row)
        # Deserialize JSON fields back into Python structures
        turn["search_queries"] = json.loads(turn["search_queries"])
        turn["urls_opened"] = json.loads(turn["urls_opened"])
        turn["context_snippets"] = json.loads(turn["context_snippets"])
        turns.append(turn)
    return turns

# Initialize database schemas automatically when module is imported
init_db()

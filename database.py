import sqlite3
import os
from datetime import datetime
from pathlib import Path

DB_PATH = "perf_detector.db"

def init_database():
    """Initialize the database with all required tables."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Metrics table - stores response times from the application
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS metrics (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        response_time_ms REAL NOT NULL,
        endpoint TEXT DEFAULT '/api/test',
        status_code INTEGER DEFAULT 200,
        error_message TEXT
    )
    ''')
    
    # Deployments table - records when deployments happen
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS deployments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        version TEXT NOT NULL,
        commit_hash TEXT,
        description TEXT
    )
    ''')
    
    # Regressions table - stores detected performance regressions
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS regressions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        detected_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        regression_start_time DATETIME NOT NULL,
        metric_increase_percent REAL NOT NULL,
        baseline_ms REAL NOT NULL,
        current_ms REAL NOT NULL,
        likely_deployment_id INTEGER,
        status TEXT DEFAULT 'active',
        FOREIGN KEY (likely_deployment_id) REFERENCES deployments(id)
    )
    ''')
    
    # Index for faster queries
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_metrics_timestamp ON metrics(timestamp)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_deployments_timestamp ON deployments(timestamp)')
    
    conn.commit()
    conn.close()
    
    print(f"✓ Database initialized at {DB_PATH}")


def get_connection():
    """Get a database connection."""
    return sqlite3.connect(DB_PATH)


def record_deployment(version, commit_hash=None, description=None):
    """Record a deployment event."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
    INSERT INTO deployments (version, commit_hash, description)
    VALUES (?, ?, ?)
    ''', (version, commit_hash, description))
    
    conn.commit()
    deployment_id = cursor.lastrowid
    conn.close()
    
    print(f"✓ Deployment recorded (v{version}, ID: {deployment_id})")
    return deployment_id


def record_metric(response_time_ms, endpoint='/api/test', status_code=200, error_message=None):
    """Record a performance metric."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
    INSERT INTO metrics (response_time_ms, endpoint, status_code, error_message)
    VALUES (?, ?, ?, ?)
    ''', (response_time_ms, endpoint, status_code, error_message))
    
    conn.commit()
    conn.close()


def get_metrics_summary():
    """Get a summary of metrics collected."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT COUNT(*) as total_metrics FROM metrics')
    total = cursor.fetchone()[0]
    
    cursor.execute('SELECT AVG(response_time_ms) as avg_ms FROM metrics')
    avg = cursor.fetchone()[0] or 0
    
    cursor.execute('SELECT COUNT(*) as total_deployments FROM deployments')
    deployments = cursor.fetchone()[0]
    
    conn.close()
    
    return {
        'total_metrics': total,
        'avg_response_time_ms': round(avg, 2),
        'total_deployments': deployments
    }

import sqlite3
import os
from datetime import datetime

def init_db():
    db_file = 'installation_state.db'
    if not os.path.exists(db_file):
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()
        
        # Create installations table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS installations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                host TEXT NOT NULL,
                tool TEXT NOT NULL,
                version TEXT NOT NULL,
                date TEXT NOT NULL
            )
        ''')

        # Create host statuses table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS host_statuses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                host TEXT NOT NULL,
                accessible INTEGER NOT NULL,
                needs_sudo_password INTEGER NOT NULL,
                last_checked TEXT NOT NULL
            )
        ''')

        conn.commit()
        conn.close()

def log_installation(host, tool, version):
    conn = sqlite3.connect('installation_state.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO installations (host, tool, version, date)
        VALUES (?, ?, ?, ?)
    ''', (host, tool, version, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    conn.close()

def check_installation(host, tool):
    conn = sqlite3.connect('installation_state.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT * FROM installations WHERE host = ? AND tool = ?
    ''', (host, tool))
    result = cursor.fetchone()
    conn.close()
    return result is not None

def update_installation(host, tool, remove=False):
    conn = sqlite3.connect('installation_state.db')
    cursor = conn.cursor()
    if remove:
        cursor.execute('''
            DELETE FROM installations WHERE host = ? AND tool = ?
        ''', (host, tool))
    conn.commit()
    conn.close()

def log_host_status(host, accessible, needs_sudo_password):
    conn = sqlite3.connect('installation_state.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO host_statuses (host, accessible, needs_sudo_password, last_checked)
        VALUES (?, ?, ?, ?)
    ''', (host, accessible, needs_sudo_password, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    conn.close()

def update_host_status(host, accessible, needs_sudo_password):
    conn = sqlite3.connect('installation_state.db')
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE host_statuses
        SET accessible = ?, needs_sudo_password = ?, last_checked = ?
        WHERE host = ?
    ''', (accessible, needs_sudo_password, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), host))
    conn.commit()
    conn.close()

def get_host_status(host):
    conn = sqlite3.connect('installation_state.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT accessible, needs_sudo_password, last_checked
        FROM host_statuses
        WHERE host = ?
    ''', (host,))
    result = cursor.fetchone()
    conn.close()
    return result

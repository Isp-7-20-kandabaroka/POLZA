"""
Database layer - SQLite
"""

import sqlite3
from datetime import datetime
from typing import Optional
from contextlib import contextmanager

DB_PATH = "bot_data.db"

@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()

def init_db():
    with get_db() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS specialists (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                photo_file_id TEXT,
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            CREATE TABLE IF NOT EXISTS time_slots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                time TEXT NOT NULL UNIQUE,
                is_active INTEGER DEFAULT 1
            );
            
            CREATE TABLE IF NOT EXISTS bookings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                specialist_id TEXT NOT NULL,
                date TEXT NOT NULL,
                time TEXT NOT NULL,
                booking_type TEXT DEFAULT 'scheduled',
                client_name TEXT,
                client_phone TEXT,
                client_username TEXT,
                client_user_id INTEGER,
                status TEXT DEFAULT 'confirmed',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (specialist_id) REFERENCES specialists(id)
            );
            
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            );
            
            CREATE INDEX IF NOT EXISTS idx_bookings_date ON bookings(specialist_id, date);
        """)
        
        # Migration: add photo_file_id if not exists
        try:
            conn.execute("ALTER TABLE specialists ADD COLUMN photo_file_id TEXT")
        except sqlite3.OperationalError:
            pass
        
        # Migration: add booking_type if not exists
        try:
            conn.execute("ALTER TABLE bookings ADD COLUMN booking_type TEXT DEFAULT 'scheduled'")
        except sqlite3.OperationalError:
            pass

# ═══════════════════════════════════════════════════════════
# SETTINGS
# ═══════════════════════════════════════════════════════════

def get_setting(key: str, default: str = "") -> str:
    with get_db() as conn:
        row = conn.execute(
            "SELECT value FROM settings WHERE key = ?", (key,)
        ).fetchone()
        return row[0] if row else default

def set_setting(key: str, value: str):
    with get_db() as conn:
        conn.execute("""
            INSERT INTO settings (key, value) VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
        """, (key, value))

# ═══════════════════════════════════════════════════════════
# SPECIALISTS
# ═══════════════════════════════════════════════════════════

def get_specialists(active_only: bool = True) -> list[dict]:
    with get_db() as conn:
        if active_only:
            rows = conn.execute(
                "SELECT * FROM specialists WHERE is_active = 1 ORDER BY name"
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM specialists ORDER BY is_active DESC, name"
            ).fetchall()
        return [dict(row) for row in rows]

def get_specialist(spec_id: str) -> Optional[dict]:
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM specialists WHERE id = ?", (spec_id,)
        ).fetchone()
        return dict(row) if row else None

def add_specialist(spec_id: str, name: str, description: str = "", photo_file_id: str = None) -> bool:
    try:
        with get_db() as conn:
            conn.execute(
                "INSERT INTO specialists (id, name, description, photo_file_id) VALUES (?, ?, ?, ?)",
                (spec_id, name, description, photo_file_id)
            )
        return True
    except sqlite3.IntegrityError:
        return False

def update_specialist(spec_id: str, name: str = None, description: str = None) -> bool:
    spec = get_specialist(spec_id)
    if not spec:
        return False
    
    with get_db() as conn:
        conn.execute(
            "UPDATE specialists SET name = ?, description = ? WHERE id = ?",
            (
                name if name is not None else spec['name'],
                description if description is not None else spec['description'],
                spec_id
            )
        )
    return True

def update_specialist_photo(spec_id: str, photo_file_id: str) -> bool:
    with get_db() as conn:
        conn.execute(
            "UPDATE specialists SET photo_file_id = ? WHERE id = ?",
            (photo_file_id, spec_id)
        )
    return True

def toggle_specialist(spec_id: str) -> bool:
    with get_db() as conn:
        conn.execute(
            "UPDATE specialists SET is_active = NOT is_active WHERE id = ?",
            (spec_id,)
        )
    return True

def delete_specialist(spec_id: str) -> bool:
    with get_db() as conn:
        conn.execute("DELETE FROM specialists WHERE id = ?", (spec_id,))
    return True

# ═══════════════════════════════════════════════════════════
# TIME SLOTS
# ═══════════════════════════════════════════════════════════

def get_time_slots(active_only: bool = True) -> list[dict]:
    with get_db() as conn:
        if active_only:
            rows = conn.execute(
                "SELECT * FROM time_slots WHERE is_active = 1 ORDER BY time"
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM time_slots ORDER BY time"
            ).fetchall()
        return [dict(row) for row in rows]

def add_time_slot(time: str) -> bool:
    try:
        with get_db() as conn:
            conn.execute("INSERT INTO time_slots (time) VALUES (?)", (time,))
        return True
    except sqlite3.IntegrityError:
        return False

def toggle_time_slot(slot_id: int) -> bool:
    with get_db() as conn:
        conn.execute(
            "UPDATE time_slots SET is_active = NOT is_active WHERE id = ?",
            (slot_id,)
        )
    return True

def delete_time_slot(slot_id: int) -> bool:
    with get_db() as conn:
        conn.execute("DELETE FROM time_slots WHERE id = ?", (slot_id,))
    return True

# ═══════════════════════════════════════════════════════════
# BOOKINGS
# ═══════════════════════════════════════════════════════════

def is_slot_available(specialist_id: str, date: str, time: str) -> bool:
    with get_db() as conn:
        row = conn.execute(
            """SELECT 1 FROM bookings 
               WHERE specialist_id = ? AND date = ? AND time = ? AND status = 'confirmed'""",
            (specialist_id, date, time)
        ).fetchone()
        return row is None

def create_booking(
    specialist_id: str, date: str, time: str,
    client_name: str, client_phone: str, 
    client_username: str, client_user_id: int,
    booking_type: str = 'scheduled'
) -> int:
    with get_db() as conn:
        cursor = conn.execute(
            """INSERT INTO bookings 
               (specialist_id, date, time, client_name, client_phone, client_username, client_user_id, booking_type)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (specialist_id, date, time, client_name, client_phone, client_username, client_user_id, booking_type)
        )
        return cursor.lastrowid

def get_bookings(
    specialist_id: str = None, 
    date_from: str = None,
    date_to: str = None,
    status: str = 'confirmed',
    limit: int = 50
) -> list[dict]:
    with get_db() as conn:
        query = """
            SELECT b.*, s.name as specialist_name 
            FROM bookings b
            JOIN specialists s ON b.specialist_id = s.id
            WHERE 1=1
        """
        params = []
        
        if specialist_id:
            query += " AND b.specialist_id = ?"
            params.append(specialist_id)
        if date_from:
            query += " AND b.date >= ?"
            params.append(date_from)
        if date_to:
            query += " AND b.date <= ?"
            params.append(date_to)
        if status:
            query += " AND b.status = ?"
            params.append(status)
        
        query += " ORDER BY b.date DESC, b.time DESC LIMIT ?"
        params.append(limit)
        
        rows = conn.execute(query, params).fetchall()
        return [dict(row) for row in rows]

def cancel_booking(booking_id: int) -> bool:
    with get_db() as conn:
        conn.execute(
            "UPDATE bookings SET status = 'cancelled' WHERE id = ?",
            (booking_id,)
        )
    return True

def get_booking(booking_id: int) -> Optional[dict]:
    with get_db() as conn:
        row = conn.execute(
            """SELECT b.*, s.name as specialist_name 
               FROM bookings b
               JOIN specialists s ON b.specialist_id = s.id
               WHERE b.id = ?""",
            (booking_id,)
        ).fetchone()
        return dict(row) if row else None

# ═══════════════════════════════════════════════════════════
# STATISTICS
# ═══════════════════════════════════════════════════════════

def get_stats() -> dict:
    with get_db() as conn:
        today = datetime.now().strftime("%Y-%m-%d")
        
        total = conn.execute(
            "SELECT COUNT(*) FROM bookings WHERE status = 'confirmed'"
        ).fetchone()[0]
        
        today_count = conn.execute(
            "SELECT COUNT(*) FROM bookings WHERE date = ? AND status = 'confirmed'",
            (today,)
        ).fetchone()[0]
        
        upcoming = conn.execute(
            "SELECT COUNT(*) FROM bookings WHERE date >= ? AND status = 'confirmed'",
            (today,)
        ).fetchone()[0]
        
        cancelled = conn.execute(
            "SELECT COUNT(*) FROM bookings WHERE status = 'cancelled'"
        ).fetchone()[0]
        
        specialists_count = conn.execute(
            "SELECT COUNT(*) FROM specialists WHERE is_active = 1"
        ).fetchone()[0]
        
        return {
            'total_bookings': total,
            'today_bookings': today_count,
            'upcoming_bookings': upcoming,
            'cancelled_bookings': cancelled,
            'active_specialists': specialists_count,
        }

# ═══════════════════════════════════════════════════════════
# SEED DATA
# ═══════════════════════════════════════════════════════════

def seed_default_data():
    """Initial data if DB is empty"""
    specs = get_specialists(active_only=False)
    if not specs:
        add_specialist("anna", "Анна Иванова", "👩‍⚕️ Психолог · 10 лет опыта\n\n✨ Специализация:\n• Тревожность и стресс\n• Депрессия\n• Отношения и семья")
        add_specialist("sergey", "Сергей Петров", "👨‍💼 Коуч · Бизнес-консультант\n\n✨ Помогаю:\n• Достигать целей\n• Масштабировать бизнес\n• Выходить из кризисов")
        add_specialist("maria", "Мария Сидорова", "👩‍🔬 Нутрициолог · Диетолог\n\n✨ Работаю с:\n• Снижением веса\n• Набором массы\n• Пищевыми привычками")
    
    slots = get_time_slots(active_only=False)
    if not slots:
        for t in ["09:00", "10:00", "11:00", "12:00", "13:00", "14:00", "15:00", "16:00", "17:00", "18:00", "19:00", "20:00"]:
            add_time_slot(t)

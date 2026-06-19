"""
Veritabanı yönetimi - SQLite
Günlük + 15 dakikalık veri desteği
"""

import sqlite3
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime
from config import DATABASE_NAME


def get_connection():
    """Veritabanı bağlantısı"""
    conn = sqlite3.connect(DATABASE_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def init_database():
    """Tabloları oluştur"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Günlük fiyat verileri
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS stock_prices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            date TEXT NOT NULL,
            open REAL,
            high REAL,
            low REAL,
            close REAL,
            volume INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(symbol, date)
        )
    """)
    
    # 15 DAKİKALIK fiyat verileri
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS stock_prices_15m (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            datetime TEXT NOT NULL,
            open REAL,
            high REAL,
            low REAL,
            close REAL,
            volume INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(symbol, datetime)
        )
    """)
    
    # Sinyaller
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            signal_type TEXT NOT NULL,
            price REAL NOT NULL,
            target_price REAL,
            stop_loss REAL,
            score INTEGER,
            strategy TEXT,
            timeframe TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Portföy
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS portfolio (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            buy_price REAL NOT NULL,
            quantity INTEGER NOT NULL,
            buy_date TEXT NOT NULL,
            sell_price REAL,
            sell_date TEXT,
            status TEXT DEFAULT 'open',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_symbol_date ON stock_prices(symbol, date)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_symbol_dt15 ON stock_prices_15m(symbol, datetime)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_signal_symbol ON signals(symbol)")
    
    conn.commit()
    conn.close()
    
    print("✅ Veritabanı hazır (Günlük + 15dk tabloları)")


def save_price_data(symbol, date, open_price, high, low, close, volume):
    """Günlük fiyat verisi kaydet"""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            INSERT OR REPLACE INTO stock_prices 
            (symbol, date, open, high, low, close, volume)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (symbol, date, open_price, high, low, close, volume))
        conn.commit()
    except Exception as e:
        print(f"❌ Veri kaydetme hatası: {e}")
    finally:
        conn.close()


def save_price_data_15m(symbol, dt, open_price, high, low, close, volume):
    """15 dakikalık fiyat verisi kaydet"""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            INSERT OR REPLACE INTO stock_prices_15m 
            (symbol, datetime, open, high, low, close, volume)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (symbol, dt, open_price, high, low, close, volume))
        conn.commit()
    except Exception as e:
        print(f"❌ 15dk veri kaydetme hatası: {e}")
    finally:
        conn.close()


def save_signal(symbol, signal_type, price, target_price, stop_loss, score, strategy, timeframe):
    """Sinyal kaydet"""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            INSERT INTO signals 
            (symbol, signal_type, price, target_price, stop_loss, score, strategy, timeframe)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (symbol, signal_type, price, target_price, stop_loss, score, strategy, timeframe))
        conn.commit()
        return cursor.lastrowid
    except Exception as e:
        print(f"❌ Sinyal kaydetme hatası: {e}")
        return None
    finally:
        conn.close()


def get_latest_signals(limit=20):
    """Son sinyaller"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT * FROM signals 
        ORDER BY created_at DESC 
        LIMIT ?
    """, (limit,))
    
    signals = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return signals


def get_stock_history(symbol, days=100):
    """Günlük hisse geçmişi"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT * FROM stock_prices 
        WHERE symbol = ? 
        ORDER BY date DESC 
        LIMIT ?
    """, (symbol, days))
    
    data = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return data


def get_stock_history_15m(symbol, limit=500):
    """15 dakikalık hisse geçmişi"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT * FROM stock_prices_15m 
        WHERE symbol = ? 
        ORDER BY datetime DESC 
        LIMIT ?
    """, (symbol, limit))
    
    data = [dict(row) for row in cursor.fetchall()]
    for row in data:
        row['date'] = row.get('datetime', '')
    
    conn.close()
    return data


def get_data_stats():
    """Veritabanı istatistikleri"""
    conn = get_connection()
    cursor = conn.cursor()
    
    stats = {}
    
    cursor.execute("SELECT COUNT(DISTINCT symbol) as cnt FROM stock_prices")
    stats['daily_symbols'] = cursor.fetchone()['cnt']
    
    cursor.execute("SELECT COUNT(*) as cnt FROM stock_prices")
    stats['daily_records'] = cursor.fetchone()['cnt']
    
    cursor.execute("SELECT COUNT(DISTINCT symbol) as cnt FROM stock_prices_15m")
    stats['m15_symbols'] = cursor.fetchone()['cnt']
    
    cursor.execute("SELECT COUNT(*) as cnt FROM stock_prices_15m")
    stats['m15_records'] = cursor.fetchone()['cnt']
    
    cursor.execute("SELECT COUNT(*) as cnt FROM signals")
    stats['total_signals'] = cursor.fetchone()['cnt']
    
    conn.close()
    return stats


if __name__ == "__main__":
    init_database()
    print("🎉 Veritabanı kurulumu tamamlandı!")
    
    stats = get_data_stats()
    print(f"\n📊 İSTATİSTİKLER:")
    print(f"   📅 Günlük veri: {stats['daily_symbols']} hisse, {stats['daily_records']} kayıt")
    print(f"   ⏰ 15dk veri  : {stats['m15_symbols']} hisse, {stats['m15_records']} kayıt")
    print(f"   📈 Sinyaller  : {stats['total_signals']} adet")
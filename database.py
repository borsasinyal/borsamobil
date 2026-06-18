"""
Veritabanı yönetimi - SQLite
Hisse verilerini ve sinyalleri saklar
"""

import sqlite3
from datetime import datetime
from config import DATABASE_NAME


def get_connection():
    """Veritabanı bağlantısı oluştur"""
    conn = sqlite3.connect(DATABASE_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def init_database():
    """Veritabanı tablolarını oluştur"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Hisse fiyat verileri tablosu
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
    
    # Sinyaller tablosu
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
    
    # Portföy tablosu
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
    
    # İndekslerimiz (hız için)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_symbol_date ON stock_prices(symbol, date)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_signal_symbol ON signals(symbol)")
    
    conn.commit()
    conn.close()
    
    print("✅ Veritabanı hazır")


def save_price_data(symbol, date, open_price, high, low, close, volume):
    """Hisse fiyat verisini kaydet"""
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
    """Son sinyalleri getir"""
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
    """Hisse geçmiş verilerini getir"""
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


if __name__ == "__main__":
    # Bu dosyayı doğrudan çalıştırırsan veritabanını kurar
    init_database()
    print("🎉 Veritabanı kurulumu tamamlandı!")
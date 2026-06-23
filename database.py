"""
Veritabanı yönetimi - SQLite
Günlük + 15 dakikalık veri + AKTİF SİNYAL TAKİBİ
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
    
    # Sinyaller (geçmiş)
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
    
    # ⭐ YENİ TABLO: AKTİF SİNYALLER (TAKİP EDİLENLER)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS active_signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            entry_price REAL NOT NULL,
            target_1 REAL,
            target_2 REAL,
            target_3 REAL,
            stop_loss REAL,
            score INTEGER,
            
            -- Hedef durumları
            target_1_hit BOOLEAN DEFAULT 0,
            target_2_hit BOOLEAN DEFAULT 0,
            target_3_hit BOOLEAN DEFAULT 0,
            stop_hit BOOLEAN DEFAULT 0,
            
            -- Yaklaşma uyarıları
            near_target_1_alerted BOOLEAN DEFAULT 0,
            near_target_2_alerted BOOLEAN DEFAULT 0,
            near_stop_alerted BOOLEAN DEFAULT 0,
            
            -- Durum
            status TEXT DEFAULT 'active',  -- active, closed, stopped
            
            -- Tarihler
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            closed_at TIMESTAMP,
            
            -- Sonuç
            final_price REAL,
            final_pnl_pct REAL
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
    
    # Index'ler
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_symbol_date ON stock_prices(symbol, date)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_symbol_dt15 ON stock_prices_15m(symbol, datetime)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_signal_symbol ON signals(symbol)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_active_symbol ON active_signals(symbol)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_active_status ON active_signals(status)")
    
    conn.commit()
    conn.close()
    
    print("✅ Veritabanı hazır (Günlük + 15dk + Aktif Sinyal Takibi)")


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
    """Sinyal kaydet (geçmiş + AKTİF SİNYALE OTOMATİK EKLE)"""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        # Geçmiş sinyalleri kaydet
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


# ════════════════════════════════════════════════════════════
# YENİ: AKTİF SİNYAL TAKİP FONKSİYONLARI
# ════════════════════════════════════════════════════════════

def add_active_signal(symbol, entry_price, target_1, target_2, target_3, stop_loss, score):
    """
    Yeni aktif sinyal ekle (takip edilecek)
    
    Eğer aynı sembol için zaten aktif sinyal varsa, eklemez!
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        # Aynı sembol için aktif sinyal var mı kontrol et
        cursor.execute("""
            SELECT COUNT(*) as count FROM active_signals
            WHERE symbol = ? AND status = 'active'
        """, (symbol,))
        
        existing = cursor.fetchone()
        if existing and existing['count'] > 0:
            print(f"⚠️ {symbol} zaten aktif takipte")
            return None
        
        # Yeni aktif sinyal ekle
        cursor.execute("""
            INSERT INTO active_signals 
            (symbol, entry_price, target_1, target_2, target_3, stop_loss, score, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'active')
        """, (symbol, entry_price, target_1, target_2, target_3, stop_loss, score))
        
        conn.commit()
        signal_id = cursor.lastrowid
        print(f"✅ {symbol} aktif takibe alındı (ID: {signal_id})")
        return signal_id
    except Exception as e:
        print(f"❌ Aktif sinyal ekleme hatası: {e}")
        return None
    finally:
        conn.close()


def get_active_signals():
    """Tüm aktif sinyalleri getir"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT * FROM active_signals 
        WHERE status = 'active'
        ORDER BY created_at DESC
    """)
    
    signals = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return signals


def update_target_hit(signal_id, target_num):
    """Hedef vuruldu olarak işaretle"""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        column = f"target_{target_num}_hit"
        cursor.execute(f"""
            UPDATE active_signals 
            SET {column} = 1
            WHERE id = ?
        """, (signal_id,))
        
        conn.commit()
        print(f"✅ Sinyal #{signal_id} - Hedef {target_num} vuruldu")
    except Exception as e:
        print(f"❌ Hedef güncelleme hatası: {e}")
    finally:
        conn.close()


def update_near_target_alerted(signal_id, target_num):
    """Hedef yaklaşma uyarısı gönderildi olarak işaretle"""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        column = f"near_target_{target_num}_alerted"
        cursor.execute(f"""
            UPDATE active_signals 
            SET {column} = 1
            WHERE id = ?
        """, (signal_id,))
        
        conn.commit()
    except Exception as e:
        print(f"❌ Yaklaşma uyarısı güncelleme hatası: {e}")
    finally:
        conn.close()


def update_near_stop_alerted(signal_id):
    """Stop yaklaşma uyarısı gönderildi olarak işaretle"""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            UPDATE active_signals 
            SET near_stop_alerted = 1
            WHERE id = ?
        """, (signal_id,))
        
        conn.commit()
    except Exception as e:
        print(f"❌ Stop uyarısı güncelleme hatası: {e}")
    finally:
        conn.close()


def close_active_signal(signal_id, final_price, status='closed'):
    """
    Aktif sinyali kapat
    status: 'closed' (hedef vuruldu), 'stopped' (stop oldu)
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        # Önce entry price'ı al
        cursor.execute("SELECT entry_price FROM active_signals WHERE id = ?", (signal_id,))
        row = cursor.fetchone()
        if not row:
            return
        
        entry_price = row['entry_price']
        pnl_pct = ((final_price - entry_price) / entry_price) * 100
        
        cursor.execute("""
            UPDATE active_signals 
            SET status = ?,
                closed_at = CURRENT_TIMESTAMP,
                final_price = ?,
                final_pnl_pct = ?,
                stop_hit = CASE WHEN ? = 'stopped' THEN 1 ELSE 0 END
            WHERE id = ?
        """, (status, final_price, pnl_pct, status, signal_id))
        
        conn.commit()
        print(f"✅ Sinyal #{signal_id} kapatıldı ({status}, PnL: {pnl_pct:.2f}%)")
    except Exception as e:
        print(f"❌ Sinyal kapatma hatası: {e}")
    finally:
        conn.close()


def get_signal_stats(days=7):
    """Son N günün sinyal istatistikleri"""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN target_1_hit = 1 THEN 1 ELSE 0 END) as t1_hit,
                SUM(CASE WHEN target_2_hit = 1 THEN 1 ELSE 0 END) as t2_hit,
                SUM(CASE WHEN target_3_hit = 1 THEN 1 ELSE 0 END) as t3_hit,
                SUM(CASE WHEN stop_hit = 1 THEN 1 ELSE 0 END) as stop_count,
                AVG(final_pnl_pct) as avg_pnl,
                MAX(final_pnl_pct) as max_pnl,
                MIN(final_pnl_pct) as min_pnl
            FROM active_signals
            WHERE created_at >= datetime('now', '-' || ? || ' days')
            AND status != 'active'
        """, (days,))
        
        stats = dict(cursor.fetchone())
        
        # Win rate hesabı
        if stats['total'] and stats['total'] > 0:
            wins = stats['t1_hit'] or 0
            stats['win_rate'] = round((wins / stats['total']) * 100, 1)
        else:
            stats['win_rate'] = 0
        
        return stats
    except Exception as e:
        print(f"❌ İstatistik hatası: {e}")
        return None
    finally:
        conn.close()


# ════════════════════════════════════════════════════════════
# MEVCUT FONKSİYONLAR
# ════════════════════════════════════════════════════════════

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
    
    # YENİ: Aktif sinyal sayısı
    cursor.execute("SELECT COUNT(*) as cnt FROM active_signals WHERE status = 'active'")
    stats['active_signals'] = cursor.fetchone()['cnt']
    
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
    print(f"   🎯 Aktif takip: {stats['active_signals']} adet")

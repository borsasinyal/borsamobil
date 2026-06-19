"""
Yahoo Finance'den BIST hisse verilerini çeker
Günlük (1d) + 15 dakikalık (15m) veri desteği
"""

import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import BIST_SYMBOLS, TUM_BIST
from database import save_price_data, save_price_data_15m, init_database


# ════════════════════════════════════════════════════════════
# GÜNLÜK VERİ FONKSİYONLARI
# ════════════════════════════════════════════════════════════

def fetch_stock_data(symbol, period="1y"):
    """Tek hisse - GÜNLÜK veri"""
    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(period=period)
        if df.empty:
            return None
        return df
    except Exception:
        return None


def save_daily_to_database(symbol, df):
    """Günlük DataFrame'i veritabanına kaydet"""
    if df is None or df.empty:
        return 0
    
    count = 0
    for date, row in df.iterrows():
        try:
            save_price_data(
                symbol=symbol,
                date=date.strftime("%Y-%m-%d"),
                open_price=float(row['Open']),
                high=float(row['High']),
                low=float(row['Low']),
                close=float(row['Close']),
                volume=int(row['Volume'])
            )
            count += 1
        except Exception:
            pass
    return count


def fetch_all_daily(symbols_list=None, delay=0.1):
    """Tüm hisselerin günlük verisini çek"""
    if symbols_list is None:
        symbols_list = BIST_SYMBOLS
    
    total = len(symbols_list)
    print(f"\n🚀 {total} hisse için GÜNLÜK veri çekiliyor...\n")
    
    success = 0
    failed = 0
    failed_symbols = []
    start_time = time.time()
    
    for i, symbol in enumerate(symbols_list, 1):
        if i % 25 == 0 or i == 1 or i == total:
            elapsed = time.time() - start_time
            avg = elapsed / i if i > 0 else 0
            remaining = avg * (total - i)
            eta_min = int(remaining // 60)
            eta_sec = int(remaining % 60)
            print(f"⏳ [{i}/{total}] ({i*100//total}%) | ✅ {success} | ❌ {failed} | ETA: ~{eta_min}dk {eta_sec}sn")
        
        df = fetch_stock_data(symbol, period="1y")
        
        if df is not None and not df.empty:
            count = save_daily_to_database(symbol, df)
            if count > 0:
                success += 1
            else:
                failed += 1
                failed_symbols.append(symbol)
        else:
            failed += 1
            failed_symbols.append(symbol)
        
        if delay > 0:
            time.sleep(delay)
    
    elapsed_total = time.time() - start_time
    total_min = int(elapsed_total // 60)
    total_sec = int(elapsed_total % 60)
    
    print(f"\n{'='*60}")
    print(f"📊 GÜNLÜK VERİ ÇEKME TAMAMLANDI")
    print(f"{'='*60}")
    print(f"✅ Başarılı     : {success}")
    print(f"❌ Başarısız    : {failed}")
    print(f"⏱️  Toplam     : {total_min}dk {total_sec}sn")
    print(f"{'='*60}")
    
    if failed_symbols and len(failed_symbols) <= 30:
        print(f"\n⚠️  Veri alınamayan hisseler:")
        for sym in failed_symbols:
            print(f"   - {sym}")
    
    return success, failed


# ════════════════════════════════════════════════════════════
# 15 DAKİKALIK VERİ FONKSİYONLARI (YENİ)
# ════════════════════════════════════════════════════════════

def fetch_stock_data_15m(symbol, period="60d"):
    """
    Tek hisse - 15 DAKİKALIK veri
    Yahoo Finance limit: max 60 gün geriye
    """
    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(period=period, interval="15m")
        if df.empty:
            return None
        return df
    except Exception:
        return None


def save_15m_to_database(symbol, df):
    """15dk DataFrame'i veritabanına kaydet"""
    if df is None or df.empty:
        return 0
    
    count = 0
    for dt, row in df.iterrows():
        try:
            save_price_data_15m(
                symbol=symbol,
                dt=dt.strftime("%Y-%m-%d %H:%M:%S"),
                open_price=float(row['Open']),
                high=float(row['High']),
                low=float(row['Low']),
                close=float(row['Close']),
                volume=int(row['Volume'])
            )
            count += 1
        except Exception:
            pass
    return count


def fetch_all_15m(symbols_list=None, delay=0.2):
    """Tüm hisselerin 15 dakikalık verisini çek"""
    if symbols_list is None:
        symbols_list = BIST_SYMBOLS
    
    total = len(symbols_list)
    print(f"\n🚀 {total} hisse için 15 DAKİKALIK veri çekiliyor...")
    print(f"⚠️  Yahoo limit: Son 60 gün")
    print(f"⏱️  Tahmini süre: ~{total * 0.5 // 60:.0f} dakika\n")
    
    success = 0
    failed = 0
    failed_symbols = []
    start_time = time.time()
    
    for i, symbol in enumerate(symbols_list, 1):
        if i % 10 == 0 or i == 1 or i == total:
            elapsed = time.time() - start_time
            avg = elapsed / i if i > 0 else 0
            remaining = avg * (total - i)
            eta_min = int(remaining // 60)
            eta_sec = int(remaining % 60)
            print(f"⏳ [{i}/{total}] ({i*100//total}%) | ✅ {success} | ❌ {failed} | ETA: ~{eta_min}dk {eta_sec}sn")
        
        df = fetch_stock_data_15m(symbol, period="60d")
        
        if df is not None and not df.empty:
            count = save_15m_to_database(symbol, df)
            if count > 0:
                success += 1
            else:
                failed += 1
                failed_symbols.append(symbol)
        else:
            failed += 1
            failed_symbols.append(symbol)
        
        if delay > 0:
            time.sleep(delay)
    
    elapsed_total = time.time() - start_time
    total_min = int(elapsed_total // 60)
    total_sec = int(elapsed_total % 60)
    
    print(f"\n{'='*60}")
    print(f"📊 15dk VERİ ÇEKME TAMAMLANDI")
    print(f"{'='*60}")
    print(f"✅ Başarılı     : {success}")
    print(f"❌ Başarısız    : {failed}")
    print(f"⏱️  Toplam     : {total_min}dk {total_sec}sn")
    print(f"{'='*60}")
    
    return success, failed


# ════════════════════════════════════════════════════════════
# ANLIK FİYAT
# ════════════════════════════════════════════════════════════

def fetch_current_price(symbol):
    """Anlık fiyat"""
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.history(period="1d")
        if not info.empty:
            return float(info['Close'].iloc[-1])
        return None
    except Exception as e:
        print(f"❌ {symbol} anlık fiyat hatası: {e}")
        return None


# ════════════════════════════════════════════════════════════
# ANA MENÜ
# ════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("\n" + "="*60)
    print("📊 BIST VERİ ÇEKME SİSTEMİ - PROFESYONEL")
    print("="*60)
    print(f"\n📋 Toplam {len(BIST_SYMBOLS)} hisse mevcut")
    
    print("\n🎯 SEÇENEKLER:")
    print("  ─── GÜNLÜK VERİ ───")
    print("  1 → Test (5 hisse - günlük)")
    print("  2 → BIST 100 (~100 hisse - günlük) ~5 dk")
    print("  3 → TÜM BIST (~530 hisse - günlük) ~15 dk")
    print()
    print("  ─── 15 DAKİKALIK VERİ ───")
    print("  4 → Test (5 hisse - 15dk)")
    print("  5 → BIST 100 (~100 hisse - 15dk) ~10 dk")
    print("  6 → TÜM BIST (~530 hisse - 15dk) ~50 dk")
    print()
    print("  ─── KOMBİNE ───")
    print("  7 → HER İKİSİ: BIST 100 (günlük + 15dk) ~15 dk")
    print("  8 → HER İKİSİ: TÜM BIST (günlük + 15dk) ~65 dk")
    
    choice = input("\nSeçim (1-8): ").strip()
    
    init_database()
    
    if choice == "1":
        print("\n🧪 5 hisse - günlük...")
        fetch_all_daily(symbols_list=BIST_SYMBOLS[:5])
        
    elif choice == "2":
        print("\n⚡ BIST 100 - günlük...")
        fetch_all_daily(symbols_list=BIST_SYMBOLS[:100])
        
    elif choice == "3":
        print("\n🚀 TÜM BIST - günlük (15 dk sürer)...")
        fetch_all_daily(symbols_list=BIST_SYMBOLS)
        
    elif choice == "4":
        print("\n🧪 5 hisse - 15dk...")
        fetch_all_15m(symbols_list=BIST_SYMBOLS[:5])
        
    elif choice == "5":
        print("\n⚡ BIST 100 - 15dk (10 dk sürer)...")
        fetch_all_15m(symbols_list=BIST_SYMBOLS[:100])
        
    elif choice == "6":
        print("\n🚀 TÜM BIST - 15dk (50 dk sürer)...")
        print("☕ Çayını al, bekle...")
        fetch_all_15m(symbols_list=BIST_SYMBOLS)
        
    elif choice == "7":
        print("\n⚡ BIST 100 - HER İKİSİ...")
        print("\n--- 1. AŞAMA: GÜNLÜK ---")
        fetch_all_daily(symbols_list=BIST_SYMBOLS[:100])
        print("\n--- 2. AŞAMA: 15dk ---")
        fetch_all_15m(symbols_list=BIST_SYMBOLS[:100])
        
    elif choice == "8":
        print("\n🚀 TÜM BIST - HER İKİSİ (65 dk sürer)...")
        print("☕ Bir kahve daha hazırla...")
        print("\n--- 1. AŞAMA: GÜNLÜK ---")
        fetch_all_daily(symbols_list=BIST_SYMBOLS)
        print("\n--- 2. AŞAMA: 15dk ---")
        fetch_all_15m(symbols_list=BIST_SYMBOLS)
    else:
        print("❌ Geçersiz seçim")
        sys.exit(0)
    
    print("\n✅ İşlem tamamlandı!")
    print("👉 Şimdi tarama yap: python services/scanner.py")
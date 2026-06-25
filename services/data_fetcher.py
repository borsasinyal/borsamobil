"""
Yahoo Finance + TradingView Hibrit Veri Çekme
ÖNCELİK: TradingView (anlık veri)
YEDEK: Yahoo Finance (15 dk geç)
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

# TradingView import (varsa)
try:
    from services.tradingview_fetcher import fetch_all_tv, fetch_stock_tv, TV_AVAILABLE
    TV_READY = True
    print("✅ TradingView modülü hazır")
except ImportError as e:
    print(f"⚠️ TradingView modülü yüklenemedi: {e}")
    TV_READY = False
    TV_AVAILABLE = False


# ════════════════════════════════════════════════════════════
# YAHOO FUNCTIONS (YEDEK)
# ════════════════════════════════════════════════════════════

def fetch_stock_data(symbol, period="1y"):
    """Tek hisse - Yahoo Finance - GÜNLÜK veri"""
    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(period=period)
        if df.empty:
            return None
        return df
    except Exception:
        return None


def save_daily_to_database(symbol, df):
    """Yahoo Finance DataFrame'i veritabanına kaydet"""
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


def fetch_all_daily_yahoo(symbols_list=None, delay=0.1):
    """Tüm hisselerin Yahoo'dan günlük verisini çek (YEDEK)"""
    if symbols_list is None:
        symbols_list = BIST_SYMBOLS
    
    total = len(symbols_list)
    print(f"\n🚀 YAHOO: {total} hisse için günlük veri çekiliyor...\n")
    
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
    print(f"📊 YAHOO VERİ ÇEKME TAMAMLANDI")
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
# ANA FONKSİYON - HİBRİT SİSTEM
# ════════════════════════════════════════════════════════════

def fetch_all_daily(symbols_list=None, delay=0.05):
    """
    HİBRİT SİSTEM:
    1. Önce TradingView dene (anlık veri)
    2. TradingView başarısız olursa Yahoo'ya düş (yedek)
    """
    if symbols_list is None:
        symbols_list = BIST_SYMBOLS
    
    print("\n" + "="*60)
    print("🎯 HİBRİT VERİ ÇEKME SİSTEMİ")
    print("="*60)
    
    # 1. ÖNCE TRADINGVIEW DENE
    if TV_READY:
        print("\n📡 1. AŞAMA: TradingView (ANLIK VERİ)")
        print("-" * 60)
        
        try:
            tv_success, tv_failed = fetch_all_tv(symbols_list, delay=0.3)
            
            # Eğer başarı oranı %50'den fazlaysa, sadece TradingView yeterli
            success_rate = (tv_success / len(symbols_list)) * 100 if len(symbols_list) > 0 else 0
            
            print(f"\n📊 TradingView Başarı Oranı: %{success_rate:.1f}")
            
            if success_rate >= 50:
                print("✅ TradingView yeterli, Yahoo'ya gerek yok")
                return tv_success, tv_failed
            else:
                print(f"⚠️ TradingView başarı oranı düşük, Yahoo'ya da bakıyoruz...")
        
        except Exception as e:
            print(f"❌ TradingView hatası: {e}")
            print("🔄 Yahoo'ya geçiliyor...")
    else:
        print("⚠️ TradingView mevcut değil, doğrudan Yahoo kullanılıyor")
    
    # 2. YAHOO YEDEK (Eğer TV başarısızsa veya yetersizse)
    print("\n📡 2. AŞAMA: Yahoo Finance (15 dk geç)")
    print("-" * 60)
    
    yahoo_success, yahoo_failed = fetch_all_daily_yahoo(symbols_list, delay)
    
    return yahoo_success, yahoo_failed


# ════════════════════════════════════════════════════════════
# 15 DAKİKALIK VERİ (YAHOO)
# ════════════════════════════════════════════════════════════

def fetch_stock_data_15m(symbol, period="60d"):
    """15 DAKİKALIK veri - Yahoo (TradingView'da farklı)"""
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
    print(f"\n🚀 {total} hisse için 15 DAKİKALIK veri çekiliyor...\n")
    
    success = 0
    failed = 0
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
        else:
            failed += 1
        
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
    """Anlık fiyat - Önce TV, sonra Yahoo"""
    
    # 1. TradingView dene
    if TV_READY:
        try:
            from services.tradingview_fetcher import get_current_price_tv
            price = get_current_price_tv(symbol)
            if price:
                return price
        except:
            pass
    
    # 2. Yahoo yedek
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
    print("📊 BIST VERİ ÇEKME SİSTEMİ - HİBRİT")
    print("="*60)
    print(f"\n📋 Toplam {len(BIST_SYMBOLS)} hisse mevcut")
    print(f"📡 TradingView: {'✅ HAZIR' if TV_READY else '❌ MEVCUT DEĞİL'}")
    
    print("\n🎯 SEÇENEKLER:")
    print("  1 → Test (5 hisse - Hibrit)")
    print("  2 → BIST 100 (Hibrit)")
    print("  3 → TÜM BIST (Hibrit)")
    print("  4 → Sadece Yahoo (Test)")
    
    choice = input("\nSeçim (1-4): ").strip()
    
    init_database()
    
    if choice == "1":
        print("\n🧪 5 hisse - Hibrit...")
        fetch_all_daily(symbols_list=BIST_SYMBOLS[:5])
    elif choice == "2":
        print("\n⚡ BIST 100 - Hibrit...")
        fetch_all_daily(symbols_list=BIST_SYMBOLS[:100])
    elif choice == "3":
        print("\n🚀 TÜM BIST - Hibrit...")
        fetch_all_daily(symbols_list=BIST_SYMBOLS)
    elif choice == "4":
        print("\n📊 TÜM BIST - Sadece Yahoo...")
        fetch_all_daily_yahoo(symbols_list=BIST_SYMBOLS)
    else:
        print("❌ Geçersiz seçim")
        sys.exit(0)
    
    print("\n✅ İşlem tamamlandı!")

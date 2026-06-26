"""
Hibrit Veri Çekme - Günlük + Saatlik
TradingView öncelikli, Yahoo yedek
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

try:
    from services.tradingview_fetcher import fetch_all_tv, fetch_stock_tv, TV_AVAILABLE
    TV_READY = True
    print("✅ TradingView modülü hazır")
except ImportError as e:
    print(f"⚠️ TradingView yüklenemedi: {e}")
    TV_READY = False
    TV_AVAILABLE = False


# ════════════════════════════════════════════════════════════
# YAHOO YEDEK
# ════════════════════════════════════════════════════════════

def fetch_stock_data(symbol, period="1y"):
    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(period=period)
        if df.empty: return None
        return df
    except: return None


def save_daily_to_database(symbol, df):
    if df is None or df.empty: return 0
    count = 0
    for date, row in df.iterrows():
        try:
            save_price_data(symbol=symbol, date=date.strftime("%Y-%m-%d"),
                          open_price=float(row['Open']), high=float(row['High']),
                          low=float(row['Low']), close=float(row['Close']),
                          volume=int(row['Volume']))
            count += 1
        except: pass
    return count


def fetch_all_daily_yahoo(symbols_list=None, delay=0.1):
    if symbols_list is None: symbols_list = BIST_SYMBOLS
    total = len(symbols_list)
    print(f"\n🚀 YAHOO: {total} hisse günlük veri...\n")
    success = 0
    failed = 0
    start_time = time.time()
    
    for i, symbol in enumerate(symbols_list, 1):
        if i % 25 == 0 or i == 1 or i == total:
            elapsed = time.time() - start_time
            avg = elapsed / i if i > 0 else 0
            remaining = avg * (total - i)
            print(f"⏳ [{i}/{total}] ({i*100//total}%) | ✅ {success} | ❌ {failed} | ETA: ~{int(remaining//60)}dk")
        
        df = fetch_stock_data(symbol, period="1y")
        if df is not None and not df.empty:
            count = save_daily_to_database(symbol, df)
            if count > 0: success += 1
            else: failed += 1
        else: failed += 1
        
        if delay > 0: time.sleep(delay)
    
    elapsed_total = time.time() - start_time
    print(f"\n{'='*60}")
    print(f"📊 YAHOO GÜNLÜK VERİ TAMAMLANDI")
    print(f"✅ Başarılı: {success} | ❌ Başarısız: {failed}")
    print(f"⏱️ Toplam: {int(elapsed_total//60)}dk {int(elapsed_total%60)}sn")
    return success, failed


# ════════════════════════════════════════════════════════════
# ANA FONKSİYON - HİBRİT + SAATLİK
# ════════════════════════════════════════════════════════════

def fetch_all_daily(symbols_list=None, delay=0.05):
    """
    HİBRİT SİSTEM:
    1. TradingView'dan GÜNLÜK veri çek
    2. TradingView'dan SAATLİK veri çek (YENİ!)
    3. Başarısızsa Yahoo'ya düş
    """
    if symbols_list is None:
        symbols_list = BIST_SYMBOLS
    
    print("\n" + "="*60)
    print("🎯 HİBRİT VERİ ÇEKME SİSTEMİ")
    print("="*60)
    
    # 1. GÜNLÜK VERİ (TradingView)
    if TV_READY:
        print("\n📡 1. AŞAMA: TradingView GÜNLÜK VERİ")
        print("-" * 60)
        
        try:
            tv_success, tv_failed = fetch_all_tv(symbols_list, delay=0.3, interval='daily')
            success_rate = (tv_success / len(symbols_list)) * 100 if len(symbols_list) > 0 else 0
            print(f"\n📊 Günlük Başarı: %{success_rate:.1f}")
            
            if success_rate >= 50:
                print("✅ Günlük veri yeterli")
                
                # 2. SAATLİK VERİ (TradingView) - YENİ!
                print("\n📡 2. AŞAMA: TradingView SAATLİK VERİ")
                print("-" * 60)
                
                try:
                    tv_h_success, tv_h_failed = fetch_all_tv(symbols_list, delay=0.3, interval='hourly')
                    h_rate = (tv_h_success / len(symbols_list)) * 100 if len(symbols_list) > 0 else 0
                    print(f"\n📊 Saatlik Başarı: %{h_rate:.1f}")
                    
                    if h_rate >= 50:
                        print("✅ Saatlik veri de çekildi!")
                    else:
                        print("⚠️ Saatlik veri kısmen başarılı")
                except Exception as e:
                    print(f"⚠️ Saatlik veri hatası: {e}")
                
                return tv_success, tv_failed
            else:
                print(f"⚠️ TradingView düşük, Yahoo'ya geçiliyor...")
        except Exception as e:
            print(f"❌ TradingView hatası: {e}")
    else:
        print("⚠️ TradingView yok, Yahoo kullanılıyor")
    
    # 3. YAHOO YEDEK
    print("\n📡 3. AŞAMA: Yahoo Finance")
    print("-" * 60)
    return fetch_all_daily_yahoo(symbols_list, delay)


# ════════════════════════════════════════════════════════════
# 15 DAKİKALIK VERİ
# ════════════════════════════════════════════════════════════

def fetch_stock_data_15m(symbol, period="60d"):
    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(period=period, interval="15m")
        if df.empty: return None
        return df
    except: return None


def save_15m_to_database(symbol, df):
    if df is None or df.empty: return 0
    count = 0
    for dt, row in df.iterrows():
        try:
            save_price_data_15m(symbol=symbol, dt=dt.strftime("%Y-%m-%d %H:%M:%S"),
                              open_price=float(row['Open']), high=float(row['High']),
                              low=float(row['Low']), close=float(row['Close']),
                              volume=int(row['Volume']))
            count += 1
        except: pass
    return count


def fetch_all_15m(symbols_list=None, delay=0.2):
    if symbols_list is None: symbols_list = BIST_SYMBOLS
    total = len(symbols_list)
    print(f"\n🚀 {total} hisse 15dk veri...\n")
    success = 0
    failed = 0
    start_time = time.time()
    
    for i, symbol in enumerate(symbols_list, 1):
        if i % 10 == 0 or i == 1 or i == total:
            elapsed = time.time() - start_time
            avg = elapsed / i if i > 0 else 0
            remaining = avg * (total - i)
            print(f"⏳ [{i}/{total}] ({i*100//total}%) | ✅ {success} | ❌ {failed} | ETA: ~{int(remaining//60)}dk")
        
        df = fetch_stock_data_15m(symbol, period="60d")
        if df is not None and not df.empty:
            count = save_15m_to_database(symbol, df)
            if count > 0: success += 1
            else: failed += 1
        else: failed += 1
        
        if delay > 0: time.sleep(delay)
    
    elapsed_total = time.time() - start_time
    print(f"\n{'='*60}")
    print(f"📊 15dk VERİ TAMAMLANDI")
    print(f"✅ Başarılı: {success} | ❌ Başarısız: {failed}")
    print(f"⏱️ Toplam: {int(elapsed_total//60)}dk {int(elapsed_total%60)}sn")
    return success, failed


# ════════════════════════════════════════════════════════════
# ANLIK FİYAT
# ════════════════════════════════════════════════════════════

def fetch_current_price(symbol):
    if TV_READY:
        try:
            from services.tradingview_fetcher import get_current_price_tv
            price = get_current_price_tv(symbol)
            if price: return price
        except: pass
    
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.history(period="1d")
        if not info.empty: return float(info['Close'].iloc[-1])
        return None
    except: return None


if __name__ == "__main__":
    print("\n📊 BIST VERİ ÇEKME - HİBRİT")
    print(f"📡 TradingView: {'✅' if TV_READY else '❌'}")
    init_database()
    fetch_all_daily(symbols_list=BIST_SYMBOLS[:5])
    print("\n✅ Tamamlandı!")

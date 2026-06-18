"""
Yahoo Finance'den BIST hisse verilerini çeker
"""

import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import sys
import os
import time

# Üst klasördeki config'i import edebilmek için
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import BIST_SYMBOLS, HISTORICAL_DAYS
from database import save_price_data


def fetch_stock_data(symbol, period="1y"):
    """
    Tek bir hisse için veri çeker
    
    Args:
        symbol: Hisse kodu (örn: "THYAO.IS")
        period: Veri süresi ("1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "max")
    
    Returns:
        DataFrame veya None
    """
    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(period=period)
        
        if df.empty:
            return None
        
        return df
    
    except Exception as e:
        return None


def fetch_current_price(symbol):
    """
    Anlık fiyat bilgisini çeker
    """
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.history(period="1d")
        
        if not info.empty:
            last_price = info['Close'].iloc[-1]
            return float(last_price)
        return None
    
    except Exception as e:
        print(f"❌ {symbol} anlık fiyat hatası: {e}")
        return None


def save_to_database(symbol, df):
    """
    DataFrame'i veritabanına kaydeder
    """
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
        except Exception as e:
            pass
    
    return count


def fetch_all_bist_stocks(limit=None, delay=0.1):
    """
    Tüm BIST hisselerinin verilerini çeker ve kaydeder
    
    Args:
        limit: Test için kaç hisse çekileceği (None = hepsi)
        delay: Her hisse arasındaki bekleme süresi (saniye)
    """
    symbols = BIST_SYMBOLS[:limit] if limit else BIST_SYMBOLS
    total = len(symbols)
    
    print(f"\n🚀 {total} hisse için veri çekiliyor...\n")
    
    success = 0
    failed = 0
    failed_symbols = []
    start_time = time.time()
    
    for i, symbol in enumerate(symbols, 1):
        # İlerleme her 25 hissede bir göster
        if i % 25 == 0 or i == 1 or i == total:
            elapsed = time.time() - start_time
            avg_per_stock = elapsed / i if i > 0 else 0
            remaining = avg_per_stock * (total - i)
            eta_min = int(remaining // 60)
            eta_sec = int(remaining % 60)
            
            print(f"⏳ [{i}/{total}] ({i*100//total}%) "
                  f"| ✅ {success} | ❌ {failed} "
                  f"| Kalan süre: ~{eta_min}dk {eta_sec}sn")
        
        df = fetch_stock_data(symbol, period="1y")
        
        if df is not None and not df.empty:
            count = save_to_database(symbol, df)
            if count > 0:
                success += 1
            else:
                failed += 1
                failed_symbols.append(symbol)
        else:
            failed += 1
            failed_symbols.append(symbol)
        
        # Rate limit'e takılmamak için ufak bekleme
        if delay > 0:
            time.sleep(delay)
    
    # Sonuç özeti
    elapsed_total = time.time() - start_time
    total_min = int(elapsed_total // 60)
    total_sec = int(elapsed_total % 60)
    
    print(f"\n{'='*60}")
    print(f"📊 VERİ ÇEKME TAMAMLANDI")
    print(f"{'='*60}")
    print(f"✅ Başarılı     : {success} hisse")
    print(f"❌ Başarısız    : {failed} hisse")
    print(f"⏱️  Toplam süre : {total_min}dk {total_sec}sn")
    print(f"{'='*60}")
    
    if failed_symbols and len(failed_symbols) <= 30:
        print(f"\n⚠️  Veri alınamayan hisseler:")
        for sym in failed_symbols:
            print(f"   - {sym}")
    elif failed_symbols:
        print(f"\n⚠️  {len(failed_symbols)} hisseden veri alınamadı (çok fazla, gösterilmiyor)")
    
    return success, failed


if __name__ == "__main__":
    from database import init_database
    
    print("\n" + "="*60)
    print("📊 BIST VERİ ÇEKME SİSTEMİ")
    print("="*60)
    print(f"\n📋 Toplam {len(BIST_SYMBOLS)} hisse mevcut")
    
    print("\nSeçenekler:")
    print("  1 → Test (sadece 5 hisse)")
    print("  2 → Hızlı (BIST 100 - ~100 hisse)")
    print("  3 → TAM (Tüm BIST - 530 hisse, ~15-20 dk)")
    
    choice = input("\nSeçim (1/2/3): ").strip()
    
    init_database()
    
    if choice == "1":
        print("\n🧪 5 hisse çekiliyor...")
        fetch_all_bist_stocks(limit=5)
    elif choice == "2":
        print("\n⚡ İlk 100 hisse çekiliyor...")
        fetch_all_bist_stocks(limit=100)
    elif choice == "3":
        print("\n🚀 TÜM BIST çekiliyor (15-20 dk sürer)...")
        print("☕ Kahveni al, bekle...\n")
        fetch_all_bist_stocks(limit=None)
    else:
        print("❌ Geçersiz seçim")
        sys.exit(0)
    
    print("\n✅ İşlem tamamlandı!")
    print("👉 Şimdi tarama yap: python services/scanner.py")
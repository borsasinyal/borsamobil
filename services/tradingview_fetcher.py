"""
TradingView Veri Çekme - Günlük + Saatlik
"""

import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from tvDatafeed import TvDatafeed, Interval
    TV_AVAILABLE = True
except ImportError:
    print("⚠️ tvDatafeed yüklenmemiş")
    TV_AVAILABLE = False

from database import save_price_data

_tv_instance = None

def get_tv_instance():
    global _tv_instance
    if _tv_instance is not None:
        return _tv_instance
    if not TV_AVAILABLE:
        return None
    try:
        username = os.environ.get('TV_USERNAME')
        password = os.environ.get('TV_PASSWORD')
        if username and password:
            print(f"🔑 TradingView'a giriş yapılıyor...")
            _tv_instance = TvDatafeed(username=username, password=password)
            print("✅ TradingView bağlantısı başarılı")
        else:
            print("⚠️ TV credentials yok, anonim")
            _tv_instance = TvDatafeed()
        return _tv_instance
    except Exception as e:
        print(f"❌ TradingView bağlantı hatası: {e}")
        return None


def fetch_stock_tv(symbol, n_bars=300, interval='daily'):
    """
    TradingView'dan veri çek
    interval: 'daily' veya 'hourly'
    """
    if not TV_AVAILABLE:
        return None
    tv = get_tv_instance()
    if not tv:
        return None
    try:
        symbol_clean = symbol.replace('.IS', '')
        
        if interval == 'hourly':
            tv_interval = Interval.in_1_hour
        else:
            tv_interval = Interval.in_daily
        
        data = tv.get_hist(
            symbol=symbol_clean,
            exchange='BIST',
            interval=tv_interval,
            n_bars=n_bars
        )
        
        if data is None or data.empty:
            return None
        
        result = []
        for idx, row in data.iterrows():
            result.append({
                'date': idx.strftime('%Y-%m-%d %H:%M:%S') if interval == 'hourly' else idx.strftime('%Y-%m-%d'),
                'open': float(row['open']),
                'high': float(row['high']),
                'low': float(row['low']),
                'close': float(row['close']),
                'volume': int(row['volume'])
            })
        return result
    except:
        return None


def fetch_all_tv(symbols_list, delay=0.3, interval='daily'):
    """Toplu veri çekme"""
    if not TV_AVAILABLE:
        return 0, len(symbols_list)
    tv = get_tv_instance()
    if not tv:
        return 0, len(symbols_list)
    
    n_bars = 300 if interval == 'daily' else 100
    interval_text = "GÜNLÜK" if interval == 'daily' else "SAATLİK"
    
    total = len(symbols_list)
    print(f"\n🚀 TradingView'dan {total} hisse için {interval_text} veri çekiliyor...\n")
    
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
        
        try:
            data = fetch_stock_tv(symbol, n_bars=n_bars, interval=interval)
            
            if data and len(data) > 0:
                for row in data:
                    try:
                        save_price_data(
                            symbol=symbol,
                            date=row['date'],
                            open_price=row['open'],
                            high=row['high'],
                            low=row['low'],
                            close=row['close'],
                            volume=row['volume']
                        )
                    except:
                        pass
                success += 1
            else:
                failed += 1
                failed_symbols.append(symbol)
            
            if delay > 0:
                time.sleep(delay)
        except:
            failed += 1
            failed_symbols.append(symbol)
    
    elapsed_total = time.time() - start_time
    total_min = int(elapsed_total // 60)
    total_sec = int(elapsed_total % 60)
    
    print(f"\n{'='*60}")
    print(f"📊 TRADINGVIEW {interval_text} VERİ ÇEKME TAMAMLANDI")
    print(f"{'='*60}")
    print(f"✅ Başarılı: {success}")
    print(f"❌ Başarısız: {failed}")
    print(f"⏱️ Toplam: {total_min}dk {total_sec}sn")
    
    return success, failed


def get_current_price_tv(symbol):
    if not TV_AVAILABLE:
        return None
    try:
        data = fetch_stock_tv(symbol, n_bars=2)
        if data and len(data) > 0:
            return data[-1]['close']
        return None
    except:
        return None
